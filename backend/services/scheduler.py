# -*- coding: utf-8 -*-
"""AI 智能排期引擎 — 查找空闲时间段并智能评分"""
from datetime import date, datetime, timedelta


def _parse_time_safe(iso_str: str) -> datetime:
    """安全解析 ISO 时间字符串"""
    try:
        return datetime.fromisoformat(iso_str)
    except (ValueError, TypeError):
        return datetime.min


def _hour_to_minutes(h: float) -> int:
    return int(h * 60)


def find_free_slots(
    events: list[dict],
    date_start: str,
    date_end: str,
    duration_minutes: int,
    prefer_morning: bool = False,
    top_k: int = 5,
) -> list[dict]:
    """在日期范围内查找空闲时段并智能评分排序。

    Args:
        events: 现有事件列表，每个含 startTime / endTime
        date_start: 起始日期 YYYY-MM-DD
        date_end: 结束日期 YYYY-MM-DD
        duration_minutes: 需要的时长（分钟）
        prefer_morning: 是否优先上午
        top_k: 返回前 K 个结果

    Returns:
        评分排序后的空闲时段列表
    """
    start = datetime.strptime(date_start, "%Y-%m-%d")
    end = datetime.strptime(date_end, "%Y-%m-%d") + timedelta(days=1)

    # 定义每天的工作时间窗口: 8:00 - 20:00
    day_start_hour = 8
    day_end_hour = 20

    # 收集每天内的事件占用区间
    busy: dict[str, list[tuple[datetime, datetime]]] = {}
    for e in events:
        es = _parse_time_safe(e.get("startTime", ""))
        ee = _parse_time_safe(e.get("endTime", ""))
        if es == datetime.min or ee == datetime.min:
            continue
        if e.get("isAllDay"):
            continue
        # Clip to our search window
        if ee <= start or es >= end:
            continue
        es_clamped = max(es, start)
        ee_clamped = min(ee, end)
        day_key = es_clamped.strftime("%Y-%m-%d")
        if day_key not in busy:
            busy[day_key] = []
        busy[day_key].append((es_clamped, ee_clamped))

    # Generate free slots per day
    all_slots: list[dict] = []
    current = start
    while current < end:
        day_key = current.strftime("%Y-%m-%d")
        day_busy = sorted(busy.get(day_key, []), key=lambda x: x[0])

        # Build free intervals for this day
        day_start_dt = current.replace(hour=day_start_hour, minute=0, second=0, microsecond=0)
        day_end_dt = current.replace(hour=day_end_hour, minute=0, second=0, microsecond=0)

        free_from = day_start_dt
        for b_start, b_end in day_busy:
            if b_start > free_from:
                gap = (b_start - free_from).total_seconds() / 60
                if gap >= duration_minutes:
                    all_slots.append({
                        "date": day_key,
                        "start": free_from.strftime("%H:%M"),
                        "end": b_start.strftime("%H:%M"),
                        "duration_minutes": int(gap),
                        "day_of_week": free_from.weekday(),
                    })
            free_from = max(free_from, b_end)

        # After last busy interval
        if day_end_dt > free_from:
            gap = (day_end_dt - free_from).total_seconds() / 60
            if gap >= duration_minutes:
                all_slots.append({
                    "date": day_key,
                    "start": free_from.strftime("%H:%M"),
                    "end": day_end_dt.strftime("%H:%M"),
                    "duration_minutes": int(gap),
                    "day_of_week": free_from.weekday(),
                })

        current += timedelta(days=1)

    # Score each slot
    for slot in all_slots:
        slot["score"] = _score_slot(slot, duration_minutes, prefer_morning)

    # Sort by score descending, take top_k
    all_slots.sort(key=lambda s: s["score"], reverse=True)
    result = all_slots[:top_k]

    # Generate natural language suggestion
    for slot in result:
        slot["suggestion"] = _format_suggestion(slot)

    return result


def _score_slot(slot: dict, needed_min: int, prefer_morning: bool) -> float:
    """对空闲时段打分 (0-100)"""
    score = 50.0  # baseline

    start_hour = int(slot["start"].split(":")[0])

    # 1. Morning preference (8-12)
    if prefer_morning:
        if start_hour < 10:
            score += 25
        elif start_hour < 12:
            score += 15
    else:
        # General: morning is still slightly preferred
        if start_hour < 10:
            score += 10
        elif start_hour < 12:
            score += 5

    # 2. Afternoon penalty (13-14 is lunch, lower energy)
    if 12 <= start_hour < 14:
        score -= 8

    # 3. Evening penalty (18+ is late)
    if start_hour >= 18:
        score -= 15

    # 4. Weekday bonus
    if slot["day_of_week"] < 5:
        score += 5

    # 5. Duration bonus: prefer slots that are just-right (not too large fragments)
    ratio = needed_min / max(slot["duration_minutes"], 1)
    if 0.7 <= ratio <= 1.3:
        score += 10  # good fit
    elif slot["duration_minutes"] >= needed_min * 3:
        score += 3   # plenty of room but less efficient

    # 6. Avoid fragmenting: penalize very short leftover after
    leftover = slot["duration_minutes"] - needed_min
    if 0 < leftover < 30:
        score -= 5  # creates a fragmented small slot

    return max(0, min(100, score))


def _format_suggestion(slot: dict) -> str:
    """生成自然语言建议"""
    wd = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    dw = wd[slot["day_of_week"]]
    return f"{slot['date']}（{dw}）{slot['start']}-{slot['end']}，共{slot['duration_minutes']}分钟空闲"


def get_energy_curve_score(hour: int) -> float:
    """精力曲线评分 (0-1)，基于通用认知规律：
    - 8-10: 高峰（深度工作）
    - 10-11: 良好
    - 11-12: 下降
    - 13-14: 低谷（午餐后）
    - 15-17: 第二高峰
    - 18+: 下降
    """
    if 8 <= hour < 10:
        return 0.95
    elif 10 <= hour < 11:
        return 0.80
    elif 11 <= hour < 12:
        return 0.60
    elif 12 <= hour < 14:
        return 0.30
    elif 14 <= hour < 17:
        return 0.75
    elif 17 <= hour < 19:
        return 0.50
    else:
        return 0.25
