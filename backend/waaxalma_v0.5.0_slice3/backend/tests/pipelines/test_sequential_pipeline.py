import pytest

from app.core.session_context import SessionContext
from app.pipelines.pipeline_state import PipelineState
from app.pipelines.sequential_pipeline import SequentialPipeline


class FirstStage:

    @property
    def name(self) -> str:
        return "first"

    async def execute(
        self,
        state: PipelineState,
        context: SessionContext,
    ) -> PipelineState:
        state.set(
            "first",
            True,
        )

        return state


class SecondStage:

    @property
    def name(self) -> str:
        return "second"

    async def execute(
        self,
        state: PipelineState,
        context: SessionContext,
    ) -> PipelineState:
        assert state.require("first") is True

        state.set(
            "second",
            True,
        )

        return state


@pytest.mark.asyncio
async def test_pipeline_executes_stages_in_order() -> None:
    pipeline = SequentialPipeline(
        name="test-pipeline",
        stages=[
            FirstStage(),
            SecondStage(),
        ],
    )

    state = PipelineState()

    result = await pipeline.execute(
        state=state,
        context=SessionContext(
            session_id="pipeline-test",
        ),
    )

    assert result.get("first") is True
    assert result.get("second") is True

    assert pipeline.stage_names == [
        "first",
        "second",
    ]


def test_pipeline_requires_name() -> None:
    with pytest.raises(
        ValueError,
        match="name cannot be empty",
    ):
        SequentialPipeline(
            name="",
            stages=[
                FirstStage(),
            ],
        )


def test_pipeline_requires_at_least_one_stage() -> None:
    with pytest.raises(
        ValueError,
        match="must contain at least one stage",
    ):
        SequentialPipeline(
            name="empty-pipeline",
            stages=[],
        )


def test_pipeline_state_requires_existing_key() -> None:
    state = PipelineState()

    with pytest.raises(
        ValueError,
        match="missing required key",
    ):
        state.require(
            "does_not_exist"
        )


@pytest.mark.asyncio
async def test_pipeline_stage_order_is_configurable() -> None:
    execution_order: list[str] = []

    class StageA:

        @property
        def name(self) -> str:
            return "a"

        async def execute(
            self,
            state: PipelineState,
            context: SessionContext,
        ) -> PipelineState:
            execution_order.append("a")
            return state

    class StageB:

        @property
        def name(self) -> str:
            return "b"

        async def execute(
            self,
            state: PipelineState,
            context: SessionContext,
        ) -> PipelineState:
            execution_order.append("b")
            return state

    pipeline = SequentialPipeline(
        name="configurable",
        stages=[
            StageB(),
            StageA(),
        ],
    )

    await pipeline.execute(
        state=PipelineState(),
        context=SessionContext(
            session_id="order-test",
        ),
    )

    assert execution_order == [
        "b",
        "a",
    ]