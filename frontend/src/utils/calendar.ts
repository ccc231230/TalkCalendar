import dayjs from "dayjs"
import isoWeek from "dayjs/plugin/isoWeek"
import type { CalendarEvent } from "../types/event"

dayjs.extend(isoWeek)

export function getMonthDays(year: number, month: number): dayjs.Dayjs[] {
  const firstDay = dayjs(new Date(year, month, 1))
  const startDay = firstDay.startOf("isoWeek")
  const lastDay = dayjs(new Date(year, month + 1, 0))
  const endDay = lastDay.endOf("isoWeek")

  const days: dayjs.Dayjs[] = []
  let current = startDay
  while (current.isBefore(endDay) || current.isSame(endDay, "day")) {
    days.push(current)
    current = current.add(1, "day")
  }
  return days
}

export function getWeekDays(date: dayjs.Dayjs): dayjs.Dayjs[] {
  const start = date.startOf("isoWeek")
  const days: dayjs.Dayjs[] = []
  for (let i = 0; i < 7; i++) {
    days.push(start.add(i, "day"))
  }
  return days
}

export function getEventsForDay(events: CalendarEvent[], date: dayjs.Dayjs): CalendarEvent[] {
  const dayStart = date.startOf("day").toISOString()
  const dayEnd = date.endOf("day").toISOString()
  return events.filter((e) => {
    // Include non-recurring events that fall on this day
    if (!e.isRecurring) {
      return e.startTime < dayEnd && e.endTime > dayStart
    }
    // For recurring events, check if this date matches the rule
    return matchesRecurrence(e, date)
  })
}

function matchesRecurrence(event: CalendarEvent, date: dayjs.Dayjs): boolean {
  if (!event.recurrenceRule) return false
  const rule = event.recurrenceRule.toUpperCase()
  const eventStart = dayjs(event.startTime)
  const dayOfWeek = date.format("dd").toUpperCase()
  const dayNum = date.date()
  const monthDay = date.date()

  // "FREQ=WEEKLY;BYDAY=MO"
  if (rule.includes("FREQ=WEEKLY") && rule.includes("BYDAY=")) {
    const targetDay = rule.split("BYDAY=")[1]?.trim()
    if (!targetDay) return false
    // Handle MO,WE,FR (multiple days)
    const targetDays = targetDay.split(",").map((d) => d.trim())
    if (targetDays.includes(dayOfWeek)) return true
  }

  // "FREQ=MONTHLY;BYMONTHDAY=15"
  if (rule.includes("FREQ=MONTHLY") && rule.includes("BYMONTHDAY=")) {
    const targetDay = parseInt(rule.split("BYMONTHDAY=")[1]?.trim() || "0")
    return monthDay === targetDay
  }

  // "FREQ=DAILY" - simple daily
  if (rule === "FREQ=DAILY") return true

  return false
}

export function isToday(date: dayjs.Dayjs): boolean {
  return date.isSame(dayjs(), "day")
}

export function isSameMonth(date: dayjs.Dayjs, year: number, month: number): boolean {
  return date.month() === month && date.year() === year
}

export function formatTime(iso: string): string {
  return dayjs(iso).format("HH:mm")
}

export function formatDateShort(iso: string): string {
  return dayjs(iso).format("MM/DD HH:mm")
}

export function checkTimeConflict(
  newEvent: { startTime: string; endTime: string },
  existingEvents: CalendarEvent[]
): CalendarEvent[] {
  return existingEvents.filter((e) => {
    if (e.isAllDay) return false
    return e.startTime < newEvent.endTime && e.endTime > newEvent.startTime
  })
}
