from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import Runnable


def build_chain(model: BaseChatModel, system_prompt: str) -> Runnable:
    """prompt | model. Input: {"history": [messages], "input": str}; output: AIMessage.

    The system prompt is passed as a partial variable so braces in it (code samples)
    are never parsed as template fields.
    """
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "{system_prompt}"),
            MessagesPlaceholder("history"),
            ("human", "{input}"),
        ]
    ).partial(system_prompt=system_prompt)
    return prompt | model
