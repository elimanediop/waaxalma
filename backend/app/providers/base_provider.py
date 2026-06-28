from abc import ABC, abstractmethod


class BaseTranslationProvider(ABC):
    @abstractmethod
    def translate(self, text: str, target_language: str = "English") -> str:
        pass


class BaseSpeechProvider(ABC):
    @abstractmethod
    def speak(self, text: str, output_filename: str) -> str:
        pass

class BaseSpeechToTextProvider(ABC):
    @abstractmethod
    def transcribe(self, audio_path: str) -> str:
        pass