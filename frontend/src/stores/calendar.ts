import { defineStore } from "pinia"
import { ref, computed } from "vue"
import dayjs from "dayjs"
import type { CalendarEvent, CreateEventInput, ConflictResult } from "../types/event"
import * as db from "../utils/db"
import { checkTimeConflict } from "../utils/calendar"

export const useCalendarStore = defineStore("calendar", () => {
  const events = ref<CalendarEvent[]>([])
  const currentYear = ref(dayjs().year())
  const currentMonth = ref(dayjs().month())
  const currentDate = ref(dayjs())
  const viewMode = ref<"month" | "week">("month")
  const isLoaded = ref(false)

  const currentMonthStr = computed(() =>
    dayjs(new Date(currentYear.value, currentMonth.value)).format("YYYY年M月")
  )

  async function loadEvents() {
    events.value = await db.getAllEvents()
    isLoaded.value = true
  }

  async function createEvent(input: CreateEventInput): Promise<CalendarEvent> {
    const event = await db.addEvent(input)
    events.value.push(event)
    return event
  }

  async function editEvent(updated: CalendarEvent): Promise<void> {
    await db.updateEvent(updated)
    const idx = events.value.findIndex((e) => e.id === updated.id)
    if (idx !== -1) events.value[idx] = updated
  }

  async function removeEvent(id: string): Promise<void> {
    await db.deleteEvent(id)
    events.value = events.value.filter((e) => e.id !== id)
  }

  function checkConflict(startTime: string, endTime: string, excludeId?: string): ConflictResult {
    const existing = events.value.filter((e) => e.id !== excludeId && !e.isAllDay)
    const conflicts = checkTimeConflict({ startTime, endTime }, existing)
    return { hasConflict: conflicts.length > 0, conflicts }
  }

  function goToPrevMonth() {
    if (currentMonth.value === 0) {
      currentMonth.value = 11
      currentYear.value--
    } else {
      currentMonth.value--
    }
  }

  function goToNextMonth() {
    if (currentMonth.value === 11) {
      currentMonth.value = 0
      currentYear.value++
    } else {
      currentMonth.value++
    }
  }

  function goToToday() {
    currentYear.value = dayjs().year()
    currentMonth.value = dayjs().month()
    currentDate.value = dayjs()
  }

  function goToPrevWeek() {
    currentDate.value = currentDate.value.subtract(1, "week")
  }

  function goToNextWeek() {
    currentDate.value = currentDate.value.add(1, "week")
  }

  function setViewMode(mode: "month" | "week") {
    viewMode.value = mode
  }

  return {
    events,
    currentYear,
    currentMonth,
    currentDate,
    viewMode,
    isLoaded,
    currentMonthStr,
    loadEvents,
    createEvent,
    editEvent,
    removeEvent,
    checkConflict,
    goToPrevMonth,
    goToNextMonth,
    goToToday,
    goToPrevWeek,
    goToNextWeek,
    setViewMode,
  }
})
