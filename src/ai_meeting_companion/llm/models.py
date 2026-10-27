from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel

FAST_MODE_BETA = "fast-mode-2026-02-01"


def make_chat_model(
    model: str, api_key: str, max_tokens: int = 1024, *, fast: bool = False, effort: str = ""
) -> BaseChatModel:
    """``fast`` turns on Anthropic fast mode (Opus only, Claude API only): same model, up to ~2.5x faster output,
    premium price. It needs the beta endpoint + beta flag + ``speed="fast"`` on every request.

    ``effort`` (low|medium|high|xhigh|max) is how hard a thinking model reasons; empty keeps the model's own default
    (``medium`` on Opus 5.5, ``high`` on Sonnet 5.5). Lower is faster but shallower."""
    from langchain_anthropic import ChatAnthropic

    extra: dict = {}
    if fast:
        extra.update(betas=[FAST_MODE_BETA], model_kwargs={"speed": "fast"})
    if effort:
        extra["output_config"] = {"effort": effort}
    return ChatAnthropic(model=model, api_key=api_key, max_tokens=max_tokens, timeout=60, max_retries=2, **extra)
