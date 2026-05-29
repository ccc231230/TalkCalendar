<template>
  <div
    class="event-item"
    :class="{ compact: compact }"
    :style="{ backgroundColor: event.color + '20', borderLeftColor: event.color }"
  >
    <span v-if="!compact" class="event-dot" :style="{ backgroundColor: event.color }"></span>
    <span class="event-title">{{ event.title }}</span>
    <span v-if="!compact && !event.isAllDay" class="event-time">
      {{ formatTime(event.startTime) }}
      <template v-if="event.endTime">- {{ formatTime(event.endTime) }}</template>
    </span>
  </div>
</template>

<script setup lang="ts">
import type { CalendarEvent } from "../types/event"
import { formatTime } from "../utils/calendar"

defineProps<{
  event: CalendarEvent
  compact?: boolean
}>()
</script>

<style scoped>
.event-item {
  padding: 2px 6px;
  border-left: 3px solid;
  border-radius: 3px;
  font-size: 12px;
  cursor: pointer;
  transition: opacity 0.15s;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.event-item:hover {
  opacity: 0.8;
}
.event-item.compact {
  padding: 1px 4px;
  font-size: 11px;
  border-left-width: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.event-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  display: inline-block;
  margin-right: 4px;
  flex-shrink: 0;
}
.event-title {
  font-weight: 500;
  color: #333;
}
.event-time {
  margin-left: 4px;
  color: #888;
  font-size: 11px;
}
</style>
