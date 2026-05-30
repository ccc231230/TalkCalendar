<template>
  <div class="cal-grid">
    <div class="grid-header">
      <div v-for="d in ['一','二','三','四','五','六','日']" :key="d" class="hd-cell">{{ d }}</div>
    </div>
    <div class="grid-body">
      <div
        v-for="(day, i) in days"
        :key="i"
        class="day-cell"
        :class="{
          'other-month': !day.isSame(currentMonth, 'month'),
          today: day.isSame(today, 'day'),
          selected: day.isSame(store.currentDate, 'day'),
        }"
        @click="emit('selectDay', day)"
      >
        <span class="day-num">{{ day.date() }}</span>
        <div class="day-events">
          <div
            v-for="ev in getDayEvents(day).slice(0, 3)"
            :key="ev.id"
            class="ev-badge"
            :style="{ background: ev.color + '20', color: ev.color, borderLeftColor: ev.color }"
            @click.stop="emit('openEvent', ev)"
          >{{ ev.title }}</div>
          <div v-if="getDayEvents(day).length > 3" class="ev-more">+{{ getDayEvents(day).length - 3 }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue"
import dayjs from "dayjs"
import { useCalendarStore } from "../stores/calendar"
import { getMonthDays, getEventsForDay } from "../utils/calendar"
import type { CalendarEvent } from "../types/event"

const store = useCalendarStore()
const today = dayjs()
const currentMonth = computed(() => dayjs(new Date(store.currentYear, store.currentMonth)))
const days = computed(() => getMonthDays(store.currentYear, store.currentMonth))

const emit = defineEmits<{
  selectDay: [date: dayjs.Dayjs]
  openEvent: [event: CalendarEvent]
}>()

function getDayEvents(day: dayjs.Dayjs) {
  return getEventsForDay(store.events, day)
}
</script>

<style scoped>
.cal-grid {
  display: flex; flex-direction: column;
  height: 100%; background: var(--bg-surface);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
}
.grid-header {
  display: grid; grid-template-columns: repeat(7, 1fr);
  text-align: center; padding: 10px 0;
  border-bottom: 1px solid var(--border-light);
  background: var(--bg-surface);
}
.hd-cell {
  font-size: 12px; font-weight: 600; color: var(--text-tertiary);
  text-transform: uppercase; letter-spacing: 0.5px;
}
.grid-body {
  display: grid; grid-template-columns: repeat(7, 1fr);
  grid-auto-rows: 1fr; flex: 1;
}
.day-cell {
  padding: 6px 8px; min-height: 90px;
  border-right: 1px solid var(--border-light);
  border-bottom: 1px solid var(--border-light);
  cursor: pointer; transition: background var(--transition);
  overflow: hidden;
}
.day-cell:nth-child(7n) { border-right: none; }
.day-cell:hover { background: var(--bg-hover); }
.day-cell.other-month { opacity: 0.3; }
.day-cell.today { background: var(--accent-soft); }
.day-cell.today .day-num {
  background: var(--accent); color: var(--text-inverse);
  border-radius: 50%; width: 26px; height: 26px;
  display: inline-flex; align-items: center; justify-content: center;
  font-weight: 600;
}
.day-cell.selected {
  box-shadow: inset 0 0 0 2px var(--accent);
  border-radius: 4px;
}
.day-num { font-size: 13px; font-weight: 500; color: var(--text-primary); }
.day-events {
  margin-top: 4px; display: flex; flex-direction: column; gap: 2px;
}
.ev-badge {
  font-size: 11px; padding: 1px 6px; border-radius: 3px;
  border-left: 2px solid; font-weight: 500;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  cursor: pointer; transition: opacity var(--transition);
}
.ev-badge:hover { opacity: 0.7; }
.ev-more { font-size: 11px; color: var(--text-tertiary); padding-left: 6px; }
</style>
