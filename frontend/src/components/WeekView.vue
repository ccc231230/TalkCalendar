<template>
  <div class="week-view">
    <div class="week-header">
      <div class="time-gutter"></div>
      <div
        v-for="(day, idx) in weekDays"
        :key="idx"
        class="day-header"
        :class="{ today: isToday(day) }"
      >
        <span class="day-name">{{ day.format("ddd") }}</span>
        <span class="day-date">{{ day.date() }}</span>
      </div>
    </div>
    <div class="week-body">
      <div class="time-column">
        <div v-for="h in hoursRange" :key="h" class="time-label">
          {{ String(h).padStart(2, "0") }}:00
        </div>
      </div>
      <div class="days-grid">
        <div
          v-for="(day, di) in weekDays"
          :key="di"
          class="day-column"
          :style="{ height: totalHeight + 'px' }"
        >
          <div
            v-for="h in hoursRange"
            :key="h"
            class="hour-slot"
            @click="clickSlot(day, h)"
          ></div>
          <div
            v-for="ev in getPositionedEvents(day)"
            :key="ev.event.id"
            class="week-event"
            :style="ev.style"
            @click="emit('openEvent', ev.event)"
          >
            <span class="event-title">{{ ev.event.title }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue"
import dayjs from "dayjs"
import { useCalendarStore } from "../stores/calendar"
import { getWeekDays, getEventsForDay, isToday } from "../utils/calendar"
import type { CalendarEvent } from "../types/event"

const store = useCalendarStore()

const DAY_START = 8
const DAY_END = 22
const SLOT_H = 50
const totalHours = DAY_END - DAY_START
const totalHeight = totalHours * SLOT_H

const hoursRange = computed(() => {
  const arr: number[] = []
  for (let h = DAY_START; h <= DAY_END; h++) arr.push(h)
  return arr
})

const weekDays = computed(() => getWeekDays(store.currentDate))

const emit = defineEmits<{
  clickSlot: [date: dayjs.Dayjs, hour: number]
  openEvent: [event: CalendarEvent]
}>()

interface PositionedEvent {
  event: CalendarEvent
  style: Record<string, string>
}

function getPositionedEvents(day: dayjs.Dayjs): PositionedEvent[] {
  const events = getEventsForDay(store.events, day).filter((e) => !e.isAllDay)
  if (events.length === 0) return []

  const dayStart = day.startOf("day")

  // Calculate raw positions for each event
  interface RawEvent {
    event: CalendarEvent
    top: number
    height: number
    lane: number
  }
  const raw: RawEvent[] = events
    .map((e) => {
      const start = dayjs(e.startTime)
      const end = dayjs(e.endTime)
      const sh = Math.max(start.diff(dayStart, "hour", true), DAY_START)
      const eh = Math.min(end.diff(dayStart, "hour", true), DAY_END)
      return {
        event: e,
        top: (sh - DAY_START) * SLOT_H,
        height: Math.max((eh - sh) * SLOT_H, 18),
        lane: 0,
      }
    })
    .sort((a, b) => a.top - b.top || b.height - a.height)

  // Assign lanes to avoid overlap
  const lanes: { endY: number }[] = []

  for (const item of raw) {
    let lane = 0
    while (lane < lanes.length && lanes[lane].endY > item.top) {
      lane++
    }
    item.lane = lane
    if (lane >= lanes.length) {
      lanes.push({ endY: item.top + item.height })
    } else {
      lanes[lane].endY = item.top + item.height
    }
  }

  const totalLanes = lanes.length

  return raw.map((item) => {
    const laneWidth = 100 / totalLanes
    return {
      event: item.event,
      style: {
        top: item.top + "px",
        height: item.height + "px",
        left: (item.lane * laneWidth) + "%",
        width: laneWidth + "%",
        backgroundColor: item.event.color + "25",
        borderLeftColor: item.event.color,
      },
    }
  })
}

function clickSlot(day: dayjs.Dayjs, hour: number) {
  const date = day.hour(hour).minute(0).second(0)
  emit("clickSlot", date, hour)
}
</script>

<style scoped>
.week-view { display: flex; flex-direction: column; height: 100%; overflow: hidden; }
.week-header { display: flex; border-bottom: 1px solid #e0e0e0; flex-shrink: 0; }
.time-gutter { width: 60px; flex-shrink: 0; }
.day-header { flex: 1; text-align: center; padding: 6px 0; }
.day-header.today { background: #e8f4fd; border-radius: 4px; }
.day-name { display: block; font-size: 11px; color: #888; }
.day-date { font-weight: 600; font-size: 16px; }
.week-body { display: flex; flex: 1; overflow-y: auto; overflow-x: hidden; }
.time-column { width: 60px; flex-shrink: 0; padding-top: 0; }
.time-label { height: 50px; font-size: 11px; color: #999; text-align: right; padding-right: 6px; line-height: 50px; box-sizing: border-box; }
.days-grid { display: flex; flex: 1; }
.day-column { flex: 1; border-left: 1px solid #eee; position: relative; }
.hour-slot { height: 50px; border-bottom: 1px solid #f0f0f0; box-sizing: border-box; cursor: pointer; }
.hour-slot:hover { background: #f5f7fa; }
.week-event {
  position: absolute; border-left: 3px solid; border-radius: 3px;
  padding: 2px 4px; font-size: 11px; overflow: hidden;
  cursor: pointer; z-index: 1; box-sizing: border-box;
}
.week-event:hover { filter: brightness(0.95); z-index: 2; }
.week-event .event-title { font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
</style>