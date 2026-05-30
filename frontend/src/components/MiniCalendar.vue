<template>
  <div class="mini-cal">
    <div class="mini-header">
      <button class="mini-nav" @click="prev">&lsaquo;</button>
      <span class="mini-label">{{ label }}</span>
      <button class="mini-nav" @click="next">&rsaquo;</button>
    </div>
    <div class="mini-weekdays">
      <span v-for="d in ['一','二','三','四','五','六','日']" :key="d">{{ d }}</span>
    </div>
    <div class="mini-grid">
      <button
        v-for="(d, i) in days"
        :key="i"
        class="mini-day"
        :class="{
          'other-month': !d.isSame(base, 'month'),
          today: d.isSame(today, 'day'),
          selected: d.isSame(selected, 'day'),
          'has-event': hasEvent(d),
        }"
        @click="$emit('select', d)"
      >{{ d.date() }}</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from "vue"
import dayjs from "dayjs"
import { useCalendarStore } from "../stores/calendar"
import { getMonthDays, getEventsForDay } from "../utils/calendar"

const store = useCalendarStore()
const base = ref(dayjs())

const today = computed(() => dayjs())
const selected = computed(() => store.currentDate)
const label = computed(() => base.value.format("YYYY年M月"))

const days = computed(() => getMonthDays(base.value.year(), base.value.month()))

function hasEvent(d: dayjs.Dayjs) {
  return getEventsForDay(store.events, d).length > 0
}
function prev() { base.value = base.value.subtract(1, "month") }
function next() { base.value = base.value.add(1, "month") }

defineEmits<{ select: [date: dayjs.Dayjs] }>()
</script>

<style scoped>
.mini-cal { user-select: none; }
.mini-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: var(--space-2);
}
.mini-label { font-size: 13px; font-weight: 600; color: var(--text-primary); }
.mini-nav {
  background: none; border: none; font-size: 16px; color: var(--text-tertiary);
  cursor: pointer; padding: 2px 6px; border-radius: 4px;
}
.mini-nav:hover { background: var(--bg-hover); color: var(--text-primary); }
.mini-weekdays {
  display: grid; grid-template-columns: repeat(7, 1fr);
  text-align: center; font-size: 10px; color: var(--text-tertiary);
  margin-bottom: 4px;
}
.mini-grid {
  display: grid; grid-template-columns: repeat(7, 1fr);
  gap: 2px;
}
.mini-day {
  aspect-ratio: 1;
  display: flex; align-items: center; justify-content: center;
  font-size: 12px; font-family: var(--font-sans);
  border: none; border-radius: 50%;
  background: transparent; color: var(--text-secondary);
  cursor: pointer; transition: all var(--transition);
}
.mini-day:hover { background: var(--bg-hover); }
.mini-day.other-month { color: var(--text-tertiary); opacity: 0.4; }
.mini-day.today { background: var(--accent-soft); color: var(--accent); font-weight: 600; }
.mini-day.selected { background: var(--accent); color: var(--text-inverse); font-weight: 600; }
.mini-day.has-event::after {
  content: ''; position: absolute; bottom: 2px;
  width: 4px; height: 4px; border-radius: 50%; background: var(--accent);
}
.mini-day.selected.has-event::after { background: var(--text-inverse); }
.mini-day { position: relative; }
</style>
