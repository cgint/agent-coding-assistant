from __future__ import annotations

import json
import asyncio
from typing import Tuple, Callable, Optional, AsyncGenerator, Dict, Any

import dspy
from datetime import datetime

from dspy_agent_lm_vertexai import get_vertexai_lm
from dspy_agent_util_streaming_grounding_manager import StreamingGroundingManager
from dspy_agent_tool_streaming_internal_knowledge import StreamingInternalKnowledgeTool
from dspy_agent_tool_streaming_websearch_tavily import StreamingWebSearchToolTavily
from dspy_agent_expert_ai import AgentCodingAssistantAI
from dspy_constants import MODEL_NAME_GEMINI_2_5_FLASH, MODEL_NAME_GEMINI_2_5_PRO, MODEL_NAME_GEMINI_2_5_FLASH_LITE, MODEL_NAME_GEMINI_2_0_FLASH
from session_history_manager import SessionHistoryManager
from dspy.utils.callback import BaseCallback
from session_models import ToolCallRecord
from dspy_pricing_service import PricingService, SingleModelPricingService


class StreamingDspyAgentService:
    """
    Streaming version of DSPy Agent Service that emits real-time events for WebSocket communication.
    Extends the original service with streaming capabilities and event callbacks.
    """

    def __init__(self, event_callback: Optional[Callable[..., Any]] = None, session_id: Optional[str] = None, threadsafe_event_callback: Optional[Callable[..., Any]] = None):
        self.event_callback = event_callback
        self.threadsafe_event_callback = threadsafe_event_callback
        self.session_id = session_id
        self.history_manager = SessionHistoryManager() if session_id else None
        # In-memory collector for per-turn tool calls (keyed by DSPy call_id)
        self._tool_calls: Dict[str, ToolCallRecord] = {}

        # Initialize the streaming grounding manager and tools with event callbacks
        self.grounding_manager = StreamingGroundingManager(
            event_callback=event_callback,
            threadsafe_event_callback=threadsafe_event_callback,
        )
        
        # Create streaming tools with event callbacks
        # Do not pass event_callback into tools directly to avoid mixing concerns and duplicate events
        internal_tool = StreamingInternalKnowledgeTool(
            grounding_manager=self.grounding_manager,
        )
        web_search_tool = StreamingWebSearchToolTavily(
            grounding_manager=self.grounding_manager,
            include_domains=["google.com"],
            top_k=10,
            include_raw_content=True,
        )

        # Attach per-request DSPy callbacks to tools to emit progress via DSPy's native hook system
        if self.threadsafe_event_callback or self.event_callback:
            tool_callback = _ToolProgressCallback(
                event_callback=self.event_callback,
                threadsafe_event_callback=self.threadsafe_event_callback,
                tool_calls=self._tool_calls,
            )
            # Instance-level callbacks are honored by DSPy in addition to global callbacks
            try:
                internal_tool.callbacks = getattr(internal_tool, "callbacks", []) + [tool_callback]  # type: ignore[attr-defined]
                web_search_tool.callbacks = getattr(web_search_tool, "callbacks", []) + [tool_callback]  # type: ignore[attr-defined]
            except Exception:
                # If attaching callbacks fails for any reason, continue without breaking
                pass

        # Initialize the main agent with streaming tools
        self.expert_ai = AgentCodingAssistantAI(tools=[internal_tool, web_search_tool])
        
        # Create streamified version of the agent for answer streaming
        self.streaming_expert_ai = dspy.streamify(
            self.expert_ai,
            stream_listeners=[
                dspy.streaming.StreamListener(signature_field_name="answer")  # type: ignore[attr-defined]
            ]
        )

        # Ensure a public stream_answer coroutine is always available on the instance.
        # This avoids AttributeError in call sites even if class-level definitions drift.
        if not hasattr(self, "stream_answer") or not callable(getattr(self, "stream_answer", None)):
            # Bind the implementation as an instance attribute
            self.stream_answer = self._stream_answer_impl  # type: ignore[assignment]
    
    def set_session_id(self, session_id: str) -> None:
        """Set or update the logical session identifier used for persistence."""
        self.session_id = session_id
        if self.history_manager is None:
            self.history_manager = SessionHistoryManager()

    @staticmethod
    def configure_dspy() -> None:
        try:
            dspy.settings.configure(
                lm=get_vertexai_lm(
                    model=f"vertex_ai/{MODEL_NAME_GEMINI_2_5_FLASH}",
                    reasoning_effort="disable",
                ),
                track_usage=True,
            )
            # Monkeypatch UsageTracker merge to handle dict/int mismatch
            from dspy.utils import usage_tracker as _ut

            def _safe_merge_usage_entries(self, result: dict[str, Any], usage_entry: dict[str, Any]) -> dict[str, Any]:
                print(f"Merging usage entries: {str(result)} and {str(usage_entry)}")
                for k, v in usage_entry.items():
                    current = result.get(k)
                    if isinstance(current, dict) and isinstance(v, dict):
                        self._merge_usage_entries(current, v)
                    elif isinstance(v, (int, float)) or v is None:
                        try:
                            result[k] = (current or 0) + (v or 0)  # type: ignore[operator]
                        except TypeError:
                            result[k] = v or 0
                    else:
                        result[k] = v
                return result

            _ut.UsageTracker._merge_usage_entries = _safe_merge_usage_entries  # type: ignore[assignment]
            dspy.configure_cache(
                enable_disk_cache=False, enable_memory_cache=False, enable_litellm_cache=False
            )
            print(f"DSPy configured to use {dspy.settings.lm.model} for streaming.")
        except Exception as e:
            print(f"Error configuring DSPy: {e}")
            raise

    async def _stream_answer_impl(self, question: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Instance-bound implementation for streaming answers with events."""
        # Reset grounding for new turn
        self.grounding_manager.reset()
        # Clear tool calls for the new turn without breaking callback reference
        self._tool_calls.clear()

        # Build history
        history_entries = []
        if self.history_manager and self.session_id:
            try:
                history_entries = self.history_manager.get_chat_history(self.session_id)
            except Exception:
                history_entries = []

        dspy_messages: list[Dict[str, Any]] = []
        for entry in history_entries:
            dspy_messages.append({"question": entry.question, "answer": entry.answer})
        history = dspy.History(messages=dspy_messages)

        # Emit start
        await self._emit_event("question_start", {
            "question": question,
            "history_turns": len(dspy_messages),
            "timestamp": self._get_timestamp(),
        })

        try:
            async for chunk in self.streaming_expert_ai(question=question, history=history):  # type: ignore[misc]
                if isinstance(chunk, dspy.streaming.StreamResponse):  # type: ignore[attr-defined]
                    chunk_data = {"chunk": chunk.chunk, "timestamp": self._get_timestamp()}
                    await self._emit_event("answer_chunk", chunk_data)
                    yield {"type": "answer_chunk", "data": chunk_data}
                elif isinstance(chunk, dspy.Prediction):
                    final_answer = chunk.answer
                    grounding_info = self.grounding_manager.format_for_display()
                    if grounding_info:
                        final_answer += grounding_info

                    usage_metadata = chunk.get_lm_usage()
                    # Augment usage metadata with cost statistics
                    try:
                        if isinstance(usage_metadata, dict):
                            usage_metadata = self._augment_usage_with_cost(usage_metadata)
                    except Exception:
                        pass
                    if self.history_manager and self.session_id:
                        # Persist collected tool calls with the chat entry
                        # Duplicate records so history contains both the start and the completion/error entries
                        flat_tools: list[ToolCallRecord] = []
                        for rec in self._tool_calls.values():
                            # Started record
                            flat_tools.append(
                                ToolCallRecord(
                                    id=rec.id,
                                    name=rec.name,
                                    status="started",
                                    started_at=rec.started_at,
                                    ended_at=None,
                                    duration_ms=None,
                                    input_summary=rec.input_summary,
                                    result_preview=None,
                                    error=None,
                                )
                            )
                            # Completion or error record
                            if rec.status in ("completed", "error"):
                                flat_tools.append(
                                    ToolCallRecord(
                                        id=rec.id,
                                        name=rec.name,
                                        status=rec.status,
                                        started_at=rec.started_at,
                                        ended_at=rec.ended_at,
                                        duration_ms=rec.duration_ms,
                                        input_summary=rec.input_summary,
                                        result_preview=rec.result_preview,
                                        error=rec.error,
                                    )
                                )

                        self.history_manager.add_chat_entry(
                            self.session_id,
                            question,
                            final_answer,
                            usage_metadata,
                            tools=flat_tools,
                        )

                    completion_data = {
                        "answer": final_answer,
                        "raw_answer": chunk.answer,
                        "grounding": self.grounding_manager.get_grounding_data(),
                        "usage_metadata": usage_metadata,
                        "timestamp": self._get_timestamp(),
                    }
                    await self._emit_event("answer_complete", completion_data)
                    yield {"type": "answer_complete", "data": completion_data}
        except Exception as e:
            error_data = {
                "message": str(e),
                "error_type": type(e).__name__,
                "timestamp": self._get_timestamp(),
            }
            await self._emit_event("error", error_data)
            yield {"type": "error", "data": error_data}
            raise

    async def stream_answer(self, question: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Public method that delegates to the internal implementation."""
        async for event in self._stream_answer_impl(question):
            yield event

    async def answer_one_question_async(self, question: str) -> Tuple[str, str]:
        """
        Async version of answer_one_question that collects all streaming events.
        
        Returns:
            Tuple of (final_answer, tracked_usage_metadata_str)
        """
        final_answer = ""
        tracked_usage_metadata_str = ""

        cur_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        print(f"Starting chat run {cur_timestamp}")

        async for event in self.stream_answer(question):
            if event["type"] == "answer_complete":
                final_answer = event["data"]["answer"]
                tracked_usage_metadata_str = json.dumps(
                    event["data"]["usage_metadata"], indent=4
                )
                break
            elif event["type"] == "error":
                raise Exception(event["data"]["message"])
        
        return final_answer, tracked_usage_metadata_str

    def answer_one_question(self, question: str) -> Tuple[str, str]:
        """
        Synchronous version that runs the async streaming in an event loop.
        
        Returns:
            Tuple of (final_answer, tracked_usage_metadata_str)
        """
        try:
            # Try to use existing event loop
            asyncio.get_running_loop()
            # If we're in an async context, we need to handle this differently
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run, 
                    self.answer_one_question_async(question)
                )
                return future.result()
        except RuntimeError:
            # No event loop running, create new one
            return asyncio.run(self.answer_one_question_async(question))

    async def _emit_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Emit event via callback if available."""
        if self.event_callback:
            await self.event_callback(event_type, data)

    def _get_timestamp(self) -> str:
        """Get current timestamp for events."""
        from datetime import datetime
        return datetime.now().isoformat()

    # --- Internal helpers: pricing augmentation ---
    def _augment_usage_with_cost(self, usage_metadata: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(usage_metadata, dict):
            return usage_metadata

        def _has_cost(u: Dict[str, Any]) -> bool:
            cs = u.get("cost_statistics") if isinstance(u.get("cost_statistics"), dict) else None
            if not cs:
                return False
            val = cs.get("total_cost_llm_api_usd") or cs.get("total_cost")
            try:
                return val is not None and float(val) > 0
            except Exception:
                return False

        # Flat structure
        if ("prompt_tokens" in usage_metadata) or ("completion_tokens" in usage_metadata):
            if _has_cost(usage_metadata):
                return usage_metadata
            model_name = usage_metadata.get("model") or self._infer_model_from_any(usage_metadata)
            prompt = int(usage_metadata.get("prompt_tokens") or 0)
            completion = int(usage_metadata.get("completion_tokens") or 0)
            cost_stats = self._compute_cost_statistics(model_name, prompt, completion)
            if cost_stats is not None:
                out = dict(usage_metadata)
                out["cost_statistics"] = cost_stats
                if model_name:
                    out["model"] = model_name
                return out
            return usage_metadata

        # Nested by model key
        for key, val in usage_metadata.items():
            if not isinstance(val, dict):
                continue
            if ("prompt_tokens" in val) or ("completion_tokens" in val) or ("total_tokens" in val):
                if _has_cost(val):
                    return usage_metadata
                prompt = int(val.get("prompt_tokens") or 0)
                completion = int(val.get("completion_tokens") or 0)
                model_name = self._normalize_model_name(key)
                cost_stats = self._compute_cost_statistics(model_name, prompt, completion)
                if cost_stats is not None:
                    new_val = dict(val)
                    new_val["cost_statistics"] = cost_stats
                    out = dict(usage_metadata)
                    out[key] = new_val
                    return out
                return usage_metadata

        return usage_metadata

    def _compute_cost_statistics(self, model_name_raw: Optional[str], prompt_tokens: int, completion_tokens: int) -> Optional[Dict[str, Any]]:
        model_name = self._normalize_model_name(model_name_raw or "")
        try:
            pricing_service = PricingService()
            model_pricing = SingleModelPricingService(model_name, pricing_service)
            stats = model_pricing.get_cost_statistics_for(prompt_tokens, completion_tokens)
            if stats is None:
                return None
            result = {
                "input_cost": stats.input_cost,
                "output_cost": stats.output_cost,
                "total_cost": stats.total_cost,
                "currency": stats.currency,
            }
            if (stats.currency or "").upper() == "USD":
                result["total_cost_llm_api_usd"] = stats.total_cost
            return result
        except Exception:
            return None

    def _normalize_model_name(self, raw_model: str) -> str:
        rm = (raw_model or "").lower()
        if "/" in rm:
            rm = rm.split("/")[-1]
        if "2.5-pro" in rm:
            return MODEL_NAME_GEMINI_2_5_PRO
        if "2.5-flash-lite" in rm or "flash-lite" in rm:
            return MODEL_NAME_GEMINI_2_5_FLASH_LITE
        if "2.5-flash" in rm:
            return MODEL_NAME_GEMINI_2_5_FLASH
        if "2.0-flash" in rm or "20-flash" in rm:
            return MODEL_NAME_GEMINI_2_0_FLASH
        return MODEL_NAME_GEMINI_2_5_FLASH

    def _infer_model_from_any(self, usage: Dict[str, Any]) -> str:
        for k, v in usage.items():
            if isinstance(v, dict) and ("prompt_tokens" in v or "completion_tokens" in v or "total_tokens" in v):
                return self._normalize_model_name(k)
        return MODEL_NAME_GEMINI_2_5_FLASH


class _ToolProgressCallback(BaseCallback):
    """Per-request tool progress callback that forwards events to the provided event emitters.

    Uses the provided threadsafe_event_callback to ensure emissions work from sync contexts as well.
    """

    def __init__(
        self,
        event_callback: Optional[Callable[[str, Dict[str, Any]], Any]] = None,
        threadsafe_event_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None,
        tool_calls: Optional[Dict[str, ToolCallRecord]] = None,
    ) -> None:
        self._event_callback = event_callback
        self._threadsafe_event_callback = threadsafe_event_callback
        self._tool_calls = tool_calls if tool_calls is not None else {}

    def on_tool_start(self, call_id: str, instance: Any, inputs: Dict[str, Any]) -> None:
        tool_name = getattr(instance, "name", getattr(instance, "__class__", type(instance)).__name__)
        input_summary = inputs.get("query", inputs.get("question", ""))
        # Handle kwargs-based query if present
        if (not input_summary) and isinstance(inputs, dict):
            try:
                kw = inputs.get("kwargs")
                if isinstance(kw, dict) and "query" in kw:
                    input_summary = kw.get("query")
            except Exception:
                pass
        # Handle positional args if present
        if (not input_summary) and isinstance(inputs, dict) and "args" in inputs:
            try:
                args = inputs.get("args")
                if isinstance(args, (list, tuple)) and args:
                    input_summary = str(args[0])
            except Exception:
                pass
        # Fallback to the full inputs dict if specific keys are missing
        if not input_summary:
            try:
                input_summary = str(inputs)
            except Exception:
                input_summary = ""
        now_str = _get_timestamp_str()
        payload = {
            "tool": tool_name,
            "query": input_summary,
            "description": f"Starting {tool_name}...",
            "timestamp": now_str,
        }
        self._emit("tool_start", payload)

        # Record start in collector
        try:
            from datetime import datetime as _dt
            started_at = _dt.fromisoformat(now_str)
        except Exception:
            from datetime import datetime as _dt
            started_at = _dt.now()
        self._tool_calls[call_id] = ToolCallRecord(
            id=call_id,
            name=tool_name,
            status="started",
            started_at=started_at,
            input_summary=(str(input_summary)[:200] if input_summary else None),
        )

    def on_tool_end(self, call_id: str, outputs: Any | None, exception: Exception | None = None) -> None:
        record = self._tool_calls.get(call_id)
        now_str = _get_timestamp_str()
        try:
            from datetime import datetime as _dt
            ended_at = _dt.fromisoformat(now_str)
        except Exception:
            from datetime import datetime as _dt
            ended_at = _dt.now()

        if exception is not None:
            payload = {
                "tool": record.name if record else None,
                "error": str(exception),
                "timestamp": now_str,
            }
            self._emit("tool_error", payload)
            if record is not None:
                record.status = "error"
                record.ended_at = ended_at
                try:
                    record.duration_ms = int((record.ended_at - record.started_at).total_seconds() * 1000)
                except Exception:
                    record.duration_ms = None
                record.error = str(exception)
            return

        # Successful completion
        try:
            as_str = str(outputs) if outputs is not None else ""
            result_preview = as_str[:200] + ("..." if len(as_str) > 200 else "") if as_str else None
        except Exception:
            result_preview = None
        tool_name = record.name if record else None
        payload = {
            "tool": tool_name,
            "result_preview": result_preview,
            "timestamp": now_str,
        }
        self._emit("tool_complete", payload)
        if record is not None:
            record.status = "completed"
            record.ended_at = ended_at
            try:
                record.duration_ms = int((record.ended_at - record.started_at).total_seconds() * 1000)
            except Exception:
                record.duration_ms = None
            record.result_preview = result_preview

    def _emit(self, event_type: str, data: Dict[str, Any]) -> None:
        # Prefer threadsafe emitter for compatibility with sync contexts
        try:
            if self._threadsafe_event_callback is not None:
                self._threadsafe_event_callback(event_type, data)
                return
        except Exception:
            pass

        # Fallback to scheduling the async event callback if available
        try:
            if self._event_callback is not None:
                loop = asyncio.get_running_loop()
                loop.create_task(self._event_callback(event_type, data))
        except Exception:
            # As a last resort, ignore emission failures to avoid breaking tool execution
            pass


def _get_timestamp_str() -> str:
    return datetime.now().isoformat()


# Backward compatibility: create a factory function that returns the original service
def create_standard_service() -> Any:
    """Create a standard non-streaming service for backward compatibility."""
    from dspy_agent_service import DspyAgentService
    return DspyAgentService()