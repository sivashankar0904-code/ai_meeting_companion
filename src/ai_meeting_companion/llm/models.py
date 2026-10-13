from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel


def make_chat_model(model: str, api_key: str, max_tokens: int = 1024) -> BaseChatModel:
    from langchain_anthropic import ChatAnthropic

    return ChatAnthropic(model=model, api_key=api_key, max_tokens=max_tokens, timeout=60, max_retries=2)
