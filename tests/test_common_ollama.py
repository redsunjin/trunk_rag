from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from common import build_ollama_messages, build_ollama_response_message


def test_build_ollama_messages_maps_roles():
    payload = build_ollama_messages(
        [
            SystemMessage(content="시스템"),
            HumanMessage(content="질문"),
            AIMessage(content="답변"),
        ]
    )

    assert payload == [
        {"role": "system", "content": "시스템"},
        {"role": "user", "content": "질문"},
        {"role": "assistant", "content": "답변"},
    ]


def test_build_ollama_response_message_uses_thinking_when_content_empty():
    message = build_ollama_response_message(
        {
            "message": {
                "role": "assistant",
                "content": "",
                "thinking": "중간 추론",
            }
        }
    )

    assert message.content == "중간 추론"
    assert message.additional_kwargs["thinking"] == "중간 추론"
