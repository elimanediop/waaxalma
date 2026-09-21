from dataclasses import dataclass, field
from typing import Any


@dataclass
class PipelineState:
    data: dict[str, Any] = field(
        default_factory=dict,
    )

    def get(
        self,
        key: str,
        default: Any = None,
    ) -> Any:
        return self.data.get(
            key,
            default,
        )

    def require(
        self,
        key: str,
    ) -> Any:
        if key not in self.data:
            raise ValueError(
                f"Pipeline state is missing required key '{key}'."
            )

        return self.data[key]

    def set(
        self,
        key: str,
        value: Any,
    ) -> None:
        self.data[key] = value

    def to_dict(self) -> dict[str, Any]:
        return dict(self.data)