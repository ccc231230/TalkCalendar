<template>
  <div class="week-panel">
    <div class="week-header">
      <div class="time-gutter"></div>
      <div v-for="(day, idx) in weekDays" :key="idx" class="day-hd" :class="{ today: isToday(day) }">
        <span class="day-name">{{ day.format("ddd") }}</span>
        <span class="day-num">{{ day.date() }}</span>
      </div>
    </div>
    <div class="week-body">
      <div class="time-col">
        <div v-for="h in hours" :key="h" class="time-label">{{ String(h).padStart(2,"0") }}:00</div>
      </div>
      <div class="days-area">
        <div v-for="(day, di) in weekDays" :key="di" class="day-col" :style="{ height: totalH + 'px' }">
          <div v-for="h in hours" :key="h" class="slot" @click="clickSlot(day, h)"></div>
          <div v-for="ev in positioned(day)" :key="ev.event.id" class="w-ev" :style="ev.style" @click="emit('openEvent', ev.event)">
            <span class="w-ev-time">{{ timeLabel(ev.event.startTime) }}</span>
            <span class="w-ev-title">{{ ev.event.title }}</span>
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
const START = 8; const END = 22; const SLOT = 50
const hours = computed(() => { const a: number[] = []; for (let h=START;h<=END;h++) a.push(h); return a })
const totalH = (END - START) * SLOT
const weekDays = computed(() => getWeekDays(store.currentDate))
const emit = defineEmits<{ clickSlot: [date: dayjs.Dayjs, hour: number]; openEvent: [event: CalendarEvent] }>()

function timeLabel(iso: string) { return dayjs(iso).format("HH:mm") }

interface Pos { event: CalendarEvent; style: Record<string,string> }
function positioned(day: dayjs.Dayjs): Pos[] {
  const evs = getEventsForDay(store.events, day).filter(e => !e.isAllDay)
  if (!evs.length) return []
  const ds = day.startOf("day")
  type R = { event: CalendarEvent; top: number; h: number; lane: number }
  const raw: R[] = evs.map(e => {
    const s = dayjs(e.startTime); const ed = dayjs(e.endTime)
    const sh = Math.max(s.diff(ds,"hour",true), START)
    const eh = Math.min(ed.diff(ds,"hour",true), END)
    return { event: e, top: (sh - START)*SLOT, h: Math.max((eh - sh)*SLOT, 22), lane: 0 }
  }).sort((a,b) => a.top - b.top || b.h - a.h)

  const lanes: { end: number }[] = []
  for (const r of raw) {
    let l = 0
    while (l < lanes.length && lanes[l].end > r.top) l++
    r.lane = l
    if (l >= lanes.length) lanes.push({ end: r.top + r.h })
    else lanes[l].end = r.top + r.h
  }
  const n = lanes.length
  return raw.map(r => ({
    event: r.event,
    style: {
      top: r.top + "px", height: r.h + "px",
      left: (r.lane * 100/n) + "%", width: (100/n) + "%",
      background: r.event.color + "18", borderLeftColor: r.event.color,
    }
  }))
}
function clickSlot(day: dayjs.Dayjs, h: number) { emit("clickSlot", day.hour(h).minute(0).second(0), h) }
</script>

<style scoped>
.week-panel {
  display: flex; flex-direction: column; height: 100%;
  background: var(--bg-surface); border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm); overflow: hidden;
}
.week-header { display: flex; border-bottom: 1px solid var(--border-light); flex-shrink: 0; }
.time-gutter { width: 56px; flex-shrink: 0; }
.day-hd { flex: 1; text-align: center; padding: 10px 0; }
.day-hd.today { background: var(--accent-soft); border-radius: 6px 6px 0 0; }
.day-name { display: block; font-size: 11px; font-weight: 500; color: var(--text-tertiary); text-transform: uppercase; }
.day-num { font-size: 18px; font-weight: 600; color: var(--text-primary); }
.week-body { display: flex; flex: 1; overflow-y: auto; overflow-x: hidden; }
.time-col { width: 56px; flex-shrink: 0; }
.time-label { height: 50px; font-size: 10px; color: var(--text-tertiary); text-align: right; padding-right: 8px; line-height: 50px; }
.days-area { display: flex; flex: 1; }
.day-col { flex: 1; border-left: 1px solid var(--border-light); position: relative; }
.slot { height: 50px; border-bottom: 1px solid var(--border-light); cursor: pointer; transition: background var(--transition); }
.slot:hover { background: var(--bg-hover); }
.w-ev {
  position: absolute; left: 1px; right: 1px; border-left: 3px solid;
  border-radius: 4px; padding: 3px 6px; font-size: 11px; overflow: hidden;
  cursor: pointer; z-index: 1; transition: box-shadow var(--transition);
}
.w-ev:hover { box-shadow: var(--shadow-md); z-index: 2; }
.w-ev-time { font-size: 10px; color: var(--text-tertiary); margin-right: 4px; }
.w-ev-title { font-weight: 600; color: var(--text-primary); }
</style>