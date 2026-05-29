import { ref, onMounted, onUnmounted } from "vue"
import dayjs from "dayjs"
import { useCalendarStore } from "../stores/calendar"

export function useNotifications() {
  const store = useCalendarStore()
  const permissionGranted = ref(false)
  let checkInterval: ReturnType<typeof setInterval> | null = null
  const notifiedEvents = new Set<string>()

  async function requestPermission(): Promise<boolean> {
    if (!("Notification" in window)) {
      console.log("浏览器不支持通知")
      return false
    }

    if (Notification.permission === "granted") {
      permissionGranted.value = true
      return true
    }

    if (Notification.permission !== "denied") {
      const result = await Notification.requestPermission()
      permissionGranted.value = result === "granted"
      return permissionGranted.value
    }

    return false
  }

  function startChecking(): void {
    if (checkInterval) return

    checkInterval = setInterval(() => {
      if (!permissionGranted.value) return
      checkUpcomingEvents()
    }, 30000) // Check every 30 seconds
  }

  function stopChecking(): void {
    if (checkInterval) {
      clearInterval(checkInterval)
      checkInterval = null
    }
  }

  function checkUpcomingEvents(): void {
    const now = dayjs()
    const fiveMinLater = now.add(5, "minute")

    for (const event of store.events) {
      if (event.isAllDay) continue
      if (notifiedEvents.has(event.id)) continue

      const startTime = dayjs(event.startTime)
      // Event starts within the next 5 minutes
      if (startTime.isAfter(now) && startTime.isBefore(fiveMinLater)) {
        showNotification(event)
        notifiedEvents.add(event.id)
      }

      // Clean up old events from notified set
      if (startTime.isBefore(now.subtract(1, "hour"))) {
        notifiedEvents.delete(event.id)
      }
    }
  }

  function showNotification(event: any): void {
    if (!permissionGranted.value) return

    const startTime = dayjs(event.startTime).format("HH:mm")
    const notification = new Notification("📅 事件提醒", {
      body: `${event.title}\n开始时间: ${startTime}`,
      icon: "/vite.svg",
      tag: event.id,
      requireInteraction: true,
    })

    notification.onclick = () => {
      window.focus()
      const date = dayjs(event.startTime)
      store.currentYear = date.year()
      store.currentMonth = date.month()
      store.currentDate = date
      notification.close()
    }
  }

  // Reset notified events each day
  function resetDaily(): void {
    notifiedEvents.clear()
  }

  onMounted(() => {
    // Reset at midnight
    const now = dayjs()
    const midnight = now.endOf("day")
    const msToMidnight = midnight.diff(now)
    setTimeout(() => {
      resetDaily()
      // Then repeat every 24 hours
      setInterval(resetDaily, 86400000)
    }, msToMidnight + 1000)
  })

  return {
    permissionGranted,
    requestPermission,
    startChecking,
    stopChecking,
  }
}
