from __future__ import annotations

from collections.abc import Iterable


ALLOWED_ACTIONS = {"观察", "等待回调", "排除"}
BANNED_TERMS = {
    "买入",
    "卖出",
    "满仓",
    "目标价",
    "加仓",
    "减仓",
    "建仓",
    "清仓",
}


def validate_action(action: str) -> str:
    if action not in ALLOWED_ACTIONS:
        allowed = "、".join(sorted(ALLOWED_ACTIONS))
        raise ValueError(f"建议动作只能使用：{allowed}")
    return action


def assert_no_banned_terms(values: Iterable[object]) -> None:
    text = "\n".join("" if value is None else str(value) for value in values)
    hits = sorted(term for term in BANNED_TERMS if term in text)
    if hits:
        raise ValueError(f"输出中包含禁用交易措辞：{', '.join(hits)}")
