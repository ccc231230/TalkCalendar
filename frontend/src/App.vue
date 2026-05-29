<template>
  <div class="app">
    <header class="app-header">
      <h1>TalkCalendar</h1>
      <div class="nav">
        <button class="nav-btn" @click="store.goToToday()">今天</button>
        <button class="nav-btn" @click="prev">&#8249;</button>
        <span class="nav-title">{{ viewMode === 'month' ? store.currentMonthStr : weekLabel }}</span>
        <button class="nav-btn" @click="next">&#8250;</button>
      </div>
      <div class="view-toggle">
        <button :class="['toggle-btn', { active: viewMode === 'month' }]" @click="viewMode = 'month'">月</button>
        <button :class="['toggle-btn', { active: viewMode === 'week' }]" @click="viewMode = 'week'">周</button>
      </div>
      <button class="add-btn" @click="openNewEvent">+ 新建</button>
      <button v-if="!notifPermission" class="notif-btn" @click="enableNotifications" title="开启提醒通知">🔔</button>
    </header>
    <main class="app-main">
      <CalendarGrid v-if="viewMode === 'month'" @select-day="handleSelectDay" @open-event="handleOpenEvent" />
      <WeekView v-else @click-slot="handleClickSlot" @open-event="handleOpenEvent" />
    </main>
    <EventModal :visible="modalVisible" :event="editingEvent" :default-date="defaultDate"
      @close="modalVisible = false; editingEvent = null"
      @saved="modalVisible = false; editingEvent = null"
      @deleted="modalVisible = false; editingEvent = null" />
    <VoicePanel :visible="voiceVisible" @close="voiceVisible = false" @created="handleVoiceCreated" />
    <button class="voice-fab" @click="toggleVoice" :class="{ active: voiceVisible }">{{ voiceVisible ? '✕' : '🎤' }}</button>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue"
import dayjs from "dayjs"
import { useCalendarStore } from "./stores/calendar"
import { useNotifications } from "./composables/useNotifications"
import CalendarGrid from "./components/CalendarGrid.vue"
import WeekView from "./components/WeekView.vue"
import EventModal from "./components/EventModal.vue"
import VoicePanel from "./components/VoicePanel.vue"
import type { CalendarEvent } from "./types/event"

const store = useCalendarStore()
const { permissionGranted: notifPermission, requestPermission, startChecking } = useNotifications()

const viewMode = computed({ get: () => store.viewMode, set: (v) => store.setViewMode(v) })
const modalVisible = ref(false)
const editingEvent = ref<CalendarEvent | null>(null)
const defaultDate = ref<string | null>(null)
const voiceVisible = ref(false)

const weekLabel = computed(() => {
  const start = store.currentDate.startOf("isoWeek")
  const end = store.currentDate.endOf("isoWeek")
  return start.format("M月D日") + " - " + end.format("M月D日")
})

function prev() { viewMode.value === "month" ? store.goToPrevMonth() : store.goToPrevWeek() }
function next() { viewMode.value === "month" ? store.goToNextMonth() : store.goToNextWeek() }
function handleSelectDay(date: dayjs.Dayjs) { defaultDate.value = date.toISOString(); openNewEvent() }
function handleClickSlot(date: dayjs.Dayjs) { defaultDate.value = date.toISOString(); openNewEvent() }
function handleOpenEvent(event: CalendarEvent) { editingEvent.value = event; modalVisible.value = true }
function openNewEvent() { editingEvent.value = null; modalVisible.value = true }
function toggleVoice() { voiceVisible.value = !voiceVisible.value }
async function handleVoiceCreated(input: any) { await store.createEvent(input) }
async function enableNotifications() { if (await requestPermission()) startChecking() }

onMounted(() => {
  store.loadEvents()
  if (Notification.permission === "granted") requestPermission().then((g) => { if (g) startChecking() })
})
</script>

<style scoped>
.app {
  display: flex;
  flex-direction: column;
  height: 100vh;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  color: #333;
  background: #fff;
}
.app-header {
  display: flex;
  align-items: center;
  padding: 10px 20px;
  border-bottom: 1px solid #e0e0e0;
  gap: 16px;
  flex-shrink: 0;
}
.app-header h1 { font-size: 18px; margin: 0; white-space: nowrap; }
.nav { display: flex; align-items: center; gap: 4px; }
.nav-btn { background: none; border: 1px solid #ddd; border-radius: 6px; padding: 4px 10px; cursor: pointer; font-size: 16px; color: #555; }
.nav-btn:hover { background: #f0f0f0; }
.nav-title { font-size: 15px; font-weight: 600; min-width: 140px; text-align: center; }
.view-toggle { display: flex; border: 1px solid #ddd; border-radius: 6px; overflow: hidden; }
.toggle-btn { background: none; border: none; padding: 4px 12px; cursor: pointer; font-size: 13px; color: #666; }
.toggle-btn.active { background: #4A90D9; color: #fff; }
.add-btn { background: #4A90D9; color: #fff; border: none; border-radius: 6px; padding: 6px 16px; cursor: pointer; font-size: 14px; margin-left: auto; }
.add-btn:hover { background: #3a7bc8; }
.notif-btn { background: none; border: 1px solid #ddd; border-radius: 6px; padding: 4px 8px; cursor: pointer; font-size: 18px; }
.notif-btn:hover { background: #f0f0f0; }
.app-main { flex: 1; overflow: hidden; display: flex; flex-direction: column; }
.voice-fab {
  position: fixed; bottom: 24px; right: 24px;
  width: 56px; height: 56px; border-radius: 50%;
  background: #4A90D9; color: #fff; border: none;
  font-size: 24px; cursor: pointer;
  box-shadow: 0 4px 12px rgba(74, 144, 217, 0.4);
  display: flex; align-items: center; justify-content: center;
  transition: all 0.2s; z-index: 100;
}
.voice-fab:hover { transform: scale(1.1); }
.voice-fab.active { background: #e74c3c; transform: rotate(90deg); }
</style>
