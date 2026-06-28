from openai import OpenAI
from app.core.config import OPENAI_TRANSLATION_MODEL

client = OpenAI()


def translate(text: str, target_language: str = "English") -> str:
    response = client.responses.create(
        model=OPENAI_TRANSLATION_MODEL,
        input=f"""
You are Waaxalma, a voice translation assistant.

Translate the following text into {target_language}.
Keep the meaning faithful.
Use natural spoken language.
Return only the translation.

Text:
{text}
"""
    )

    return response.output_text.strip()