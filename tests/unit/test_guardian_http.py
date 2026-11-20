from __future__ import annotations

from copy import deepcopy

import pytest

from app.core.openai.requests import ResponsesRequest
from app.modules.proxy.guardian_http import guardian_http_has_inline_full_context


def guardian_body() -> dict:
    metadata = {
        "turn_id": "review_previous",
        "create_time": 123.5,
        "content_item_kinds": ["text"],
        "content_item_metadata": [{"provenance": {"type": "user", "hook": False}}],
    }
    return {
        "model": "codex-auto-review",
        "instructions": "Apply the complete approval policy.",
        "store": False,
        "parallel_tool_calls": False,
        "client_metadata": {
            "x-openai-subagent": "guardian",
            "parent_response_id": "resp_main_new",
            "root_turn_id": "root",
            "session_id": "session",
            "thread_id": "thread",
            "turn_id": "turn",
            "x-codex-window-id": "window:1",
        },
        "input": [
            {
                "type": "additional_tools",
                "role": "developer",
                "id": "tools_local",
                "tools": [
                    {
                        "type": "namespace",
                        "name": "functions",
                        "description": "Review tools",
                        "tools": [
                            {"type": "function", "name": "evaluate", "parameters": {"type": "object"}},
                            {"type": "custom", "name": "record", "format": {"type": "text"}},
                        ],
                    },
                ],
            },
            {
                "type": "message",
                "role": "developer",
                "id": "policy_local",
                "content": [{"type": "input_text", "text": "Preserve the policy and user authorization."}],
                "internal_chat_message_metadata_passthrough": metadata,
            },
            {
                "type": "message",
                "role": "user",
                "id": "user_previous",
                "content": [{"type": "input_text", "text": "Review the first harmless command."}],
            },
            {
                "type": "reasoning",
                "id": "rs_previous",
                "summary": [],
                "encrypted_content": "synthetic-inline-ciphertext",
                "internal_chat_message_metadata_passthrough": {"turn_id": "review_previous"},
            },
            {
                "type": "message",
                "role": "assistant",
                "id": "msg_previous",
                "phase": "final_answer",
                "content": [{"type": "output_text", "text": "The first review is complete."}],
            },
            {
                "type": "message",
                "role": "user",
                "id": "user_new",
                "content": [{"type": "input_text", "text": "Review this new harmless command."}],
            },
        ],
    }


def test_guardian_inline_context_keeps_all_policy_and_encrypted_history_unchanged():
    payload = ResponsesRequest.model_validate(guardian_body())
    before = deepcopy(payload.to_payload())
    assert guardian_http_has_inline_full_context(payload)
    assert payload.to_payload() == before


@pytest.mark.parametrize(
    "change",
    [
        {"previous_response_id": "resp_owner"},
        {"conversation": "conv_owner"},
        {"input": [{"type": "item_reference", "id": "item_owner"}]},
        {"input": [{"type": "function_call_output", "call_id": "missing", "output": "done"}]},
        {"input": [{"type": "input_file", "file_id": "file_owner"}]},
        {"input": [{"type": "reasoning", "id": "rs_owner"}]},
        {"input": [{"type": "compaction", "encrypted_content": "opaque_compaction"}]},
        {"client_metadata": {"unknown_owner_state": "opaque"}},
    ],
)
def test_guardian_inline_context_rejects_external_or_unknown_state(change):
    body = guardian_body() | change
    assert not guardian_http_has_inline_full_context(ResponsesRequest.model_validate(body))


@pytest.mark.parametrize("hosted_type", ["file_search", "code_interpreter", "mcp"])
def test_guardian_inline_context_rejects_hosted_namespace_tools(hosted_type):
    body = guardian_body()
    body["input"][0]["tools"][0]["tools"] = [{"type": hosted_type}]
    assert not guardian_http_has_inline_full_context(ResponsesRequest.model_validate(body))


def test_guardian_inline_context_rejects_unsettled_reasoning():
    body = guardian_body()
    del body["input"][4]
    assert not guardian_http_has_inline_full_context(ResponsesRequest.model_validate(body))


@pytest.mark.parametrize(
    "choice",
    [
        {"type": "web_search"},
        {"type": "web_search_preview"},
        {"type": "allowed_tools", "mode": "auto", "tools": [{"type": "web_search"}]},
    ],
)
def test_guardian_inline_context_rejects_hosted_tool_choices(choice):
    body = guardian_body() | {"tool_choice": choice}
    assert not guardian_http_has_inline_full_context(ResponsesRequest.model_validate(body))


@pytest.mark.parametrize(
    "choice",
    [
        "auto",
        "none",
        "required",
        {"type": "function", "name": "functions.evaluate"},
        {"type": "custom", "name": "functions.record"},
    ],
)
def test_guardian_inline_context_accepts_local_tool_choices(choice):
    body = guardian_body() | {"tool_choice": choice}
    assert guardian_http_has_inline_full_context(ResponsesRequest.model_validate(body))


@pytest.mark.parametrize("phase", [None, "final_answer"])
def test_failed_verdict_does_not_complete_inline_reasoning(phase):
    body = guardian_body()
    body["input"][4].update(status="failed", phase=phase)
    assert not guardian_http_has_inline_full_context(ResponsesRequest.model_validate(body))


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("input", 5, "content", 0, "type"), []),
        (("input", 5, "content", 0, "type"), {}),
        (("input", 0, "tools", 0, "tools", 0, "type"), []),
        (("input", 0, "tools", 0, "tools", 0, "type"), {}),
        (("input", 5, "role"), []),
        (("input", 4, "phase"), {}),
        (("input", 0, "tools", 0, "tools", 1, "format", "type"), []),
        (("tool_choice",), {"type": []}),
    ],
)
def test_guardian_inline_context_treats_malformed_discriminators_as_ineligible(path, value):
    body = guardian_body()
    target = body
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    assert not guardian_http_has_inline_full_context(ResponsesRequest.model_validate(body))
