import pytest

from app.core.session_context import SessionContext
from app.pipelines.pipeline_state import PipelineState
from app.pipelines.sequential_pipeline import SequentialPipeline
from app.registry.pipeline_registry import PipelineRegistry


class FakeStage:

    def __init__(
        self,
        name: str,
    ) -> None:
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    async def execute(
        self,
        state: PipelineState,
        context: SessionContext,
    ) -> PipelineState:
        return state


def create_pipeline(
    name: str,
) -> SequentialPipeline:
    return SequentialPipeline(
        name=name,
        stages=[
            FakeStage(
                name="fake-stage",
            ),
        ],
    )


def test_register_and_get_pipeline() -> None:
    registry = PipelineRegistry()

    pipeline = create_pipeline(
        "interpreter.text"
    )

    registry.register(
        pipeline
    )

    resolved = registry.get(
        "interpreter.text"
    )

    assert resolved is pipeline


def test_contains_registered_pipeline() -> None:
    registry = PipelineRegistry()

    pipeline = create_pipeline(
        "interpreter.audio"
    )

    registry.register(
        pipeline
    )

    assert registry.contains(
        "interpreter.audio"
    )

    assert not registry.contains(
        "unknown"
    )


def test_duplicate_pipeline_registration_is_rejected() -> None:
    registry = PipelineRegistry()

    first_pipeline = create_pipeline(
        "interpreter.text"
    )

    second_pipeline = create_pipeline(
        "interpreter.text"
    )

    registry.register(
        first_pipeline
    )

    with pytest.raises(
        ValueError,
        match="already registered",
    ):
        registry.register(
            second_pipeline
        )


def test_unknown_pipeline_is_rejected() -> None:
    registry = PipelineRegistry()

    with pytest.raises(
        KeyError,
        match="not registered",
    ):
        registry.get(
            "unknown"
        )


def test_pipeline_names_are_sorted() -> None:
    registry = PipelineRegistry()

    registry.register(
        create_pipeline(
            "interpreter.text"
        )
    )

    registry.register(
        create_pipeline(
            "interpreter.audio"
        )
    )

    registry.register(
        create_pipeline(
            "translation.text"
        )
    )

    assert registry.names() == [
        "interpreter.audio",
        "interpreter.text",
        "translation.text",
    ]

def test_custom_pipeline_can_be_registered() -> None:
    registry = PipelineRegistry()

    pipeline = SequentialPipeline(
        name="custom.workflow",
        stages=[
            FakeStage(
                name="custom-stage",
            ),
        ],
    )

    registry.register(
        pipeline
    )

    assert registry.contains(
        "custom.workflow"
    )

    assert (
        registry
        .get("custom.workflow")
        .stage_names
    ) == [
        "custom-stage",
    ]