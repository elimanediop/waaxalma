import uuid
from typing import Any

from app.agents.base_agent import BaseAgent
from app.core.agent_input import AgentInput
from app.core.agent_result import AgentResult
from app.core.session_context import SessionContext
from app.exceptions.error_codes import ErrorCode
from app.pipelines.pipeline import Pipeline
from app.pipelines.pipeline_state import PipelineState


class InterpreterAgent(BaseAgent):
    description = (
        "Agent that interprets user messages into another language "
        "and generates spoken audio."
    )

    def __init__(
        self,
        *,
        text_pipeline: Pipeline,
        audio_pipeline: Pipeline,
    ) -> None:
        self._text_pipeline = text_pipeline
        self._audio_pipeline = audio_pipeline

    @property
    def name(self) -> str:
        return "interpreter"

    async def execute(
        self,
        agent_input: AgentInput,
        context: SessionContext,
    ) -> AgentResult:
        operation = agent_input.operation
        payload = agent_input.payload

        if operation == "interpret":
            return await self._execute_text_interpretation(
                payload=payload,
                context=context,
            )

        if operation == "interpret_audio":
            return await self._execute_audio_interpretation(
                payload=payload,
                context=context,
            )

        return AgentResult(
            success=False,
            output=None,
            error_code=ErrorCode.UNSUPPORTED_OPERATION.value,
            error_message=(
                f"Operation '{operation}' is not supported "
                f"by agent '{self.name}'."
            ),
            metadata=self._build_metadata(
                operation=operation,
                context=context,
            ),
        )

    async def _execute_text_interpretation(
        self,
        payload: dict[str, Any],
        context: SessionContext,
    ) -> AgentResult:
        text = payload.get("text")

        if not isinstance(text, str) or not text.strip():
            return AgentResult(
                success=False,
                output=None,
                error_code=ErrorCode.INVALID_INPUT.value,
                error_message="'text' is required.",
                metadata=self._build_metadata(
                    operation="interpret",
                    context=context,
                ),
            )

        target_language = payload.get(
            "target_language",
            context.target_language,
        )

        state = PipelineState(
            data={
                "request_id": str(uuid.uuid4()),
                "agent_name": self.name,
                "source_text": text.strip(),
                "target_language": target_language,
            }
        )

        result = await self._text_pipeline.execute(
            state=state,
            context=context,
        )

        return AgentResult(
            success=True,
            output=self._build_output(
                state=result,
                context=context,
            ),
            metadata=self._build_metadata(
                operation="interpret",
                context=context,
            ),
        )

    async def _execute_audio_interpretation(
        self,
        payload: dict[str, Any],
        context: SessionContext,
    ) -> AgentResult:
        audio_path = payload.get("audio_path")

        if not isinstance(audio_path, str) or not audio_path.strip():
            return AgentResult(
                success=False,
                output=None,
                error_code=ErrorCode.INVALID_INPUT.value,
                error_message="'audio_path' is required.",
                metadata=self._build_metadata(
                    operation="interpret_audio",
                    context=context,
                ),
            )

        target_language = payload.get(
            "target_language",
            context.target_language,
        )

        state = PipelineState(
            data={
                "request_id": str(uuid.uuid4()),
                "agent_name": self.name,
                "audio_path": audio_path.strip(),
                "target_language": target_language,
            }
        )

        result = await self._audio_pipeline.execute(
            state=state,
            context=context,
        )

        return AgentResult(
            success=True,
            output=self._build_output(
                state=result,
                context=context,
            ),
            metadata=self._build_metadata(
                operation="interpret_audio",
                context=context,
            ),
        )

    def _build_output(
        self,
        state: PipelineState,
        context: SessionContext,
    ) -> dict[str, Any]:
        quality = None

        if state.get("quality_accepted") is not None:
            quality = {
                "accepted": state.get(
                    "quality_accepted"
                ),
                "score": state.get(
                    "quality_score"
                ),
                "issues": state.get(
                    "quality_issues",
                    [],
                ),
                "metadata": state.get(
                    "quality_metadata",
                    {},
                ),
            }

        return {
            "request_id": state.require(
                "request_id"
            ),
            "session_id": context.session_id,
            "agent": self.name,
            "source_text": state.require(
                "source_text"
            ),
            "interpreted_text": state.require(
                "interpreted_text"
            ),
            "audio_url": state.require(
                "audio_url"
            ),
            "quality": quality,
        }

    def _build_metadata(
        self,
        operation: str,
        context: SessionContext,
    ) -> dict[str, Any]:
        return {
            "agent": self.name,
            "operation": operation,
            "session_id": context.session_id,
        }