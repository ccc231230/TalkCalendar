<template>
  <div class="calendar-grid">
    <div class="grid-header">
      <div v-for="day in weekDays" :key="day" class="header-cell">{{ day }}</div>
    </div>
    <div class="grid-body">
      <div
        v-for="(day, idx) in days"
        :key="idx"
        class="day-cell"
        :class="{
          'other-month': !isSameMonth(day, store.currentYear, store.currentMonth),
          today: isToday(day),
          selected: day.isSame(store.currentDate, 'day'),
        }"
        @click="selectDay(day)"
      >
        <span class="day-num">{{ day.date() }}</span>
        <div class="day-events">
          <EventItem
            v-for="event in getDayEvents(day)"
            :key="event.id"
            :event="event"
            compact
            @click.stop="openEvent(event)"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue"
import dayjs from "dayjs"
import { useCalendarStore } from "../stores/calendar"
import { getMonthDays, getEventsForDay, isToday, isSameMonth } from "../utils/calendar"
import EventItem from "./EventItem.vue"
import type { CalendarEvent } from "../types/event"

const store = useCalendarStore()

const weekDays = ["一", "二", "三", "四", "五", "六", "日"]

const days = computed(() =>
  getMonthDays(store.currentYear, store.currentMonth)
)

const emit = defineEmits<{
  selectDay: [date: dayjs.Dayjs]
  openEvent: [event: CalendarEvent]
}>()

function getDayEvents(day: dayjs.Dayjs) {
  return getEventsForDay(store.events, day).slice(0, 3)
}

function selectDay(day: dayjs.Dayjs) {
  store.currentDate = day
  emit("selectDay", day)
}

function openEvent(event: CalendarEvent) {
  emit("openEvent", event)
}
</script>

<style scoped>
.calendar-grid {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.grid-header {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  text-align: center;
  padding: 8px 0;
  border-bottom: 1px solid #e0e0e0;
}
.header-cell {
  font-size: 13px;
  font-weight: 600;
  color: #666;
}
.grid-body {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  grid-auto-rows: 1fr;
  flex: 1;
}
.day-cell {
  border-right: 1px solid #eee;
  border-bottom: 1px solid #eee;
  padding: 4px 6px;
  min-height: 90px;
  cursor: pointer;
  transition: background 0.15s;
  overflow: hidden;
}
.day-cell:hover {
  background: #f5f7fa;
}
.day-cell.other-month {
  opacity: 0.35;
}
.day-cell.today {
  background: #e8f4fd;
}
.day-cell.today .day-num {
  background: #4A90D9;
  color: #fff;
  border-radius: 50%;
  width: 24px;
  height: 24px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.day-cell.selected {
  outline: 2px solid #4A90D9;
  outline-offset: -2px;
}
.day-num {
  font-size: 13px;
  color: #333;
}
.day-events {
  margin-top: 2px;
  display: flex;
  flex-direction: column;
  gap: 1px;
}
</style>
