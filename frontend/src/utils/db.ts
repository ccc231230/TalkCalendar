import type { CalendarEvent, CreateEventInput } from "../types/event"

const DB_NAME = "talkcalendar"
const DB_VERSION = 1
const STORE_NAME = "events"

function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION)
    request.onupgradeneeded = () => {
      const db = request.result
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        const store = db.createObjectStore(STORE_NAME, { keyPath: "id" })
        store.createIndex("startTime", "startTime", { unique: false })
        store.createIndex("endTime", "endTime", { unique: false })
      }
    }
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error)
  })
}

export async function getAllEvents(): Promise<CalendarEvent[]> {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readonly")
    const store = tx.objectStore(STORE_NAME)
    const request = store.getAll()
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error)
  })
}

export async function getEventsByDateRange(start: Date, end: Date): Promise<CalendarEvent[]> {
  const all = await getAllEvents()
  const startISO = start.toISOString()
  const endISO = end.toISOString()
  return all.filter((e) => {
    // Include if event overlaps with range
    return e.startTime < endISO && e.endTime > startISO
  })
}

export async function addEvent(input: CreateEventInput): Promise<CalendarEvent> {
  const db = await openDB()
  const event: CalendarEvent = {
    id: crypto.randomUUID(),
    title: input.title,
    description: input.description || "",
    startTime: input.startTime,
    endTime: input.endTime,
    isAllDay: input.isAllDay || false,
    isRecurring: input.isRecurring || false,
    recurrenceRule: input.recurrenceRule || "",
    category: input.category || "other",
    color: getCategoryColor(input.category || "other"),
    createdAt: new Date().toISOString(),
  }
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readwrite")
    const store = tx.objectStore(STORE_NAME)
    const request = store.add(event)
    request.onsuccess = () => resolve(event)
    request.onerror = () => reject(request.error)
  })
}

export async function updateEvent(event: CalendarEvent): Promise<void> {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readwrite")
    const store = tx.objectStore(STORE_NAME)
    const request = store.put(event)
    request.onsuccess = () => resolve()
    request.onerror = () => reject(request.error)
  })
}

export async function deleteEvent(id: string): Promise<void> {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readwrite")
    const store = tx.objectStore(STORE_NAME)
    const request = store.delete(id)
    request.onsuccess = () => resolve()
    request.onerror = () => reject(request.error)
  })
}

export async function deleteRecurringEvents(originalId: string): Promise<void> {
  const db = await openDB()
  const all = await getAllEvents()
  const toDelete = all.filter((e) => e.id === originalId || e.id.startsWith(originalId + "_"))
  const tx = db.transaction(STORE_NAME, "readwrite")
  const store = tx.objectStore(STORE_NAME)
  for (const e of toDelete) {
    store.delete(e.id)
  }
  return new Promise((resolve, reject) => {
    tx.oncomplete = () => resolve()
    tx.onerror = () => reject(tx.error)
  })
}

export function getCategoryColor(category: string): string {
  const colors: Record<string, string> = {
    work: "#4A90D9",
    personal: "#7ED321",
    health: "#F5A623",
    other: "#9B9B9B",
  }
  return colors[category] || colors.other
}
