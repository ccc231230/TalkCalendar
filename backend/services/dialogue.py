# -*- coding: utf-8 -*-
"""多轮对话服务 —— LLM + Function Calling + Session 管理"""
import json, os, uuid
from datetime import date, datetime, timedelta
from typing import Any
from openai import AsyncOpenAI

# ---------- LLM client ----------
LLM_BASE = os.getenv("LLM_BASE_URL", "https://api.moonshot.cn/v1")
LLM_KEY = os.getenv("LLM_API_KEY", "sk-wOdkbbpMycLEMPlPgDD123ZrRrpbwmYu5b2AOXHTkIyCGxUa")
LLM_MODEL = os.getenv("LLM_MODEL", "kimi-k2.5")

_client: AsyncOpenAI | None = None

def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(base_url=LLM_BASE, api_key=LLM_KEY)
    return _client

# ---------- 系统提示词 ----------
SYSTEM_PROMPT = """你是 TalkCalendar 的 AI 日程助手。

核心规则：
1. 果断行动，不要反复追问。能从上下文推断的信息直接使用默认值（时长默认1小时，标题从用户话中提取）。
2. 每次最多问一个问题，能不问就不问。
3. 当创建事件发生时间冲突时，告知用户并建议替代时间。
3.5. 当用户询问任何关于日程安排的问题时，必须首先调用 query_events 工具查询实际数据，再根据结果回答。禁止不查数据直接编造回答。
4. 对话简洁，回复控制在3句话以内。
5. 今天日期随请求传入，以系统提供的日期为准。

可用操作：
- create_event: 创建日历事件（默认时长1小时）
- query_events: 查询某天/某周的事件
- delete_event: 删除事件
- find_free_slots: 查找空闲时间段

信息不全时优先用合理默认值直接调工具，不要反复追问。"""

# ---------- Function definitions ----------
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_event",
            "description": "创建一个日历事件。必须在确认所有必要信息（标题、日期、时间）后才调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "事件标题"},
                    "date": {"type": "string", "description": "日期，格式 YYYY-MM-DD"},
                    "start_time": {"type": "string", "description": "开始时间，格式 HH:MM，如 14:30"},
                    "end_time": {"type": "string", "description": "结束时间，格式 HH:MM，如 15:30"},
                    "category": {"type": "string", "enum": ["work", "personal", "health", "other"]},
                    "is_recurring": {"type": "boolean", "description": "是否周期性事件"},
                    "recurrence_rule": {"type": "string", "description": "RRULE 格式，如 FREQ=WEEKLY;BYDAY=MO"},
                },
                "required": ["title", "date", "start_time", "end_time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_events",
            "description": "查询指定日期或日期范围内的事件",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {"type": "string", "description": "查询日期，格式 YYYY-MM-DD"},
                    "date_end": {"type": "string", "description": "结束日期（可选），格式 YYYY-MM-DD"},
                },
                "required": ["date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_event",
            "description": "删除日历事件。必须确认用户确实想删除。",
            "parameters": {
                "type": "object",
                "properties": {
                    "event_id": {"type": "string", "description": "事件 ID"},
                    "title_match": {"type": "string", "description": "按标题模糊匹配删除"},
                    "date": {"type": "string", "description": "限定日期范围，格式 YYYY-MM-DD"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_free_slots",
            "description": "在指定日期范围内查找空闲时间段",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_start": {"type": "string", "description": "开始日期，格式 YYYY-MM-DD"},
                    "date_end": {"type": "string", "description": "结束日期（可选），默认+7天"},
                    "duration_minutes": {"type": "integer", "description": "需要的时长（分钟），默认60"},
                    "prefer_morning": {"type": "boolean", "description": "是否优先上午"},
                },
                "required": ["duration_minutes"],
            },
        },
    },
]

# ---------- Session management ----------
_sessions: dict[str, Any] = {}

class ChatSession:
    def __init__(self, sid: str | None = None):
        self.id = sid or str(uuid.uuid4())[:8]
        self.history: list[dict] = []

    def add_message(self, role: str, content: str | None = None,
                    reasoning_content: str | None = None,
                    tool_calls: list[dict] | None = None,
                    tool_call_id: str | None = None,
                    name: str | None = None):
        msg: dict = {"role": role}
        if content is not None:
            msg["content"] = content
        if reasoning_content is not None:
            msg["reasoning_content"] = reasoning_content
        if tool_calls is not None:
            msg["tool_calls"] = tool_calls
        if tool_call_id is not None:
            msg["tool_call_id"] = tool_call_id
        if name is not None:
            msg["name"] = name
        self.history.append(msg)

def get_or_create_session(session_id: str | None) -> ChatSession:
    if session_id and session_id in _sessions:
        return _sessions[session_id]
    session = ChatSession(session_id)
    _sessions[session.id] = session
    return session

# ---------- Calendar backend ----------
class CalendarBackend:
    def __init__(self):
        self.events: list[dict] = []

    def set_events(self, events: list[dict]):
        existing_ids = {e.get("id") for e in self.events}
        for e in events:
            if e.get("id") not in existing_ids:
                self.events.append(e)
                existing_ids.add(e.get("id"))

    def query(self, date_str: str, date_end: str | None = None):
        from datetime import datetime as dt, timedelta as td
        d_start = dt.strptime(date_str, "%Y-%m-%d")
        d_end = dt.strptime(date_end, "%Y-%m-%d") + td(days=1) if date_end else d_start + td(days=1)
        result = []
        for e in self.events:
            es = dt.fromisoformat(e.get("startTime", ""))
            ee = dt.fromisoformat(e.get("endTime", ""))
            if es < d_end and ee > d_start:
                result.append(e)
        return result

    def find_free_slots(self, date_start: str, date_end: str, duration_min: int, prefer_morning: bool = False):
        from services.scheduler import find_free_slots as ffs
        return ffs(self.events, date_start, date_end, duration_min, prefer_morning)

    def create_event_spec(self, title: str, date: str, start_time: str, end_time: str,
                           category: str = "other", is_recurring: bool = False, recurrence_rule: str = ""):
        st = f"{date}T{start_time}:00"
        et = f"{date}T{end_time}:00"
        colors = {"work": "#4A90D9", "personal": "#7ED321", "health": "#F5A623", "other": "#9B9B9B"}
        return {
            "id": str(uuid.uuid4())[:8],
            "title": title,
            "startTime": st,
            "endTime": et,
            "isAllDay": False,
            "isRecurring": is_recurring,
            "recurrenceRule": recurrence_rule,
            "category": category,
            "color": colors.get(category, "#9B9B9B"),
            "createdAt": datetime.now().isoformat(),
            "description": "",
        }

_backend = CalendarBackend()

# ---------- Tool executor ----------
async def execute_tool(tool_name: str, arguments: dict) -> str:
    try:
        if tool_name == "query_events":
            events = _backend.query(arguments["date"], arguments.get("date_end"))
            return json.dumps({"count": len(events), "events": events}, ensure_ascii=False)

        elif tool_name == "find_free_slots":
            slots = _backend.find_free_slots(
                arguments.get("date_start", date.today().isoformat()),
                arguments.get("date_end", (date.today() + timedelta(days=7)).isoformat()),
                arguments["duration_minutes"],
                arguments.get("prefer_morning", False),
            )
            return json.dumps({"slots": slots}, ensure_ascii=False)

        elif tool_name == "create_event":
            st = f"{arguments['date']}T{arguments['start_time']}:00"
            et = f"{arguments['date']}T{arguments['end_time']}:00"
            conflicts = [e for e in _backend.events
                         if e.get("startTime", "") < et and e.get("endTime", "") > st]
            if conflicts:
                conflict_titles = ", ".join(e.get("title", "?") for e in conflicts[:3])
                return json.dumps({"status": "conflict", "conflicts": conflict_titles,
                                   "suggestion": "该时段与已有事件冲突，请选择其他时间"}, ensure_ascii=False)
            spec = _backend.create_event_spec(**arguments)
            _backend.events.append(spec)
            return json.dumps({"status": "created", "event": spec}, ensure_ascii=False)

        elif tool_name == "delete_event":
            deleted = []
            remaining = []
            for e in _backend.events:
                match = False
                if arguments.get("event_id") and e.get("id") == arguments["event_id"]:
                    match = True
                if arguments.get("title_match") and arguments["title_match"] in e.get("title", ""):
                    match = True
                if match:
                    deleted.append(e)
                else:
                    remaining.append(e)
            _backend.events = remaining
            return json.dumps({"status": "deleted", "count": len(deleted)}, ensure_ascii=False)

        else:
            return json.dumps({"error": f"Unknown tool: {tool_name}"})
    except Exception as e:
        return json.dumps({"error": str(e)})

# ---------- Rule-based fast path (no LLM needed) ----------
QRY_KW = ["查看", "查询", "有什么", "有哪些", "看一下", "看看", "什么安排", "有啥", "查一下", "有什么事", "安排是", "说说", "告诉我", "列出", "显示"]
DEL_KW = ["删除", "取消", "移除", "去掉"]
DAY_MAP_RULE = {"今天": 0, "明天": 1, "后天": 2, "大后天": 3}
WD_MAP_RULE = {
    "周一": 0, "周二": 1, "周三": 2, "周四": 3, "周五": 4, "周六": 5, "周日": 6,
    "星期一": 0, "星期二": 1, "星期三": 2, "星期四": 3, "星期五": 4, "星期六": 5, "星期天": 6, "星期日": 6,
    "下周一": 7, "下周二": 8, "下周三": 9, "下周四": 10, "下周五": 11, "下周六": 12, "下周日": 13,
    "下星期一": 7, "下星期二": 8, "下星期三": 9, "下星期四": 10, "下星期五": 11, "下星期六": 12, "下星期天": 13,
}


def _parse_query_date(text: str):
    today = date.today()
    if any(w in text for w in ["这周", "本周"]):
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=6)
        return start, end
    if any(w in text for w in ["下周"]):
        start = today - timedelta(days=today.weekday()) + timedelta(days=7)
        end = start + timedelta(days=6)
        return start, end
    for kw, offset in DAY_MAP_RULE.items():
        if kw in text:
            d = today + timedelta(days=offset)
            return d, d
    for kw in sorted(WD_MAP_RULE.keys(), key=len, reverse=True):
        if kw in text:
            offset = WD_MAP_RULE[kw]
            today_wd = today.weekday()
            target_wd = offset % 7
            days_ahead = target_wd - today_wd
            if days_ahead < 0:
                days_ahead += 7
            d = today + timedelta(days=days_ahead)
            if offset >= 7:
                d += timedelta(days=7)
            return d, d
    if any(kw in text for kw in QRY_KW):
        return today, today
    return None


def _format_events(events: list[dict]) -> str:
    if not events:
        return None
    header = ["事件", "开始", "结束"]
    rows = []
    max_lens = [len(h) for h in header]
    for e in events:
        title = e.get("title", "未命名")
        st = e.get("startTime", "")
        et = e.get("endTime", "")
        try:
            st_dt = datetime.fromisoformat(st)
            et_dt = datetime.fromisoformat(et)
            if st_dt.tzinfo is not None:
                from datetime import timezone as _tz, timedelta as _td
                cst = _tz(_td(hours=8))
                st_dt = st_dt.astimezone(cst)
                et_dt = et_dt.astimezone(cst)
            st_str = st_dt.strftime('%H:%M')
            et_str = et_dt.strftime('%H:%M')
        except (ValueError, TypeError):
            st_str = "-"
            et_str = "-"
        rows.append([title, st_str, et_str])
        max_lens[0] = max(max_lens[0], len(title))
        max_lens[1] = max(max_lens[1], len(st_str))
        max_lens[2] = max(max_lens[2], len(et_str))
    pad = 2
    def fmt_line(cells):
        return "  ".join(cells[i].ljust(max_lens[i] + pad) for i in range(3))
    result = []
    result.append(fmt_line(header))
    result.append("  ".join("-" * (max_lens[i] + pad) for i in range(3)))
    for row in rows:
        result.append(fmt_line(row))
    return "\n".join(result)


def rule_query(events: list[dict], text: str) -> dict | None:
    has_query_kw = any(kw in text for kw in QRY_KW)
    date_range = _parse_query_date(text)
    # If no query keyword AND no date keyword, skip (not a query)
    if not has_query_kw and date_range is None:
        return None
    if date_range is None:
        return None
    session = get_or_create_session(None)
    start, end = date_range
    matched = []
    for e in events:
        try:
            es = datetime.fromisoformat(e.get("startTime", ""))
            ee = datetime.fromisoformat(e.get("endTime", ""))
            # Normalize to naive datetime for date comparison
            if es.tzinfo is not None:
                es = es.replace(tzinfo=None)
            if ee.tzinfo is not None:
                ee = ee.replace(tzinfo=None)
        except (ValueError, TypeError):
            continue
        if es.date() <= end and ee.date() >= start:
            matched.append(e)
    if start == end:
        if start == date.today():
            date_label = "今天"
        elif start == date.today() + timedelta(days=1):
            date_label = "明天"
        else:
            date_label = start.strftime("%m月%d日")
    else:
        date_label = f"{start.strftime('%m月%d日')} - {end.strftime('%m月%d日')}"
    if not matched:
        return {
            "session_id": session.id,
            "reply": f"{date_label}暂无安排",
            "action": None,
        }
    event_list = _format_events(matched)
    return {
        "session_id": session.id,
        "reply": f"{date_label}的安排：\n{event_list}",
        "action": None,
    }


def rule_delete(events: list[dict], text: str) -> dict | None:
    if not any(kw in text for kw in DEL_KW):
        return None
    clean = text
    for kw in DEL_KW:
        clean = clean.replace(kw, "")
    for kw in list(DAY_MAP_RULE.keys()) + list(WD_MAP_RULE.keys()):
        clean = clean.replace(kw, "")
    import re as _re
    clean = _re.sub(r"\s+", "", clean).strip()
    clean = _re.sub(r"的$", "", clean).strip()  # strip trailing particle
    if not clean or len(clean) < 2:
        return None
    matched = []
    for e in events:
        title = e.get("title", "")
        if clean in title or title in clean:
            matched.append(e)
    session = get_or_create_session(None)
    if not matched:
        return None  # let LLM handle complex delete matching
    if len(matched) == 1:
        e = matched[0]
        return {
            "session_id": session.id,
            "reply": f"确认删除「{e.get('title', '未知')}」吗？请回复「确认」来删除。",
            "action": {"tool": "delete_event", "arguments": {"title_match": clean}, "result": {"status": "pending_confirm", "events": [{"id": e.get("id"), "title": e.get("title")}]}},
        }
    else:
        titles = "、".join(e.get("title", "?") for e in matched[:5])
        return {
            "session_id": session.id,
            "reply": f"找到 {len(matched)} 个匹配的事件：{titles}。请指定要删除哪一个？",
            "action": None,
        }

# ---------- Core dialogue ----------
async def process_message(
    text: str,
    session_id: str | None = None,
    events_json: list[dict] | None = None,
) -> dict:
    """处理用户消息，返回 AI 回复和操作结果"""
    session = get_or_create_session(session_id)
    if events_json is not None:
        _backend.set_events(events_json)

    today = date.today()
    today_context = f"今天是 {today.strftime('%Y年%m月%d日')}（{['周一','周二','周三','周四','周五','周六','周日'][today.weekday()]}）。"

    session.add_message("user", text)

    client = get_client()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT + "\n\n" + today_context},
    ] + session.history

    response = await client.chat.completions.create(
        model=LLM_MODEL,
        messages=messages,
        tools=TOOLS,
        tool_choice="auto",
        temperature=1.0,
        max_tokens=4096,
    )

    msg = response.choices[0].message

    if not msg.tool_calls:
        reply = msg.content or ""
        session.add_message("assistant", reply)
        return {
            "session_id": session.id,
            "reply": reply,
            "action": None,
        }

    session.add_message("assistant", msg.content, reasoning_content=getattr(msg, "reasoning_content", None), tool_calls=[
        {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
        for tc in msg.tool_calls
    ])

    actions = []
    for tc in msg.tool_calls:
        args = json.loads(tc.function.arguments)
        result = await execute_tool(tc.function.name, args)
        session.add_message("tool", result, tool_call_id=tc.id, name=tc.function.name)
        actions.append({"tool": tc.function.name, "arguments": args, "result": json.loads(result)})

    messages2 = [
        {"role": "system", "content": SYSTEM_PROMPT + "\n\n" + today_context},
    ] + session.history

    response2 = await client.chat.completions.create(
        model=LLM_MODEL,
        messages=messages2,
        temperature=1.0,
        max_tokens=4096,
    )

    reply = response2.choices[0].message.content or ""
    session.add_message("assistant", reply)

    return {
        "session_id": session.id,
        "reply": reply,
        "action": actions[0] if len(actions) == 1 else actions,
    }


def mock_reply(text: str) -> dict:
    """Mock 模式：无需 LLM API 时的本地规则对话"""
    import re
    session = get_or_create_session(None)
    today = date.today()

    if any(kw in text for kw in ["找", "空闲", "空档", "安排", "时间", "什么时候"]):
        dur_match = re.search(r'(\d+)\s*(小时|分钟|个钟)', text)
        duration = 60
        if dur_match:
            if dur_match.group(2) in ("小时", "个钟"):
                duration = int(dur_match.group(1)) * 60
            else:
                duration = int(dur_match.group(1))
        return {
            "session_id": session.id,
            "reply": f"好的，我帮你找一下接下来几天至少{duration}分钟的空闲时间。你想安排在上午还是下午？有没有偏好的日期？",
            "action": None,
        }

    if any(kw in text for kw in ["添加", "新建", "创建", "安排", "加入", "加个"]):
        return {
            "session_id": session.id,
            "reply": "收到！请问这个事件的标题是什么？具体想安排在哪天、什么时间？",
            "action": None,
        }

    if any(kw in text for kw in ["查看", "查询", "有什么", "有哪些", "看一下"]):
        return {
            "session_id": session.id,
            "reply": f"好的，今天是{today.strftime('%Y年%m月%d日')}。你想查看哪天的安排？比如「今天」「明天」或者「这周」？",
            "action": None,
        }

    if any(kw in text for kw in ["删除", "取消", "移除", "去掉"]):
        return {
            "session_id": session.id,
            "reply": "你想取消哪个事件？告诉我标题或日期，我帮你找到并确认删除。",
            "action": None,
        }

    return {
        "session_id": session.id,
        "reply": f"好的，我记下了。你想对这个日程做什么操作呢？比如「创建事件」「查看安排」「找空闲时间」都可以告诉我～",
        "action": None,
    }
