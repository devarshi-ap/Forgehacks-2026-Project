import os

from dotenv import load_dotenv
from groq import Groq


load_dotenv()


api_key = os.getenv("GROQ_API_KEY")


if not api_key:

    raise RuntimeError(
        "GROQ_API_KEY is missing from .env"
    )


client = Groq(
    api_key=api_key
)


response = client.chat.completions.create(

    model="openai/gpt-oss-120b",

    messages=[
        {
            "role": "user",
            "content":
                "Reply with exactly one sentence: "
                "StormSignal Module 2 is working."
        }
    ],

    temperature=0.1
)


print()
print("GROQ TEST SUCCESS")
print()
print(
    response.choices[0].message.content
)