import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.getenv("GROK_API_KEY"), base_url="https://api.groq.com/openai/v1")


def chat_about_image(caption: str, objects: list[dict], history: list[dict], user_message: str) -> tuple[str, int]:
    object_summary = ", ".join(
        [f"{item.get('label', 'unknown')} ({item.get('confidence', 0):.2f})" for item in objects]
    ) or "No objects detected"

    system_prompt = (
        "You are an AI assistant. The user is asking about a photo. "
        f"Caption: {caption}. "
        f"Detected objects: {object_summary}. "
        "Answer questions about this image."
    )

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=messages,
        temperature=0.3,
    )

    reply = response.choices[0].message.content or "I could not generate a response."
    tokens_used = response.usage.total_tokens if response.usage else 0
    return reply, tokens_used
