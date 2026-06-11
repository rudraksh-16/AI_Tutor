import asyncio
import json
import logging
from typing import AsyncGenerator, Awaitable, Callable, Dict, Any, Optional

from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.db.database import SessionLocal

logger = logging.getLogger(__name__)


class ChatCoordinator:
    """Orchestrates agent streams and keeps them alive across client disconnects."""

    _active_runs: Dict[str, Dict[str, Any]] = {}
    _lock = asyncio.Lock()
    _DONE = object()

    @staticmethod
    async def create_streaming_response(
        conversation_id: Any,
        agent_stream: Optional[AsyncGenerator[Dict[str, Any], None]],
        save_func: Callable[[AsyncSession, Any, Dict[str, Any]], Awaitable[None]],
        final_payload_callback: Optional[Callable[[Dict[str, Any]], AsyncGenerator[str, None]]] = None,
    ) -> StreamingResponse:
        """Create an SSE response backed by a background task for the conversation."""
        run_key = str(conversation_id)
        subscriber_queue: asyncio.Queue = asyncio.Queue()
        snapshot_payload: Optional[str] = None

        async with ChatCoordinator._lock:
            run = ChatCoordinator._active_runs.get(run_key)
            run_already_exists = run is not None
            if run is None and agent_stream is None:
                return StreamingResponse(
                    ChatCoordinator._empty_stream(),
                    media_type="text/event-stream",
                )
            if run is None:
                run = {"subscribers": set(), "assistant_snapshot": ""}
                ChatCoordinator._active_runs[run_key] = run
                run["task"] = asyncio.create_task(
                    ChatCoordinator._run_in_background(
                        run_key,
                        conversation_id,
                        agent_stream,
                        save_func,
                        final_payload_callback,
                    )
                )
            elif run.get("assistant_snapshot"):
                snapshot_payload = ChatCoordinator._build_snapshot_event(
                    run["assistant_snapshot"]
                )
            run["subscribers"].add(subscriber_queue)

        async def streaming_wrapper():
            try:
                if run_already_exists and snapshot_payload:
                    yield snapshot_payload
                while True:
                    item = await subscriber_queue.get()
                    if item is ChatCoordinator._DONE:
                        break
                    yield item
            finally:
                await ChatCoordinator._unsubscribe(run_key, subscriber_queue)

        return StreamingResponse(streaming_wrapper(), media_type="text/event-stream")

    @staticmethod
    async def _run_in_background(
        run_key: str,
        conversation_id: Any,
        agent_stream: AsyncGenerator[Dict[str, Any], None],
        save_func: Callable[[AsyncSession, Any, Dict[str, Any]], Awaitable[None]],
        final_payload_callback: Optional[Callable[[Dict[str, Any]], AsyncGenerator[str, None]]],
    ) -> None:
        """Keep consuming the agent stream even if all clients disconnect."""
        collected_final: Dict[str, Any] = {}

        try:
            async for event in agent_stream:
                await ChatCoordinator._capture_stream_state(run_key, event)
                if event.get("type") == "final":
                    collected_final.update(event.get("data", {}))
                await ChatCoordinator._broadcast(run_key, f"data: {json.dumps(event)}\n\n")

            if collected_final:
                await ChatCoordinator._finalize_and_persist(conversation_id, collected_final, save_func)

                if final_payload_callback:
                    async for extra_event in ChatCoordinator._run_post_processing(final_payload_callback, collected_final):
                        await ChatCoordinator._broadcast(run_key, extra_event)

        except Exception as exc:
            logger.exception("Error during background agent streaming for %s", conversation_id)
            await ChatCoordinator._broadcast(
                run_key,
                f"data: {json.dumps({'error': str(exc)})}\n\n",
            )
        finally:
            await ChatCoordinator._finish_run(run_key)

    @staticmethod
    async def _broadcast(run_key: str, payload: str) -> None:
        async with ChatCoordinator._lock:
            run = ChatCoordinator._active_runs.get(run_key)
            if not run:
                return
            subscribers = list(run["subscribers"])

        for queue in subscribers:
            await queue.put(payload)

    @staticmethod
    async def _unsubscribe(run_key: str, queue: asyncio.Queue) -> None:
        async with ChatCoordinator._lock:
            run = ChatCoordinator._active_runs.get(run_key)
            if not run:
                return
            run["subscribers"].discard(queue)

    @staticmethod
    async def _finish_run(run_key: str) -> None:
        async with ChatCoordinator._lock:
            run = ChatCoordinator._active_runs.pop(run_key, None)
            if not run:
                return
            subscribers = list(run["subscribers"])

        for queue in subscribers:
            await queue.put(ChatCoordinator._DONE)

    @staticmethod
    async def _finalize_and_persist(conv_id: Any, data: dict, save_fn: Callable) -> None:
        """Save the final agent output to the database."""
        try:
            async with SessionLocal() as db:
                await save_fn(db, conv_id, data)
        except Exception as exc:
            logger.error("Failed to save final stream results for %s: %s", conv_id, exc)

    @staticmethod
    async def _run_post_processing(callback: Callable, data: dict) -> AsyncGenerator[str, None]:
        """Execute optional post-completion logic and yield any resulting SSE events."""
        try:
            async for extra_event in callback(data):
                yield extra_event
        except Exception as exc:
            logger.error("Error in final payload callback: %s", exc)

    @staticmethod
    async def has_active_run(conversation_id: Any) -> bool:
        """Return whether a conversation currently has a live background stream."""
        async with ChatCoordinator._lock:
            return str(conversation_id) in ChatCoordinator._active_runs

    @staticmethod
    async def _capture_stream_state(run_key: str, event: Dict[str, Any]) -> None:
        """Track the latest assistant text so new subscribers can resume smoothly."""
        event_type = event.get("type")
        if event_type == "text":
            await ChatCoordinator._append_snapshot_text(run_key, event.get("content", ""))
            return
        if event_type == "final":
            final_text = event.get("data", {}).get("assistant_text", "")
            await ChatCoordinator._replace_snapshot_text(run_key, final_text)

    @staticmethod
    async def _append_snapshot_text(run_key: str, chunk: str) -> None:
        """Append a streamed text delta to the in-memory assistant snapshot."""
        if not chunk:
            return
        async with ChatCoordinator._lock:
            run = ChatCoordinator._active_runs.get(run_key)
            if not run:
                return
            current_text = run.get("assistant_snapshot", "")
            run["assistant_snapshot"] = f"{current_text}{chunk}"

    @staticmethod
    async def _replace_snapshot_text(run_key: str, content: str) -> None:
        """Replace the in-memory assistant snapshot with the finalized text."""
        async with ChatCoordinator._lock:
            run = ChatCoordinator._active_runs.get(run_key)
            if not run:
                return
            run["assistant_snapshot"] = content or ""

    @staticmethod
    def _build_snapshot_event(content: str) -> str:
        """Build the resume snapshot event for a reconnecting subscriber."""
        return f"data: {json.dumps({'type': 'resume_snapshot', 'content': content})}\n\n"

    @staticmethod
    async def _empty_stream() -> AsyncGenerator[str, None]:
        """Yield an empty SSE stream for no-op resume attempts."""
        if False:
            yield ""
