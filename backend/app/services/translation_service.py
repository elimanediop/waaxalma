from app.observability.operations import observe, record_usage
from app.core.config import OPENAI_API_KEY
from openai import OpenAI
from app.core.config import OPENAI_TRANSLATION_MODEL

client = OpenAI(api_key=OPENAI_API_KEY)


@observe("translation", model=OPENAI_TRANSLATION_MODEL)
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

    record_usage(getattr(response, "usage", None), model=OPENAI_TRANSLATION_MODEL)
    return response.output_text.strip()