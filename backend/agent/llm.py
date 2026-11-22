"""Single file that knows the model provider.  Swap the model here only."""
from __future__ import annotations

import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

import config

load_dotenv()


def get_llm() -> ChatOpenAI:
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise ValueError(
            "OPENROUTER_API_KEY not set. "
            "Copy .env.example → .env and add your key, "
            "or set it as a Vercel environment variable."
        )
    return ChatOpenAI(
        model=config.MODEL,
        base_url="https://openrouter.ai/api/v1",
        api_key=key,
        temperature=0,
        max_tokens=1024,
    )
