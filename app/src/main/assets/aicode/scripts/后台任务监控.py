#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AiCode 后台任务与用量面板。

后台任务来自 App 注入的 AICODE_RUNNING_TASKS（终端会话、运行中的工具、子代理），
不再扫描 ps：容器里 PRoot 的 /proc 信息不完整，也分不清用户任务与 App 调用链。

余额按常见供应商接口查一次，查到才在标题行（header.balance）与收起态显示；
查不到就完全不显示，不占位。
"""

import json
import os
import re
import urllib.request

MAX_LISTED = 8

# 把任务识别成人类可读的名字。顺序：先匹配动作再匹配工具名，
# 否则 `pip install pytest` 会被 pytest 误判成「测试」。
TASK_LABELS = [
    (re.compile(r"assemble\w*|bundle\w*|gradlew|\bgradle\b", re.I), "Android 构建"),
    (re.compile(r"\bpip3?\s+install\b|\bpoetry\b|\bconda\b|\buv\s+pip\b", re.I), "Python 安装"),
    (re.compile(r"\b(npm|pnpm|yarn)\s+(install|add|ci)\b", re.I), "Node 安装"),
    (re.compile(r"\bgit\s+(clone|fetch|pull|push)\b", re.I), "Git 同步"),
    (re.compile(r"\bcurl\b|\bwget\b", re.I), "下载"),
    (re.compile(r"\bffmpeg\b", re.I), "媒体处理"),
    (re.compile(r"\bcargo\s+(build|test|run)\b|\brustc\b", re.I), "Rust 编译"),
    (re.compile(r"\bmake\b|\bcmake\b|\bninja\b", re.I), "源码编译"),
    (re.compile(r"\bpytest\b|\bjest\b|\bvitest\b|go\s+test|unittest", re.I), "测试"),
    (re.compile(r"\bvite\b|\bwebpack\b|\besbuild\b", re.I), "前端构建"),
    (re.compile(r"\bnpm\s+run\b|\byarn\s+run\b|\bpnpm\s+run\b", re.I), "Node 任务"),
    (re.compile(r"\bpython3?\b", re.I), "Python 脚本"),
    (re.compile(r"\bnode\b|\bnpx\b", re.I), "Node 脚本"),
    (re.compile(r"\bjava\b|\bkotlin\b", re.I), "JVM 任务"),
]


def _as_int(value, default=0):
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def format_tokens(value):
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "0k"
    if v >= 999_950:
        return f"{v / 1_000_000.0:.2f}".rstrip("0").rstrip(".") + "M"
    if v <= 0:
        return "0k"
    return f"{v / 1000.0:.1f}".rstrip("0").rstrip(".") + "k"


def format_price(value):
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "$0"
    if v <= 0:
        return "$0"
    if v >= 100:
        text = f"{v:.4g}"
    elif v >= 1:
        text = f"{v:.2f}"
    elif v >= 0.01:
        text = f"{v:.3f}"
    else:
        text = f"{v:.4f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return "$" + text


def format_duration(seconds):
    try:
        total = int(max(0, float(seconds)))
    except (TypeError, ValueError):
        return "刚刚"
    if total < 60:
        return f"{total}秒"
    if total < 3600:
        return f"{total // 60}分{total % 60:02d}秒"
    return f"{total // 3600}时{(total % 3600) // 60:02d}分"


def _format_balance(amount, currency):
    try:
        value = float(amount)
    except (TypeError, ValueError):
        return None
    symbol = "¥" if str(currency).upper() == "CNY" else "$"
    if abs(value) >= 1000:
        text = f"{value:,.2f}"
    elif abs(value) >= 1:
        text = f"{value:.2f}"
    else:
        text = f"{value:.4f}".rstrip("0").rstrip(".")
    return f"{symbol}{text}"


def _http_get_json(url, api_key, timeout=3.0):
    request = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "User-Agent": "AiCode-dashboard",
    })
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8", "replace"))


def query_balance():
    """按常见供应商的余额接口查一次；不支持或失败返回 None（界面就不显示余额）。"""
    base = os.environ.get("AICODE_PROVIDER_BASE_URL", "").strip().rstrip("/")
    api_key = os.environ.get("AICODE_PROVIDER_API_KEY", "").strip()
    if not base or not api_key:
        return None
    root = base[:-3] if base.endswith("/v1") else base
    lower = base.lower()
    try:
        if "deepseek" in lower:
            data = _http_get_json(f"{root}/user/balance", api_key)
            infos = data.get("balance_infos") or []
            if infos:
                info = infos[0]
                return _format_balance(info.get("total_balance"), info.get("currency", "CNY"))
        if "siliconflow" in lower:
            data = _http_get_json(f"{root}/user/info", api_key)
            amount = data.get("totalBalance")
            if amount is None:
                amount = data.get("balance")
            return _format_balance(amount, "CNY")
        if "openrouter" in lower:
            data = _http_get_json(f"{root}/credits", api_key)
            payload = data.get("data") or {}
            total = float(payload.get("total_credits") or 0)
            used = float(payload.get("total_usage") or 0)
            return _format_balance(total - used, "USD")
    except Exception:
        return None
    return None


def load_tasks():
    raw = os.environ.get("AICODE_RUNNING_TASKS", "").strip()
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return []
    if not isinstance(data, list):
        return []
    return [t for t in data if isinstance(t, dict) and t.get("running", True)]


def describe_task(task):
    text = f"{task.get('detail') or ''} {task.get('title') or ''}"
    for pattern, label in TASK_LABELS:
        if pattern.search(text):
            return label
    return task.get("title") or "任务"


def metric_column(label, value):
    return {
        "type": "Column",
        "width": "1",
        "gap": 1,
        "items": [
            {"type": "TextBlock", "text": label, "size": "Small", "isSubtle": True},
            {"type": "TextBlock", "text": value, "size": "Small", "weight": "Bolder"},
        ],
    }


def metric_group(columns, gap=8):
    return {"type": "ColumnSet", "gap": gap, "columns": columns}


def tasks_card(tasks, balance):
    count = len(tasks)
    named = [(describe_task(t), t) for t in tasks]
    named.sort(key=lambda item: item[1].get("elapsedSec") or 0, reverse=True)
    primary_title, primary = named[0]
    primary_elapsed = format_duration(primary.get("elapsedSec"))

    compact_text = (
        f"**{primary_title}**（{primary_elapsed}）"
        if count == 1
        else f"**{primary_title}** 等 {count} 个任务（最长 {primary_elapsed}）"
    )

    compact_items = [{"type": "StatusDot", "color": "Warning", "size": 8}]
    if balance:
        compact_items.append({"type": "TextBlock", "text": balance, "weight": "Bolder"})
    compact_items.extend([
        {"type": "Badge", "text": f"{count} 个任务", "style": "Warning"},
        {"type": "TextBlock", "text": compact_text, "weight": 1, "color": "Warning"},
        {"type": "ActionButton", "title": "刷新", "action": "refresh", "style": "Subtle"},
    ])

    body = [
        {
            "type": "FactSet",
            "facts": [
                {"title": title, "value": format_duration(t.get("elapsedSec"))}
                for title, t in named[:MAX_LISTED]
            ],
        }
    ]
    if count > MAX_LISTED:
        body.append({
            "type": "TextBlock",
            "text": f"… 另有 {count - MAX_LISTED} 个任务未列出",
            "size": "Small",
            "isSubtle": True,
        })
    body.append({
        "type": "Row",
        "items": [
            {
                "type": "ActionButton",
                "title": "刷新",
                "action": "refresh",
                "style": "Subtle",
                "weight": 1,
            }
        ],
    })

    card = {
        "type": "AdaptiveCard",
        "version": "1.5",
        "compact": {"type": "Row", "items": compact_items},
        "body": body,
    }
    if balance:
        card["header"] = {"balance": balance}
    return card


def idle_card(balance):
    total_in = _as_int(os.environ.get("AICODE_TOTAL_INPUT_TOKENS"))
    total_out = _as_int(os.environ.get("AICODE_TOTAL_OUTPUT_TOKENS"))
    cost_in = os.environ.get("AICODE_MODEL_INPUT_COST_USD_PER_M", "0")
    cost_out = os.environ.get("AICODE_MODEL_OUTPUT_COST_USD_PER_M", "0")
    cost_cache = os.environ.get("AICODE_MODEL_CACHE_READ_COST_USD_PER_M", "0")

    compact_items = [{"type": "StatusDot", "color": "Good", "size": 6}]
    if balance:
        compact_items.append({"type": "TextBlock", "text": balance, "weight": "Bolder"})
    compact_items.extend([
        {"type": "TextBlock", "text": "就绪", "weight": 1},
        {"type": "Badge", "text": "空闲", "style": "Good"},
    ])

    card = {
        "type": "AdaptiveCard",
        "version": "1.5",
        "compact": {"type": "Row", "items": compact_items},
        "body": [
            {
                "type": "ColumnSet",
                "gap": 0,
                "columns": [
                    {
                        "type": "Column",
                        "width": "1",
                        "items": [
                            {
                                "type": "Metric",
                                "label": "后台任务",
                                "value": "无",
                                "color": "Good",
                            },
                            {
                                "type": "ActionButton",
                                "title": "刷新",
                                "action": "refresh",
                                "style": "Subtle",
                            },
                        ],
                    },
                    {
                        "type": "Column",
                        "width": "1.5",
                        "separator": True,
                        "gap": 2,
                        "items": [
                            metric_group([
                                metric_column("输入", format_tokens(total_in)),
                                metric_column("输出", format_tokens(total_out)),
                                metric_column("总计", format_tokens(total_in + total_out)),
                            ]),
                            metric_group([
                                metric_column("输入", format_price(cost_in)),
                                metric_column("输出", format_price(cost_out)),
                                metric_column("缓存", format_price(cost_cache)),
                            ]),
                        ],
                    },
                ],
            }
        ],
    }
    if balance:
        card["header"] = {"balance": balance}
    return card


def main():
    tasks = load_tasks()
    balance = query_balance()
    card = tasks_card(tasks, balance) if tasks else idle_card(balance)
    print(json.dumps(card, ensure_ascii=False))


if __name__ == "__main__":
    main()
