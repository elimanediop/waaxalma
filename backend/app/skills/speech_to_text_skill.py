from app.providers.base_provider import BaseSpeechToTextProvider


class SpeechToTextSkill:
    def __init__(self, provider: BaseSpeechToTextProvider):
        self.provider = provider

    def execute(self, audio_path: str) -> str:
        return self.provider.transcribe(audio_path)