from __future__ import annotations

import math
from collections.abc import Mapping

from app.core.openai.requests import ResponsesRequest
from app.core.types import JsonValue
from app.modules.proxy.replay_safety import responses_payload_is_account_neutral_fresh_replay

_MESSAGE_METADATA_FIELDS = frozenset({"turn_id", "create_time", "content_item_kinds", "content_item_metadata"})
_CLIENT_METADATA_FIELDS = frozenset(
    {
        "root_turn_id",
        "session_id",
        "thread_id",
        "turn_id",
        "parent_response_id",
        "guardian_credits_requested",
        "x-codex-installation-id",
        "x-codex-parent-thread-id",
        "x-codex-turn-metadata",
        "x-codex-window-id",
        "x-openai-subagent",
        "x-codex-ws-stream-request-start-ms",
        "ws_request_header_x_openai_internal_codex_responses_lite",
    }
)


def guardian_http_has_inline_full_context(payload: ResponsesRequest) -> bool:
    """Recognize a native Guardian full HTTP prompt without editing its body.

    Inline IDs/provenance are labels, and encrypted reasoning carries its bytes
    in the request. They must all reach the provider unchanged. A validation-only
    view checks the visible messages and declaration-only tools with the shared
    classifier; stored objects, hosted tools, pending calls and incomplete
    reasoning remain on the continuity path. This is not a generic replay rule.
    """
    try:
        return _guardian_http_has_inline_full_context(payload)
    except TypeError:
        # Extra nested fields are legal JSON, not fully schema-constrained.
        # An unhashable discriminator in this pure classification step makes
        # the body ineligible; it must not turn the route into an HTTP 500.
        return False


def _guardian_http_has_inline_full_context(payload: ResponsesRequest) -> bool:
    if (
        payload.model != "codex-auto-review"
        or payload.store
        or payload.previous_response_id is not None
        or payload.conversation is not None
        or not isinstance(payload.input, list)
        or not payload.input
    ):
        return False
    validation = dict(payload.to_replay_safety_payload())
    if not _local_tool_choice(validation.get("tool_choice")):
        return False
    metadata = validation.get("client_metadata")
    if metadata is not None and not (
        isinstance(metadata, dict)
        and set(metadata) <= _CLIENT_METADATA_FIELDS
        and all(isinstance(value, str) for value in metadata.values())
    ):
        return False
    validation.pop("client_metadata", None)
    reasoning = validation.get("reasoning")
    if isinstance(reasoning, dict) and "context" in reasoning:
        if reasoning["context"] not in (None, "auto", "all_turns", "last_turn", "current_turn"):
            return False
        validation["reasoning"] = {key: value for key, value in reasoning.items() if key != "context"}
    visible: list[JsonValue] = []
    pending_reasoning = False
    last_user = last_assistant = -1
    for index, item in enumerate(payload.input):
        if not isinstance(item, dict):
            return False
        if item.get("id") is not None and not isinstance(item["id"], str):
            return False
        kind = item.get("type")
        if kind == "reasoning":
            if not _inline_reasoning(item):
                return False
            pending_reasoning = True
            continue
        candidate = dict(item)
        candidate.pop("id", None)
        if kind == "additional_tools":
            tools = _declarations(item.get("tools"))
            if tools is None:
                return False
            candidate["tools"] = tools
        elif kind in (None, "message"):
            role = item.get("role")
            if role == "assistant":
                if item.get("status") not in (None, "completed"):
                    return False
                if item.get("phase") in (None, "final_answer"):
                    pending_reasoning = False
                last_assistant = index
            elif pending_reasoning:
                return False
            if role == "user":
                last_user = index
            if not _message_metadata(item.get("internal_chat_message_metadata_passthrough")):
                return False
            candidate.pop("internal_chat_message_metadata_passthrough", None)
            content = item.get("content")
            if isinstance(content, list) and any(
                not isinstance(part, dict) or part.get("type") not in {"input_text", "output_text", "text", "refusal"}
                for part in content
            ):
                return False
        else:
            return False
        visible.append(candidate)
    if pending_reasoning or last_user <= last_assistant:
        return False
    validation["input"] = visible
    if validation.get("tools") is not None:
        tools = _declarations(validation["tools"])
        if tools is None:
            return False
        validation["tools"] = tools
    return responses_payload_is_account_neutral_fresh_replay(validation)


def _local_tool_choice(value: JsonValue | None) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value in {"auto", "none", "required"}
    if not isinstance(value, dict) or not set(value) <= {"type", "name"}:
        return False
    name = value.get("name")
    return value.get("type") in ("function", "custom") and isinstance(name, str) and bool(name.strip())


def _declarations(value: JsonValue, depth: int = 0) -> list[JsonValue] | None:
    if not isinstance(value, list) or depth > 2:
        return None
    flattened: list[JsonValue] = []
    for tool in value:
        if not isinstance(tool, dict):
            return None
        if tool.get("type") == "namespace":
            name = tool.get("name")
            if (
                not set(tool) <= {"type", "name", "description", "tools"}
                or not isinstance(name, str)
                or not name.strip()
                or (tool.get("description") is not None and not isinstance(tool["description"], str))
            ):
                return None
            children = _declarations(tool.get("tools"), depth + 1)
            if children is None:
                return None
            flattened.extend(children)
        elif tool.get("type") in {"function", "custom"}:
            flattened.append(tool)
        else:
            return None
    return flattened


def _inline_reasoning(item: Mapping[str, JsonValue]) -> bool:
    encrypted = item.get("encrypted_content")
    summary = item.get("summary")
    return (
        set(item)
        <= {"type", "id", "summary", "encrypted_content", "status", "internal_chat_message_metadata_passthrough"}
        and isinstance(encrypted, str)
        and bool(encrypted.strip())
        and item.get("status") in (None, "completed")
        and _message_metadata(item.get("internal_chat_message_metadata_passthrough"))
        and isinstance(summary, list)
        and all(
            isinstance(part, dict)
            and set(part) <= {"type", "text"}
            and part.get("type") == "summary_text"
            and isinstance(part.get("text"), str)
            for part in summary
        )
    )


def _message_metadata(value: JsonValue | None) -> bool:
    if value is None:
        return True
    if not isinstance(value, dict) or not set(value) <= _MESSAGE_METADATA_FIELDS:
        return False
    turn_id = value.get("turn_id")
    if not isinstance(turn_id, str) or not turn_id.strip():
        return False
    created = value.get("create_time")
    if created is not None:
        if isinstance(created, bool) or not isinstance(created, (int, float)):
            return False
        if isinstance(created, float) and not math.isfinite(created):
            return False
    kinds = value.get("content_item_kinds")
    if kinds is not None and not (isinstance(kinds, list) and all(isinstance(kind, str) for kind in kinds)):
        return False
    provenance_items = value.get("content_item_metadata")
    if provenance_items is None:
        return True
    if not isinstance(provenance_items, list):
        return False
    for item in provenance_items:
        if item is None:
            continue
        if not isinstance(item, dict) or set(item) != {"provenance"}:
            return False
        provenance = item["provenance"]
        if not (
            isinstance(provenance, dict)
            and set(provenance) <= {"type", "hook"}
            and isinstance(provenance.get("type"), str)
            and ("hook" not in provenance or isinstance(provenance["hook"], bool))
        ):
            return False
    return True
