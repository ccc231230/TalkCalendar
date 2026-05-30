<template>
  <div class="app">
    <aside class="sidebar">
      <div class="sidebar-brand">
        <span class="brand-icon">🗓️</span>
        <span class="brand-text">TalkCalendar</span>
      </div>

      <button class="btn btn-primary btn-full" @click="openNewEvent">
        <span>+</span> 新建事件
      </button>

      <nav class="sidebar-nav">
        <button class="nav-item" :class="{ active: viewMode === 'month' }" @click="viewMode = 'month'">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
          <span>月视图</span>
        </button>
        <button class="nav-item" :class="{ active: viewMode === 'week' }" @click="viewMode = 'week'">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
          <span>周视图</span>
        </button>
      </nav>

      <div class="sidebar-minical">
        <MiniCalendar @select="goToDate" />
      </div>

      <div class="sidebar-footer">
        <button v-if="!notifPermission" class="btn btn-ghost btn-sm" @click="enableNotifications">🔔 开启提醒</button>
      </div>
    </aside>

    <main class="main-area">
      <header class="topbar">
        <div class="topbar-nav">
          <button class="btn btn-ghost btn-icon" @click="prev">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg>
          </button>
          <button class="btn btn-ghost date-label" @click="store.goToToday()">
            {{ viewMode === 'month' ? store.currentMonthStr : weekLabel }}
          </button>
          <button class="btn btn-ghost btn-icon" @click="next">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
          </button>
          <button class="btn btn-ghost btn-sm" @click="store.goToToday()">今天</button>
        </div>
      </header>

      <div class="content-area">
        <CalendarGrid v-if="viewMode === 'month'" @select-day="handleSelectDay" @open-event="handleOpenEvent" />
        <WeekView v-else @click-slot="handleClickSlot" @open-event="handleOpenEvent" />
      </div>
    </main>

    <EventModal :visible="modalVisible" :event="editingEvent" :default-date="defaultDate"
      @close="modalVisible = false; editingEvent = null"
      @saved="modalVisible = false; editingEvent = null"
      @deleted="modalVisible = false; editingEvent = null" />

    <ChatPanel :visible="chatVisible" @close="chatVisible = false" @created="handleChatCreated" />

    <button class="fab" @click="toggleChat" :class="{ active: chatVisible }">
      <svg v-if="!chatVisible" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/></svg>
      <span v-else class="fab-close">✕</span>
    </button>
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
import ChatPanel from "./components/ChatPanel.vue"
import MiniCalendar from "./components/MiniCalendar.vue"
import type { CalendarEvent } from "./types/event"

const store = useCalendarStore()
const { permissionGranted: notifPermission, requestPermission, startChecking } = useNotifications()

const viewMode = computed({ get: () => store.viewMode, set: (v) => store.setViewMode(v) })
const modalVisible = ref(false)
const editingEvent = ref<CalendarEvent | null>(null)
const defaultDate = ref<string | null>(null)
const chatVisible = ref(false)

const weekLabel = computed(() => {
  const s = store.currentDate.startOf("isoWeek")
  const e = store.currentDate.endOf("isoWeek")
  return s.format("M月D日") + " - " + e.format("M月D日")
})

function prev() { viewMode.value === "month" ? store.goToPrevMonth() : store.goToPrevWeek() }
function next() { viewMode.value === "month" ? store.goToNextMonth() : store.goToNextWeek() }
function handleSelectDay(d: dayjs.Dayjs) { defaultDate.value = d.toISOString(); openNewEvent() }
function handleClickSlot(d: dayjs.Dayjs) { defaultDate.value = d.toISOString(); openNewEvent() }
function handleOpenEvent(e: CalendarEvent) { editingEvent.value = e; modalVisible.value = true }
function openNewEvent() { editingEvent.value = null; modalVisible.value = true }
function toggleChat() { chatVisible.value = !chatVisible.value }
function goToDate(d: dayjs.Dayjs) {
  store.currentYear = d.year(); store.currentMonth = d.month(); store.currentDate = d
}
async function handleChatCreated(input: any) { await store.createEvent(input) }
async function enableNotifications() { if (await requestPermission()) startChecking() }

onMounted(() => {
  store.loadEvents()
  if (Notification.permission === "granted") requestPermission().then((g) => { if (g) startChecking() })
})
</script>

<style scoped>
.app {
  display: flex;
  height: 100vh;
  background: var(--bg-primary);
}
/* Sidebar */
.sidebar {
  width: 240px;
  background: var(--bg-surface);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  padding: var(--space-5);
  gap: var(--space-4);
  flex-shrink: 0;
}
.sidebar-brand {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) 0;
}
.brand-icon { font-size: 22px; }
.brand-text { font-size: 17px; font-weight: 700; letter-spacing: -0.3px; }

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  border: none;
  border-radius: var(--radius-md);
  font-family: var(--font-sans);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition);
}
.btn-primary {
  background: var(--accent);
  color: var(--text-inverse);
  padding: 10px 16px;
}
.btn-primary:hover { background: var(--accent-hover); }
.btn-full { width: 100%; }
.btn-ghost {
  background: transparent;
  color: var(--text-secondary);
  padding: 6px 10px;
}
.btn-ghost:hover { background: var(--bg-hover); color: var(--text-primary); }
.btn-icon { padding: 6px; border-radius: var(--radius-sm); }
.btn-sm { font-size: 13px; padding: 4px 10px; }

.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.nav-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: 10px 12px;
  border: none;
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--text-secondary);
  font-size: 14px;
  font-family: var(--font-sans);
  cursor: pointer;
  transition: all var(--transition);
}
.nav-item:hover { background: var(--bg-hover); color: var(--text-primary); }
.nav-item.active { background: var(--accent-soft); color: var(--accent); font-weight: 600; }
.sidebar-minical { flex: 1; }
.sidebar-footer { padding-top: var(--space-3); border-top: 1px solid var(--border); }

/* Main */
.main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3) var(--space-6);
  border-bottom: 1px solid var(--border);
  background: var(--bg-surface);
  flex-shrink: 0;
}
.topbar-nav {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.date-label {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary) !important;
  min-width: 160px;
  justify-content: center;
}
.content-area {
  flex: 1;
  overflow: hidden;
  padding: var(--space-4);
}

/* FAB */
.fab {
  position: fixed;
  bottom: 28px;
  right: 28px;
  width: 56px;
  height: 56px;
  border-radius: 50%;
  border: none;
  background: var(--accent);
  color: var(--text-inverse);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: var(--shadow-lg);
  transition: all 200ms cubic-bezier(0.4, 0, 0.2, 1);
  z-index: 100;
}
.fab:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-xl);
}
.fab.active {
  background: var(--danger);
  transform: rotate(90deg);
}
.fab-close { font-size: 26px; font-weight: 300; line-height: 1; }
</style>
