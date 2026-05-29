<template>
  <Teleport to="body">
    <div v-if="visible" class="modal-overlay" @click.self="close">
      <div class="modal">
        <div class="modal-header">
          <h3>{{ isEditing ? "编辑事件" : "新建事件" }}</h3>
          <button class="close-btn" @click="close">&times;</button>
        </div>
        <div class="modal-body">
          <label>
            标题
            <input v-model="form.title" type="text" placeholder="事件标题" />
          </label>
          <label>
            描述
            <textarea v-model="form.description" rows="2" placeholder="可选"></textarea>
          </label>
          <div class="row">
            <label>
              开始时间
              <input v-model="form.startDate" type="date" />
              <input v-model="form.startTime" type="time" />
            </label>
          </div>
          <div class="row">
            <label>
              结束时间
              <input v-model="form.endDate" type="date" />
              <input v-model="form.endTime" type="time" />
            </label>
          </div>
          <label class="checkbox-label">
            <input v-model="form.isAllDay" type="checkbox" />
            全天事件
          </label>
          <div v-if="!form.isAllDay" class="row">
            <label>
              分类
              <select v-model="form.category">
                <option value="work">工作</option>
                <option value="personal">个人</option>
                <option value="health">健康</option>
                <option value="other">其他</option>
              </select>
            </label>
          </div>
          <div class="row">
            <label class="checkbox-label">
              <input v-model="form.isRecurring" type="checkbox" />
              周期性事件
            </label>
          </div>
          <div v-if="form.isRecurring">
            <label>
              重复规则
              <select v-model="form.recurrenceRule">
                <option value="FREQ=DAILY">每天</option>
                <option value="FREQ=WEEKLY;BYDAY=MO">每周一</option>
                <option value="FREQ=WEEKLY;BYDAY=TU">每周二</option>
                <option value="FREQ=WEEKLY;BYDAY=WE">每周三</option>
                <option value="FREQ=WEEKLY;BYDAY=TH">每周四</option>
                <option value="FREQ=WEEKLY;BYDAY=FR">每周五</option>
                <option value="FREQ=WEEKLY;BYDAY=SA">每周六</option>
                <option value="FREQ=WEEKLY;BYDAY=SU">每周日</option>
                <option value="FREQ=MONTHLY;BYMONTHDAY=1">每月1号</option>
                <option value="FREQ=MONTHLY;BYMONTHDAY=15">每月15号</option>
              </select>
            </label>
          </div>
          <div v-if="conflictResult?.hasConflict" class="conflict-warning">
            ⚠️ 时间冲突！已存在以下事件：
            <ul>
              <li v-for="c in conflictResult.conflicts" :key="c.id">
                {{ c.title }} ({{ formatDateShort(c.startTime) }})
              </li>
            </ul>
          </div>
        </div>
        <div class="modal-footer">
          <button v-if="isEditing" class="btn btn-danger" @click="handleDelete">删除</button>
          <div class="right-btns">
            <button class="btn btn-secondary" @click="close">取消</button>
            <button class="btn btn-primary" @click="handleSave">保存</button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, reactive, watch, computed } from "vue"
import dayjs from "dayjs"
import type { CalendarEvent, ConflictResult } from "../types/event"
import { useCalendarStore } from "../stores/calendar"
import { formatDateShort } from "../utils/calendar"

const props = defineProps<{
  visible: boolean
  event?: CalendarEvent | null
  defaultDate?: string | null
}>()

const emit = defineEmits<{
  close: []
  saved: []
  deleted: [id: string]
}>()

const store = useCalendarStore()
const isEditing = computed(() => !!props.event)

const form = reactive({
  title: "",
  description: "",
  startDate: "",
  startTime: "",
  endDate: "",
  endTime: "",
  isAllDay: false,
  category: "work" as string,
  isRecurring: false,
  recurrenceRule: "FREQ=WEEKLY;BYDAY=MO",
})

const conflictResult = ref<ConflictResult | null>(null)

watch(
  () => [props.visible, props.event, props.defaultDate],
  () => {
    if (!props.visible) return
    if (props.event) {
      const s = dayjs(props.event.startTime)
      const e = dayjs(props.event.endTime)
      form.title = props.event.title
      form.description = props.event.description
      form.startDate = s.format("YYYY-MM-DD")
      form.startTime = s.format("HH:mm")
      form.endDate = e.format("YYYY-MM-DD")
      form.endTime = e.format("HH:mm")
      form.isAllDay = props.event.isAllDay
      form.category = props.event.category
      form.isRecurring = props.event.isRecurring
      form.recurrenceRule = props.event.recurrenceRule || "FREQ=WEEKLY;BYDAY=MO"
    } else {
      const base = props.defaultDate ? dayjs(props.defaultDate) : dayjs()
      const start = base.hour(9).minute(0).second(0)
      const end = base.hour(10).minute(0).second(0)
      form.title = ""
      form.description = ""
      form.startDate = start.format("YYYY-MM-DD")
      form.startTime = start.format("HH:mm")
      form.endDate = end.format("YYYY-MM-DD")
      form.endTime = end.format("HH:mm")
      form.isAllDay = false
      form.category = "work"
      form.isRecurring = false
      form.recurrenceRule = "FREQ=WEEKLY;BYDAY=MO"
    }
    conflictResult.value = null
  },
  { immediate: true }
)

function handleSave() {
  if (!form.title.trim()) return

  const startTime = dayjs(`${form.startDate}T${form.startTime}:00`).toISOString()
  const endTime = dayjs(`${form.endDate}T${form.endTime}:00`).toISOString()

  const result = store.checkConflict(startTime, endTime, props.event?.id)
  if (result.hasConflict) {
    conflictResult.value = result
    return
  }

  if (isEditing.value && props.event) {
    store.editEvent({
      ...props.event,
      title: form.title,
      description: form.description,
      startTime,
      endTime,
      isAllDay: form.isAllDay,
      category: form.category as CalendarEvent["category"],
      isRecurring: form.isRecurring,
      recurrenceRule: form.recurrenceRule,
    }).then(() => {
      emit("saved")
      close()
    })
  } else {
    store.createEvent({
      title: form.title,
      description: form.description,
      startTime,
      endTime,
      isAllDay: form.isAllDay,
      category: form.category as CalendarEvent["category"],
      isRecurring: form.isRecurring,
      recurrenceRule: form.recurrenceRule,
    }).then(() => {
      emit("saved")
      close()
    })
  }
}

function handleDelete() {
  if (props.event) {
    store.removeEvent(props.event.id)
    emit("deleted", props.event.id)
    close()
  }
}

function close() {
  emit("close")
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.modal {
  background: #fff;
  border-radius: 12px;
  width: 460px;
  max-width: 90vw;
  max-height: 85vh;
  overflow-y: auto;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.15);
}
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #eee;
}
.modal-header h3 { margin: 0; font-size: 17px; }
.close-btn {
  background: none;
  border: none;
  font-size: 22px;
  cursor: pointer;
  color: #999;
  padding: 0 4px;
}
.modal-body {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.modal-body label {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 13px;
  color: #555;
}
.modal-body input[type="text"],
.modal-body input[type="date"],
.modal-body input[type="time"],
.modal-body textarea,
.modal-body select {
  padding: 8px 10px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
}
.row { display: flex; gap: 8px; align-items: flex-end; }
.row label { flex: 1; }
.checkbox-label {
  flex-direction: row !important;
  align-items: center;
  gap: 8px !important;
}
.conflict-warning {
  background: #fff3cd;
  border: 1px solid #ffc107;
  border-radius: 6px;
  padding: 10px 14px;
  font-size: 13px;
  color: #856404;
}
.conflict-warning ul { margin: 4px 0 0 16px; }
.modal-footer {
  display: flex;
  justify-content: space-between;
  padding: 14px 20px;
  border-top: 1px solid #eee;
}
.right-btns { display: flex; gap: 8px; }
.btn {
  padding: 8px 18px;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
}
.btn-primary { background: #4A90D9; color: #fff; }
.btn-primary:hover { background: #3a7bc8; }
.btn-secondary { background: #eee; color: #333; }
.btn-secondary:hover { background: #ddd; }
.btn-danger { background: #e74c3c; color: #fff; }
.btn-danger:hover { background: #c0392b; }
</style>
