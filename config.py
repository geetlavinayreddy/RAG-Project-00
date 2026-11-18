import os

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()


def generate_answer(question: str, context: list[str]) -> str:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY is missing. Add it to a .env file before asking questions."
        )

    client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")
    context_text = "\n\n".join(context)
    prompt = (
        "You are Super Jarvis, a helpful PDF assistant. "
        "Answer only from the supplied context. If the context does not contain "
        "the answer, say that you could not find it in the documents.\n\n"
        f"Context:\n{context_text}\n\n"
        f"Question:\n{question}"
    )
    response = client.chat.completions.create(
        model=os.getenv("OPENROUTER_MODEL", "openrouter/free"),
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    answer = response.choices[0].message.content
    if not answer:
        raise RuntimeError("OpenRouter returned an empty answer.")
    return answer
