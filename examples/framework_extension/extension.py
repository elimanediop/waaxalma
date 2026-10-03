"""An offline extension using only Waaxalma's public facade."""
from dataclasses import dataclass

from app.framework import (
    AgentInput, AgentRegistry, AgentResult, BaseAgent, PipelineRegistry,
    PipelineState, ProviderRegistry, SequentialPipeline, SessionContext,
    TranslationProvider,
)


class DemoTranslationProvider:
    """Deterministic contract example, not a real translation engine."""
    name = "demo"

    async def translate(self, text: str, target_language: str) -> str:
        return f"[{target_language}] {text}"


@dataclass
class TranslationStage:
    provider: TranslationProvider
    name: str = "demo_translation"

    async def execute(self, state: PipelineState, context: SessionContext) -> PipelineState:
        state.set("translated_text", await self.provider.translate(
            state.require("source_text"), context.target_language,
        ))
        return state


class DemoAgent(BaseAgent):
    name = "demo_interpretation"

    def __init__(self, pipeline: SequentialPipeline) -> None:
        self.pipeline = pipeline

    async def execute(self, agent_input: AgentInput, context: SessionContext) -> AgentResult:
        if agent_input.operation != "translate":
            return AgentResult(success=False, error_code="DEMO_UNSUPPORTED_OPERATION",
                               error_message="Use the translate operation.")
        text = agent_input.payload.get("text")
        if not isinstance(text, str) or not text.strip():
            return AgentResult(success=False, error_code="DEMO_TEXT_REQUIRED",
                               error_message="Supply non-empty text.")
        state = await self.pipeline.execute(PipelineState({"source_text": text}), context)
        return AgentResult(success=True, output=state.to_dict())


def build_extension() -> tuple[AgentRegistry, PipelineRegistry, ProviderRegistry]:
    provider = DemoTranslationProvider()
    providers = ProviderRegistry()
    providers.register(capability="translation", name=provider.name, provider=provider)
    pipeline = SequentialPipeline(name="demo_pipeline", stages=[TranslationStage(provider)])
    pipelines = PipelineRegistry()
    pipelines.register(pipeline)
    agents = AgentRegistry()
    agents.register(DemoAgent(pipeline))
    return agents, pipelines, providers
