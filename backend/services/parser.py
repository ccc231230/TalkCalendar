# -*- coding: utf-8 -*-
"""自然语言解析器 - TalkCalendar"""
import re
from datetime import datetime, timedelta, date
from typing import Optional

CN_NUM = {"一":1,"二":2,"两":2,"三":3,"四":4,"五":5,"六":6,"七":7,"八":8,"九":9,"十":10,"十一":11,"十二":12,"零":0}
ADD_KW = ["添加","新建","创建","安排","加入","增加"]
DEL_KW = ["删除","取消","移除","去掉"]
QRY_KW = ["查看","查询","有什么","有哪些","有什么安排","看一下"]
DAY_MAP = {"今天":0,"明天":1,"后天":2,"大后天":3}
WD_MAP = {"周一":0,"周二":1,"周三":2,"周四":3,"周五":4,"周六":5,"周日":6,"星期一":0,"星期二":1,"星期三":2,"星期四":3,"星期五":4,"星期六":5,"星期日":6,"星期天":6,"下周一":7,"下周二":8,"下周三":9,"下周四":10,"下周五":11,"下周六":12,"下周日":13,"下星期一":7,"下星期二":8,"下星期三":9,"下星期四":10,"下星期五":11,"下星期六":12,"下星期日":13}
RC_WD = {"周一":"MO","周二":"TU","周三":"WE","周四":"TH","周五":"FR","周六":"SA","周日":"SU","星期一":"MO","星期二":"TU","星期三":"WE","星期四":"TH","星期五":"FR","星期六":"SA","星期日":"SU"}

def _cn2n(s):
    if not s: return 0
    if s.isdigit(): return int(s)
    if s in CN_NUM: return CN_NUM[s]
    if "十" in s:
        p = s.split("十")
        t = CN_NUM.get(p[0], 1) if p[0] else 1
        o = CN_NUM.get(p[1], 0) if len(p)>1 and p[1] else 0
        return t*10+o
    return 0

def _parse_time(text):
    d = r"([一两二三四五六七八九十]|十一|十二|\d{1,2})"
    for pat, fn in [
        (re.compile(r"(早上|早晨|上午)"+d+r"点"), lambda m:_cn2n(m.group(2))),
        (re.compile(r"(早上|早晨|上午)"+d+r"点半"), lambda m:_cn2n(m.group(2))+0.5),
        (re.compile(r"下午"+d+r"点"), lambda m:_cn2n(m.group(1))+12),
        (re.compile(r"下午"+d+r"点半"), lambda m:_cn2n(m.group(1))+12.5),
        (re.compile(r"晚上"+d+r"点"), lambda m:_cn2n(m.group(1))+12 if _cn2n(m.group(1))<8 else _cn2n(m.group(1))),
        (re.compile(r"(\d{1,2})点(?!\d)"), lambda m:int(m.group(1))),
        (re.compile(r"(\d{1,2})点半(?!\d)"), lambda m:int(m.group(1))+0.5),
        (re.compile(r"(\d{1,2}):(\d{2})"), lambda m:int(m.group(1))+int(m.group(2))/60),
    ]:
        m = pat.search(text)
        if m:
            try:
                h = fn(m); hr = max(0,min(23,int(h))); mn = int((h-hr)*60)
                return f"{hr:02d}:{mn:02d}"
            except: continue
    return None

def _detect_intent(text):
    for kw in DEL_KW:
        if kw in text: return "delete"
    for kw in QRY_KW:
        if kw in text: return "query"
    for kw in ADD_KW:
        if kw in text: return "add"
    dt = _parse_date(text); return "add" if (_parse_time(text) or dt) else "unknown"

def _parse_date(text):
    today = date.today()
    for w,off in DAY_MAP.items():
        if w in text: return today+timedelta(days=off)
    for w,off in WD_MAP.items():
        if w in text: return today+timedelta(days=off)
    m = re.search(r"(\d{1,2})月(\d{1,2})[号日]", text)
    if m:
        y = today.year; t = date(y,int(m.group(1)),int(m.group(2)))
        return date(y+1,t.month,t.day) if t<today else t
    return None

def _parse_recurrence(text):
    if "每天" in text or "每日" in text: return "FREQ=DAILY"
    m = re.search(r"每月(\d{1,2})[号日]", text)
    if m: return f"FREQ=MONTHLY;BYMONTHDAY={m.group(1)}"
    if "每月" in text or "每个月" in text: return "FREQ=MONTHLY"
    for cn,en in RC_WD.items():
        prefix = "每"+cn if cn in ("周一","周二","周三","周四","周五","周六","周日") else "每个"+cn
        if prefix in text: return f"FREQ=WEEKLY;BYDAY={en}"
    if "每周" in text or "每个星期" in text:
        for cn,en in RC_WD.items():
            if cn in text: return f"FREQ=WEEKLY;BYDAY={en}"
        return "FREQ=WEEKLY"
    return None

def _parse(text):
    text = text.strip()
    r = {"intent":"unknown","params":{},"raw_text":text}
    if not text: return r
    r["intent"] = _detect_intent(text)
    dt = _parse_date(text)
    rr = _parse_recurrence(text)
    if dt: r["params"]["date"] = dt.strftime("%Y-%m-%d")
    if rr: r["params"]["is_recurring"] = True; r["params"]["recurrence_rule"] = rr
    tm = _parse_time(text)
    if tm:
        r["params"]["time"] = tm
        if dt:
            h,mn = int(tm.split(":")[0]), int(tm.split(":")[1])
            sd = datetime(dt.year,dt.month,dt.day,h,mn)
            r["params"]["start_time"] = sd.isoformat()
            r["params"]["end_time"] = (sd+timedelta(hours=1)).isoformat()
    title = _extract_title(text, r["intent"])
    if title: r["params"]["title"] = title
    return r

def _extract_title(text, intent):
    c = text
    for kw in ADD_KW+DEL_KW+QRY_KW: c = c.replace(kw,"")
    c = re.sub(r"(今天|明天|后天|大后天)","",c)
    c = re.sub(r"(早上|早晨|上午|下午|晚上|中午)","",c)
    c = re.sub(r"([一两二三四五六七八九十]|十一|十二|\d{1,2})点(半)?","",c)
    c = re.sub(r"(\d{1,2}):(\d{2})","",c)
    c = re.sub(r"(\d{1,2})月(\d{1,2})[号日]","",c)
    c = re.sub(r"(每[天周月日])","",c)
    c = re.sub(r"(每个[一二三四五六日])","",c)
    c = re.sub(r"(每周[一-日]|每星期[一-日])","",c)
    c = re.sub(r"(下?周[一-日]|下?星期[一-日天])","",c)
    c = re.sub(r"的","",c)
    c = re.sub(r"\s+"," ",c).strip()
    return c if (c and len(c)>1 and intent!="query") else None

def parse_voice_command(text):
    r = _parse(text)
    p = r["params"]
    return {"intent":r["intent"],"title":p.get("title"),"date":p.get("date"),
            "time":p.get("time"),"startTime":p.get("start_time"),
            "endTime":p.get("end_time"),
            "isRecurring":p.get("is_recurring",False),
            "recurrenceRule":p.get("recurrence_rule"),
            "rawText":r["raw_text"]}