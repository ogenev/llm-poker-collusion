"""Inspect model calls with explicit inputs and durable, correlated evidence."""

import asyncio
from datetime import UTC, datetime
from time import monotonic

from inspect_ai.event import Event, ModelEvent
from inspect_ai.log import EvalSample, resolve_sample_attachments, transcript
from inspect_ai.model import (
    ChatMessage,
    ChatMessageSystem,
    ChatMessageUser,
    GenerateConfig,
    Model,
    ModelOutput,
)
from inspect_ai.util import span

from poker_collusion.model_adapter import GenerateText, ModelConfig, ModelRequest
from poker_collusion.model_log import ModelJournal
from poker_collusion.records import DecisionParseError
from poker_collusion.session_audit import current_request_id


def generation_config(config: ModelConfig, max_connections: int) -> GenerateConfig:
    return GenerateConfig(
        max_tokens=config.max_tokens,
        temperature=config.temperature,
        max_retries=0,
        cache=False,
        max_connections=max_connections,
        num_choices=1,
        system_message="",
        fallback_models=[],
        batch=False,
        fail_on_refusal=False,
    )


def _model_events(start: int, span_id: str) -> list[dict[str, object]]:
    # Public Inspect APIs resolve attachment references before saving the
    # provider's available raw request/response payloads in our own journal.
    trace = transcript()
    events: list[Event] = [
        event
        for event in trace.history.events_from(start)
        if isinstance(event, ModelEvent) and event.span_id == span_id
    ]
    sample = resolve_sample_attachments(
        EvalSample(
            id="audit",
            epoch=1,
            input="",
            target="",
            events=events,
            attachments=dict(trace.attachments),
        ),
        resolve_attachments="full",
    )
    return [event.model_dump(mode="json", exclude={"traceback_ansi"}) for event in sample.events]


def _response_error(output: ModelOutput) -> str | None:
    if output.error or len(output.choices) != 1:
        return "Expected one successful model response"
    if output.stop_reason not in ("stop", "unknown") or output.message.tool_calls:
        return f"Unusable model response: {output.stop_reason}"
    if output.fallback is not None:
        return "Model fallbacks are unavailable in this experiment"
    return None


def inspect_generator(model: Model, journal: ModelJournal, max_connections: int) -> GenerateText:
    async def generate(request: ModelRequest) -> str:
        if str(model) != request.config.model:
            raise ValueError("Inspect model differs from the configured model")
        request_id = current_request_id()
        span_id = f"{journal.session_id}-request-{request_id}"
        messages: list[ChatMessage] = [
            ChatMessageSystem(content=request.prompt.system),
            ChatMessageUser(content=request.prompt.user),
        ]
        config = generation_config(request.config, max_connections)
        async with span(f"Poker request {request_id}", type="poker_decision", id=span_id):
            journal.emit(
                "call_started",
                request_id=request_id,
                span_id=span_id,
                timestamp=datetime.now(UTC).isoformat(),
                prompt=request.prompt,
                prompt_sha256=request.prompt.sha256,
                requested_model=request.config.model,
                generation=config.model_dump(mode="json", exclude_none=True),
                input=[message.model_dump(mode="json") for message in messages],
            )
            start = transcript().history.event_count
            started = monotonic()
            try:
                output = await model.generate(
                    input=messages,
                    tools=[],
                    tool_choice="none",
                    config=config,
                    cache=False,
                )
            except BaseException as error:
                journal.emit(
                    "call_finished",
                    request_id=request_id,
                    span_id=span_id,
                    status="cancelled" if isinstance(error, asyncio.CancelledError) else "error",
                    elapsed_seconds=monotonic() - started,
                    error={"type": type(error).__name__, "detail": str(error)},
                    output=None,
                    response_error=None,
                    model_events=_model_events(start, span_id),
                )
                raise
            response_error = _response_error(output)
            # This write finishes before parsing, validation, or any game effect.
            journal.emit(
                "call_finished",
                request_id=request_id,
                span_id=span_id,
                status="returned",
                elapsed_seconds=monotonic() - started,
                error=None,
                output=output.model_dump(mode="json"),
                response_error=response_error,
                model_events=_model_events(start, span_id),
            )
            if response_error is not None:
                raise DecisionParseError(output.completion, response_error)
            return output.completion

    return generate
