<template>
  <Teleport to="body">
    <Transition name="cp">
      <div v-if="visible" class="cp-overlay">
        <div class="cp-panel" :class="{ expanded: isExpanded }">
          <div class="cp-header">
            <div class="cp-header-left">
              <span class="cp-avatar">🤖</span>
              <div>
                <div class="cp-title">AI 日程助手</div>
                <div class="cp-subtitle">{{ mockMode ? '离线模式' : '在线' }}</div>
              </div>
            </div>
            <div class="cp-header-right">
              <button class="cp-icon-btn" @click="isExpanded = !isExpanded" :title="isExpanded ? '收起' : '展开'">
                {{ isExpanded ? '⊖' : '⊕' }}
              </button>
              <button class="cp-icon-btn" @click="resetChat" title="新对话">→</button>
              <button class="cp-icon-btn cp-close" @click="close">✕</button>
            </div>
          </div>
          <div class="cp-messages" ref="msgContainer">
            <div v-if="messages.length === 0" class="cp-welcome">
              <div class="cp-welcome-icon">🎉</div>
              <div class="cp-welcome-title">有什么我可以帮你的？</div>
              <div class="cp-welcome-hints">
                <button v-for="h in hints" :key="h" class="cp-hint" @click="sendText(h)">{{ h }}</button>
              </div>
            </div>
            <div v-for="(msg, i) in messages" :key="i" class="cp-msg-row" :class="msg.role">
              <div class="cp-msg-bubble" :class="msg.role">
                <div class="cp-msg-text">{{ msg.text }}</div>
                <div v-if="msg.slots && msg.slots.length" class="cp-slots-inline">
                  <SlotPicker :slots="msg.slots" :loading="false" @select="handleSlotSelect($event, msg)" />
                </div>
              </div>
            </div>
            <div v-if="thinking" class="cp-msg-row assistant">
              <div class="cp-msg-bubble assistant thinking">
                <span class="cp-dot">●</span><span class="cp-dot">●</span><span class="cp-dot">●</span>
              </div>
            </div>
          </div>
          <div class="cp-input-area">
            <div v-if="isRecording" class="cp-recording-bar">
              <span class="cp-rec-dot"></span>
              <span>录音中...</span>
              <button class="cp-icon-btn cp-stop-rec" @click="stopRecording">⏹ 结束</button>
            </div>
            <div v-else class="cp-input-row">
              <button class="cp-icon-btn cp-mic-btn" @click="startRecording" :disabled="thinking">🎤</button>
              <input ref="textInput" v-model="textDraft" class="cp-text-input" autocomplete="off"
                placeholder="输入消息，或点击麦克风..." @keydown.enter="sendText(textDraft)" :disabled="thinking" />
              <button class="cp-send-btn" @click="sendText(textDraft)"
                :disabled="!textDraft.trim() || thinking">发送</button>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, watch, nextTick, onUnmounted, computed } from "vue"
import SlotPicker from "./SlotPicker.vue"
import { useCalendarStore } from "../stores/calendar"

const props = defineProps<{ visible: boolean }>()
const emit = defineEmits<{ close: []; created: [input: any] }>()

const store = useCalendarStore()

interface ChatMessage {
  role: "user" | "assistant"
  text: string
  slots?: any[]
  action?: any
}

const messages = ref<ChatMessage[]>([])
const thinking = ref(false)
const textDraft = ref("")
const textInput = ref<HTMLInputElement | null>(null)
const msgContainer = ref<HTMLDivElement | null>(null)
const sessionId = ref<string | null>(null)
const isExpanded = ref(true)
const isRecording = ref(false)

let recTimer: any = null
let _audioCleanup: (() => void) | null = null
let _pcmChunks: Float32Array[] | null = null

const mockMode = computed(() => true)

const hints = [
  "明天下午三点和产品经理开会",
  "本周找个2小时深度工作时间",
  "今天有什么安排？",
  "下周一上午十点站会",
]

function scrollToBottom() {
  nextTick(() => {
    if (msgContainer.value) msgContainer.value.scrollTop = msgContainer.value.scrollHeight
  })
}

function sendText(text: string) {
  const trimmed = text.trim()
  if (!trimmed || thinking.value) return
  textDraft.value = ""
  messages.value.push({ role: "user", text: trimmed })
  scrollToBottom()
  thinking.value = true
  const events = store.events.map(e => ({
    id: e.id, title: e.title, startTime: e.startTime, endTime: e.endTime,
    isAllDay: e.isAllDay, isRecurring: e.isRecurring, recurrenceRule: e.recurrenceRule,
    category: e.category, color: e.color,
  }))
  fetch("/api/dialogue/message", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text: trimmed, session_id: sessionId.value, events }),
  })
    .then(res => res.json())
    .then(data => {
      sessionId.value = data.session_id
      const msg: ChatMessage = { role: "assistant", text: data.reply, action: data.action }
      if (data.action) {
        const act = Array.isArray(data.action) ? data.action[0] : data.action
        if (act?.tool === "find_free_slots" && act.result?.slots) msg.slots = act.result.slots
        if (act?.tool === "create_event" && act.result?.status === "created") {
          const ev = act.result.event
          emit("created", {
            title: ev.title, startTime: ev.startTime, endTime: ev.endTime,
            isRecurring: ev.isRecurring, recurrenceRule: ev.recurrenceRule, category: ev.category,
          })
        }
      }
      messages.value.push(msg)
    })
    .catch(() => {
      messages.value.push({ role: "assistant", text: "抱歉，网络出了问题，请稍后重试。" })
    })
    .finally(() => {
      thinking.value = false
      scrollToBottom()
    })
}

function startRecording() {
  navigator.mediaDevices.getUserMedia({ audio: true }).then(stream => {
    const audioCtx = new AudioContext({ sampleRate: 16000 })
    const source = audioCtx.createMediaStreamSource(stream)
    const scriptNode = audioCtx.createScriptProcessor(4096, 1, 1)
    const pcmChunks: Float32Array[] = []

    scriptNode.onaudioprocess = (e) => {
      pcmChunks.push(new Float32Array(e.inputBuffer.getChannelData(0)))
    }
    source.connect(scriptNode)
    scriptNode.connect(audioCtx.destination)

    isRecording.value = true
    recTimer = setInterval(() => {}, 1000)

    _audioCleanup = () => {
      try { scriptNode.disconnect() } catch {}
      try { source.disconnect() } catch {}
      try { audioCtx.close() } catch {}
      try { stream.getTracks().forEach(t => t.stop()) } catch {}
    }
    _pcmChunks = pcmChunks
  }).catch((e: any) => {
    messages.value.push({ role: "assistant", text: "麦克风访问失败：" + (e.message || "") })
  })
}

function encodeWav(chunks: Float32Array[]): Blob {
  let totalLen = 0
  for (const c of chunks) totalLen += c.length
  const merged = new Float32Array(totalLen)
  let off = 0
  for (const c of chunks) { merged.set(c, off); off += c.length }
  const pcm = new Int16Array(merged.length)
  for (let i = 0; i < merged.length; i++) {
    const s = Math.max(-1, Math.min(1, merged[i]))
    pcm[i] = s < 0 ? s * 0x8000 : s * 0x7FFF
  }
  const dataLen = pcm.length * 2
  const buffer = new ArrayBuffer(44 + dataLen)
  const view = new DataView(buffer)
  const ws = (pos: number, str: string) => { for (let i = 0; i < str.length; i++) view.setUint8(pos + i, str.charCodeAt(i)) }
  ws(0, "RIFF"); view.setUint32(4, 36 + dataLen, true); ws(8, "WAVE"); ws(12, "fmt ")
  view.setUint32(16, 16, true); view.setUint16(20, 1, true); view.setUint16(22, 1, true)
  view.setUint32(24, 16000, true); view.setUint32(28, 32000, true); view.setUint16(32, 2, true); view.setUint16(34, 16, true)
  ws(36, "data"); view.setUint32(40, dataLen, true)
  new Int16Array(buffer, 44).set(pcm)
  return new Blob([buffer], { type: "audio/wav" })
}

function fallbackMock() {
  const samples = [
    "明天下午三点和产品经理开会",
    "下周一上午十点站会",
    "周五有什么安排",
     "取消明天的会议",
     "后天晚上七点去健身房",
  ]
  sendText(samples[Math.floor(Math.random() * samples.length)])
}

function stopRecording() {
  if (!isRecording.value) return
  isRecording.value = false
  if (recTimer) { clearInterval(recTimer); recTimer = null }
  if (_audioCleanup) { _audioCleanup(); _audioCleanup = null }
  const chunks = _pcmChunks
  _pcmChunks = null
  if (!chunks || chunks.length === 0) { fallbackMock(); return }

  const wavBlob = encodeWav(chunks)
  if (wavBlob.size < 100) { fallbackMock(); return }

  // Try iFlytek ASR with 5s timeout
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), 5000)
  const fd = new FormData()
  fd.append("file", wavBlob, "recording.wav")

  fetch("/api/asr/recognize", { method: "POST", body: fd, signal: controller.signal })
    .then(r => { clearTimeout(timeout); return r.json() })
    .then(d => {
      if (d.status === "success" && d.text) {
        sendText(d.text)
      } else {
        fallbackMock()
      }
    })
    .catch(() => {
      clearTimeout(timeout)
      fallbackMock()
    })
}

function resetChat() {
  messages.value = []
  sessionId.value = null
  fetch("/api/dialogue/reset", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId.value || "", text: "" }),
  }).catch(() => {})
}

function handleSlotSelect(slot: any, _msg: ChatMessage) {
  const text = "在" + slot.date + " " + slot.start + " 创建事件，时长" + slot.duration_minutes + "分钟"
  sendText(text)
}

function close() { stopRecording(); emit("close") }

watch(() => props.visible, (v) => {
  if (v) { textDraft.value = ""; nextTick(() => textInput.value?.focus()) }
  else stopRecording()
})

onUnmounted(() => { stopRecording() })
</script>

<style scoped>
.cp-overlay{position:fixed;inset:0;z-index:2000;display:flex;justify-content:flex-end;pointer-events:none}
.cp-panel{pointer-events:all;width:420px;max-width:100vw;height:100vh;background:var(--bg-surface);border-left:1px solid var(--border);display:flex;flex-direction:column;box-shadow:-4px 0 24px rgba(0,0,0,0.08)}
.cp-panel.expanded{width:520px}
.cp-header{display:flex;align-items:center;justify-content:space-between;padding:16px 20px;border-bottom:1px solid var(--border);flex-shrink:0}
.cp-header-left{display:flex;align-items:center;gap:12px}
.cp-avatar{font-size:28px}
.cp-title{font-size:16px;font-weight:700}
.cp-subtitle{font-size:11px;color:var(--text-tertiary)}
.cp-header-right{display:flex;gap:4px}
.cp-icon-btn{width:32px;height:32px;border:none;border-radius:8px;background:transparent;font-size:16px;cursor:pointer;display:flex;align-items:center;justify-content:center;color:var(--text-secondary);transition:all 150ms}
.cp-icon-btn:hover{background:var(--bg-hover);color:var(--text-primary)}
.cp-close:hover{background:var(--danger);color:white}
.cp-messages{flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:12px}
.cp-welcome{text-align:center;padding:40px 10px}
.cp-welcome-icon{font-size:48px;margin-bottom:12px}
.cp-welcome-title{font-size:17px;font-weight:600;margin-bottom:16px}
.cp-welcome-hints{display:flex;flex-wrap:wrap;gap:8px;justify-content:center}
.cp-hint{padding:8px 14px;border:1px solid var(--border);border-radius:20px;background:var(--bg-primary);font-size:13px;color:var(--text-secondary);cursor:pointer;font-family:var(--font-sans);transition:all 150ms}
.cp-hint:hover{border-color:var(--accent);color:var(--accent)}
.cp-msg-row{display:flex}
.cp-msg-row.user{justify-content:flex-end}
.cp-msg-row.assistant{justify-content:flex-start}
.cp-msg-bubble{max-width:85%;padding:10px 14px;border-radius:16px;font-size:14px;line-height:1.55}
.cp-msg-bubble.user{background:var(--accent);color:white;border-bottom-right-radius:4px}
.cp-msg-bubble.assistant{background:var(--bg-primary);border:1px solid var(--border);border-bottom-left-radius:4px}
.cp-msg-bubble.thinking{padding:12px 18px;display:flex;gap:4px}
.cp-msg-text{white-space:pre-wrap;word-break:break-word}
.cp-dot{animation:cpBounce 1.2s infinite;font-size:8px;color:var(--text-tertiary)}
.cp-dot:nth-child(2){animation-delay:0.2s}
.cp-dot:nth-child(3){animation-delay:0.4s}
@keyframes cpBounce{0%,60%,100%{transform:translateY(0);opacity:.3}30%{transform:translateY(-6px);opacity:1}}
.cp-slots-inline{margin-top:10px}
.cp-input-area{padding:12px 16px;border-top:1px solid var(--border);flex-shrink:0}
.cp-recording-bar{display:flex;align-items:center;gap:10px;padding:10px 14px;background:var(--danger);color:white;border-radius:12px;font-size:14px;font-weight:500}
.cp-rec-dot{width:10px;height:10px;border-radius:50%;background:white;animation:cpPulse 1s infinite}
@keyframes cpPulse{0%,100%{opacity:1}50%{opacity:.3}}
.cp-stop-rec{margin-left:auto;color:white!important;font-size:14px!important;width:auto!important;padding:0 8px!important}
.cp-input-row{display:flex;align-items:center;gap:8px}
.cp-mic-btn{width:40px;height:40px;font-size:20px;flex-shrink:0}
.cp-mic-btn:hover{background:var(--accent-soft)}
.cp-text-input{flex:1;border:1px solid var(--border);border-radius:20px;padding:8px 16px;font-size:14px;font-family:var(--font-sans);background:var(--bg-primary);color:var(--text-primary);outline:none;transition:border-color 150ms}
.cp-text-input:focus{border-color:var(--accent)}
.cp-send-btn{padding:8px 18px;border:none;border-radius:20px;background:var(--accent);color:white;font-size:14px;font-weight:600;font-family:var(--font-sans);cursor:pointer;transition:all 150ms;flex-shrink:0}
.cp-send-btn:hover{background:var(--accent-hover)}
.cp-send-btn:disabled{opacity:.4;cursor:not-allowed}
.cp-enter-active,.cp-leave-active{transition:all 250ms cubic-bezier(.4,0,.2,1)}
.cp-enter-from,.cp-leave-to{opacity:0}
.cp-enter-from .cp-panel,.cp-leave-to .cp-panel{transform:translateX(40px)}
</style>
