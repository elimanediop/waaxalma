from typing import Any

from pydantic import BaseModel, Field


class TextTranslationResult(BaseModel):
    source_text: str
    translated_text: str
    source_language: str | None = None
    target_language: str

    quality_accepted: bool
    quality_score: float | None = None
    quality_issues: list[str] = Field(default_factory=list)

    metadata: dict[str, Any] = Field(default_factory=dict)