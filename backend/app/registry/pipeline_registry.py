from app.pipelines.pipeline import Pipeline


class PipelineRegistry:

    def __init__(self) -> None:
        self._pipelines: dict[str, Pipeline] = {}

    def register(
        self,
        pipeline: Pipeline,
    ) -> None:
        if pipeline.name in self._pipelines:
            raise ValueError(
                f"Pipeline '{pipeline.name}' is already registered."
            )

        self._pipelines[pipeline.name] = pipeline

    def get(
        self,
        name: str,
    ) -> Pipeline:
        pipeline = self._pipelines.get(name)

        if pipeline is None:
            raise KeyError(
                f"Pipeline '{name}' is not registered."
            )

        return pipeline

    def contains(
        self,
        name: str,
    ) -> bool:
        return name in self._pipelines

    def names(self) -> list[str]:
        return sorted(
            self._pipelines.keys()
        )