<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="visible" class="modal-overlay" @click.self="close">
        <div class="modal">
          <div class="modal-header">
            <h3>{{ isEditing ? '编辑事件' : '新建事件' }}</h3>
            <button class="close-btn" @click="close">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
          </div>

          <div class="modal-body">
            <div class="field">
              <input v-model="form.title" type="text" placeholder="事件标题" class="input" autofocus />
            </div>

            <div class="field-row">
              <div class="field">
                <label class="label">日期</label>
                <input v-model="form.startDate" type="date" class="input" />
              </div>
              <div class="field" v-if="!form.isAllDay">
                <label class="label">时间</label>
                <input v-model="form.startTime" type="time" class="input" />
              </div>
            </div>

            <div class="field-row" v-if="!form.isAllDay">
              <div class="field">
                <label class="label">结束日期</label>
                <input v-model="form.endDate" type="date" class="input" />
              </div>
              <div class="field">
                <label class="label">结束时间</label>
                <input v-model="form.endTime" type="time" class="input" />
              </div>
            </div>

            <div class="field">
              <textarea v-model="form.description" rows="2" placeholder="添加描述..." class="input textarea"></textarea>
            </div>

            <div class="field-row">
              <div class="field">
                <label class="label">分类</label>
                <select v-model="form.category" class="input select">
                  <option value="work">💼 工作</option>
                  <option value="personal">👤 个人</option>
                  <option value="health">💚 健康</option>
                  <option value="other">📌 其他</option>
                </select>
              </div>
            </div>

            <div class="toggle-row">
              <label class="toggle">
                <input v-model="form.isAllDay" type="checkbox" />
                <span class="toggle-track"></span>
                全天事件
              </label>
              <label class="toggle">
                <input v-model="form.isRecurring" type="checkbox" />
                <span class="toggle-track"></span>
                周期性
              </label>
            </div>

            <div v-if="form.isRecurring" class="field">
              <select v-model="form.recurrenceRule" class="input select">
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
            </div>

            <div v-if="conflictResult?.hasConflict" class="conflict-box">
              <div class="conflict-title">⚠️ 时间冲突</div>
              <div v-for="c in conflictResult.conflicts" :key="c.id" class="conflict-item">
                {{ c.title }} · {{ formatDateShort(c.startTime) }}
              </div>
            </div>
          </div>

          <div class="modal-footer">
            <button v-if="isEditing" class="btn btn-danger" @click="handleDelete">删除</button>
            <div class="footer-right">
              <button class="btn btn-ghost" @click="close">取消</button>
              <button class="btn btn-primary" @click="handleSave">保存</button>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, reactive, watch, computed } from "vue"
import dayjs from "dayjs"
import type { CalendarEvent, ConflictResult } from "../types/event"
import { useCalendarStore } from "../stores/calendar"
import { formatDateShort } from "../utils/calendar"

const props = defineProps<{ visible: boolean; event?: CalendarEvent | null; defaultDate?: string | null }>()
const emit = defineEmits<{ close: []; saved: []; deleted: [id: string] }>()

const store = useCalendarStore()
const isEditing = computed(() => !!props.event)
const conflictResult = ref<ConflictResult | null>(null)

const form = reactive({
  title: "", description: "", startDate: "", startTime: "",
  endDate: "", endTime: "", isAllDay: false,
  category: "work" as string, isRecurring: false,
  recurrenceRule: "FREQ=WEEKLY;BYDAY=MO",
})

watch(() => [props.visible, props.event, props.defaultDate], () => {
  if (!props.visible) return
  if (props.event) {
    const s = dayjs(props.event.startTime)
    const e = dayjs(props.event.endTime)
    form.title = props.event.title; form.description = props.event.description
    form.startDate = s.format("YYYY-MM-DD"); form.startTime = s.format("HH:mm")
    form.endDate = e.format("YYYY-MM-DD"); form.endTime = e.format("HH:mm")
    form.isAllDay = props.event.isAllDay; form.category = props.event.category
    form.isRecurring = props.event.isRecurring
    form.recurrenceRule = props.event.recurrenceRule || "FREQ=WEEKLY;BYDAY=MO"
  } else {
    const base = props.defaultDate ? dayjs(props.defaultDate) : dayjs()
    const s = base.minute(0).second(0)
    form.title = ""; form.description = ""
    form.startDate = s.format("YYYY-MM-DD"); form.startTime = s.format("HH:mm")
    form.endDate = s.add(1,"hour").format("YYYY-MM-DD"); form.endTime = s.add(1,"hour").format("HH:mm")
    form.isAllDay = false; form.category = "work"
    form.isRecurring = false; form.recurrenceRule = "FREQ=WEEKLY;BYDAY=MO"
  }
  conflictResult.value = null
}, { immediate: true })

function handleSave() {
  if (!form.title.trim()) return
  const st = form.isAllDay
    ? dayjs(form.startDate).startOf("day").format("YYYY-MM-DDTHH:mm:ss")
    : dayjs(form.startDate + "T" + form.startTime + ":00").format("YYYY-MM-DDTHH:mm:ss")
  const et = form.isAllDay
    ? dayjs(form.endDate || form.startDate).endOf("day").format("YYYY-MM-DDTHH:mm:ss")
    : dayjs(form.endDate + "T" + form.endTime + ":00").format("YYYY-MM-DDTHH:mm:ss")

  const cr = store.checkConflict(st, et, props.event?.id)
  if (cr.hasConflict) { conflictResult.value = cr; return }

  if (isEditing.value && props.event) {
    store.editEvent({ ...props.event, title: form.title, description: form.description,
      startTime: st, endTime: et, isAllDay: form.isAllDay,
      category: form.category as any, isRecurring: form.isRecurring,
      recurrenceRule: form.recurrenceRule,
    }).then(() => { emit("saved"); close() })
  } else {
    store.createEvent({ title: form.title, description: form.description,
      startTime: st, endTime: et, isAllDay: form.isAllDay,
      category: form.category as any, isRecurring: form.isRecurring,
      recurrenceRule: form.recurrenceRule,
    }).then(() => { emit("saved"); close() })
  }
}

function handleDelete() {
  if (props.event) { store.removeEvent(props.event.id); emit("deleted", props.event.id); close() }
}
function close() { emit("close") }
</script>

<style scoped>
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.3);
  backdrop-filter: blur(4px);
  display: flex; align-items: center; justify-content: center;
  z-index: 1000;
}
.modal {
  background: var(--bg-surface); border-radius: var(--radius-xl);
  width: 460px; max-width: 92vw; max-height: 85vh; overflow-y: auto;
  box-shadow: var(--shadow-xl);
}
.modal-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: var(--space-5) var(--space-6);
  border-bottom: 1px solid var(--border-light);
}
.modal-header h3 { font-size: 17px; font-weight: 600; }
.close-btn { background: none; border: none; color: var(--text-tertiary); cursor: pointer; padding: 4px; border-radius: 6px; }
.close-btn:hover { background: var(--bg-hover); color: var(--text-primary); }
.modal-body { padding: var(--space-6); display: flex; flex-direction: column; gap: var(--space-4); }
.modal-footer {
  display: flex; justify-content: space-between; align-items: center;
  padding: var(--space-4) var(--space-6); border-top: 1px solid var(--border-light);
}
.footer-right { display: flex; gap: var(--space-2); }

.field { display: flex; flex-direction: column; gap: 4px; flex: 1; }
.field-row { display: flex; gap: var(--space-3); }
.label { font-size: 12px; font-weight: 500; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.5px; }
.input {
  padding: 10px 12px; border: 1px solid var(--border); border-radius: var(--radius-sm);
  font-size: 14px; font-family: var(--font-sans); background: var(--bg-surface);
  color: var(--text-primary); transition: border-color var(--transition);
  outline: none;
}
.input:focus { border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-light); }
.input::placeholder { color: var(--text-tertiary); }
.textarea { resize: vertical; }
.select { cursor: pointer; }

.toggle-row { display: flex; gap: var(--space-6); }
.toggle {
  display: flex; align-items: center; gap: var(--space-2);
  font-size: 13px; color: var(--text-secondary); cursor: pointer;
}
.toggle input { display: none; }
.toggle-track {
  width: 36px; height: 20px; border-radius: 10px;
  background: var(--border); position: relative; transition: all var(--transition);
}
.toggle-track::after {
  content: ''; position: absolute; top: 2px; left: 2px;
  width: 16px; height: 16px; border-radius: 50%;
  background: white; transition: all var(--transition);
}
.toggle input:checked + .toggle-track { background: var(--accent); }
.toggle input:checked + .toggle-track::after { left: 18px; }

.btn {
  padding: 8px 16px; border: none; border-radius: var(--radius-sm);
  font-size: 14px; font-weight: 500; font-family: var(--font-sans);
  cursor: pointer; transition: all var(--transition);
}
.btn-primary { background: var(--accent); color: var(--text-inverse); }
.btn-primary:hover { background: var(--accent-hover); }
.btn-ghost { background: transparent; color: var(--text-secondary); }
.btn-ghost:hover { background: var(--bg-hover); }
.btn-danger { background: transparent; color: var(--danger); }
.btn-danger:hover { background: #fef2f2; }

.conflict-box {
  background: #fef8e7; border: 1px solid #fde68a;
  border-radius: var(--radius-sm); padding: var(--space-4);
}
.conflict-title { font-size: 13px; font-weight: 600; color: #92400e; margin-bottom: 4px; }
.conflict-item { font-size: 13px; color: #a16207; }

.modal-enter-active, .modal-leave-active { transition: all 200ms ease; }
.modal-enter-from, .modal-leave-to { opacity: 0; }
.modal-enter-from .modal, .modal-leave-to .modal { transform: scale(0.95) translateY(10px); }
</style>
