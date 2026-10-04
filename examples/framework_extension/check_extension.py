"""Run after installing the wheel, without adding backend source to sys.path."""
import asyncio

from app.framework import AgentInput, PipelineState, SessionContext
from app.framework.testing import (
    assert_agent_conformance, assert_stage_conformance,
    assert_translation_provider_conformance,
)
from extension import TranslationStage, build_extension


async def main() -> None:
    agents, pipelines, providers = build_extension()
    provider = providers.get(capability="translation", name="demo")
    context = SessionContext(target_language="en")
    assert await assert_translation_provider_conformance(
        provider, text="bonjour", target_language="en",
    ) == "[en] bonjour"
    state = await assert_stage_conformance(
        TranslationStage(provider), PipelineState({"source_text": "bonjour"}), context,
    )
    assert state.require("translated_text") == "[en] bonjour"
    assert pipelines.names() == ["demo_pipeline"]
    agent = agents.find("demo_interpretation")
    result = await assert_agent_conformance(
        agent, AgentInput(operation="translate", payload={"text": "bonjour"}), context,
    )
    assert result.success and result.output["translated_text"] == "[en] bonjour"
    for agent_input, error in [
        (AgentInput(operation="invalid"), "DEMO_UNSUPPORTED_OPERATION"),
        (AgentInput(operation="translate"), "DEMO_TEXT_REQUIRED"),
    ]:
        failure = await assert_agent_conformance(agent, agent_input, context)
        assert not failure.success and failure.error_code == error
    print("External agent/provider/stage: conformance and composition OK")


if __name__ == "__main__":
    asyncio.run(asyncio.wait_for(main(), timeout=10))
