export interface CalendarEvent {
  id: string
  title: string
  description: string
  startTime: string // ISO 8601
  endTime: string   // ISO 8601
  isAllDay: boolean
  isRecurring: boolean
  recurrenceRule: string // RFC 5545 RRULE e.g. "FREQ=WEEKLY;BYDAY=MO"
  category: "work" | "personal" | "health" | "other"
  color: string
  createdAt: string
}

export interface CreateEventInput {
  title: string
  description?: string
  startTime: string
  endTime: string
  isAllDay?: boolean
  isRecurring?: boolean
  recurrenceRule?: string
  category?: CalendarEvent["category"]
}

export interface VoiceParseResult {
  intent: "add" | "delete" | "query" | "unknown"
  params: {
    title?: string
    date?: string
    time?: string
    startTime?: string
    endTime?: string
    isRecurring?: boolean
    recurrenceRule?: string
  }
  rawText: string
  confidence: number
}

export interface ConflictResult {
  hasConflict: boolean
  conflicts: CalendarEvent[]
}
