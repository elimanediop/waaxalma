from app.providers.base_provider import BaseSpeechProvider


class SpeechSkill:
    def __init__(self, provider: BaseSpeechProvider):
        self.provider = provider

    def execute(self, text: str, output_filename: str) -> str:
        return self.provider.speak(
            text=text,
            output_filename=output_filename,
        )