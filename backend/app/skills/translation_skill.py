from app.providers.base_provider import BaseTranslationProvider


class TranslationSkill:
    def __init__(self, provider: BaseTranslationProvider):
        self.provider = provider

    def execute(self, text: str, target_language: str = "English") -> str:
        return self.provider.translate(
            text=text,
            target_language=target_language,
        )