<template>
  <Teleport to="body">
    <div v-if="visible" class="voice-overlay" @click.self="$emit('close')">
      <div class="voice-panel">
        <template v-if="state === 'idle'">
          <p>准备录音...</p>
        </template>
        <template v-if="state === 'recording'">
          <div class="waveform-container">
            <canvas ref="waveCanvas" class="waveform-canvas"></canvas>
          </div>
          <div class="recording-timer">{{ formatDuration(seconds) }}</div>
          <div class="mic-icon">🎤</div>
          <p class="state-text">正在聆听...</p>
          <button class="btn-stop" @click="stopRec">结束录音</button>
        </template>
        <template v-if="state === 'processing'">
          <div class="spinner"></div>
          <p class="state-text">识别中...</p>
        </template>
        <template v-if="state === 'done'">
          <div class="result-label">识别文字</div>
          <div class="result-text">{{ resultText }}</div>
          <div v-if="parseData" class="event-card">
            <div class="event-card-title">{{ parseData.title || '未命名事件' }}</div>
            <div class="event-card-row">📅 {{ parseData.date || '' }} {{ parseData.time || '' }}</div>
          </div>
          <div style="display:flex;gap:8px;justify-content:center;margin-top:12px">
            <button class="btn-confirm" @click="confirm">确认添加</button>
            <button class="btn-cancel" @click="$emit('close')">取消</button>
          </div>
        </template>
        <template v-if="state === 'error'">
          <p>{{ errMsg }}</p>
          <button class="btn-retry" @click="retry">重试</button>
        </template>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, watch, nextTick, onUnmounted } from "vue"
import dayjs from "dayjs"
import type { CreateEventInput } from "../types/event"

const props = defineProps<{ visible: boolean }>()
const emit = defineEmits<{ close: []; created: [input: CreateEventInput] }>()

const state = ref<"idle" | "recording" | "processing" | "done" | "error">("idle")
const seconds = ref(0)
const errMsg = ref("")
const resultText = ref("")
const parseData = ref<any>(null)
const waveCanvas = ref<HTMLCanvasElement | null>(null)

let audioCtx2: AudioContext | null = null
let scriptNode: ScriptProcessorNode | null = null
let sourceNode: MediaStreamAudioSourceNode | null = null
let pcmChunks: Float32Array[] = []
let stream: MediaStream | null = null
let timer: ReturnType<typeof setInterval> | null = null
let animId: number | null = null
let audioCtx: AudioContext | null = null
let analyserNode: AnalyserNode | null = null

function formatDuration(s: number) {
  const m = Math.floor(s / 60)
  const sec = s % 60
  return m + ":" + String(sec).padStart(2, "0")
}

watch(() => props.visible, async (v) => {
  if (v) {
    state.value = "idle"
    seconds.value = 0
    resultText.value = ""
    parseData.value = null
    errMsg.value = ""
    await nextTick()
    startRec()
  } else {
    cleanup()
  }
})

async function startRec() {
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    startWaveform(stream)
    pcmChunks = []
    const sr = 16000
    audioCtx2 = new AudioContext({ sampleRate: sr })
    sourceNode = audioCtx2.createMediaStreamSource(stream)
    scriptNode = audioCtx2.createScriptProcessor(4096, 1, 1)
    scriptNode.onaudioprocess = (e) => {
      pcmChunks.push(new Float32Array(e.inputBuffer.getChannelData(0)))
    }
    sourceNode.connect(scriptNode)
    scriptNode.connect(audioCtx2.destination)
    state.value = "recording"
    seconds.value = 0
    timer = setInterval(() => { seconds.value++ }, 1000)
  } catch (e: any) {
    state.value = "error"
    errMsg.value = "麦克风访问失败: " + (e.message || "")
  }
}

function stopRec() {
  scriptNode?.disconnect(); sourceNode?.disconnect(); audioCtx2?.close()
  state.value = "processing"
  stopWaveform()

  setTimeout(async () => {
    const blob = encodeWav(pcmChunks, 16000)
    try {
      const fd = new FormData()
      fd.append("file", blob, "rec.webm")
      const r1 = await fetch("/api/asr/recognize", { method: "POST", body: fd })
      const d1 = await r1.json()
      if (d1.status === 'success' && d1.text) { resultText.value = d1.text } else if (d1.status === 'mock') { resultText.value = getMock() } else { state.value = 'error'; errMsg.value = d1.error || '语音识别失败'; return }
      if (resultText.value) {
        const r2 = await fetch("/api/nlp/parse", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text: resultText.value }),
        })
        parseData.value = await r2.json()
      }
      state.value = "done"
    } catch (e: any) {
      state.value = "error"
      errMsg.value = e.message || "处理失败"
    }
  }, 300)
}

function retry() {
  cleanup()
  startRec()
}

function confirm() {
  if (!parseData.value) return
  const d = parseData.value
  const input: CreateEventInput = {
    title: d.title || "未命名事件",
    startTime: d.startTime || new Date().toISOString(),
    endTime: d.endTime || new Date(Date.now() + 3600000).toISOString(),
    isRecurring: d.isRecurring || false,
    recurrenceRule: d.recurrenceRule || "",
    category: "other",
  }
  emit("created", input)
  cleanup()
  emit("close")
}

function getMock() {
  const s = ["明天下午三点和产品经理开会", "下周一上午十点站会", "周五有什么安排"]
  return s[Math.floor(Math.random() * s.length)]
}

function cleanup() {
  stopWaveform()
  if (timer) { clearInterval(timer); timer = null }
  scriptNode?.disconnect(); sourceNode?.disconnect(); audioCtx2?.close()
  stream?.getTracks().forEach((t) => t.stop())
  stream = null
  }

// Waveform
function startWaveform(s: MediaStream) {
  nextTick(() => {
    const c = waveCanvas.value
    if (!c) return
    const ctx = c.getContext("2d")
    if (!ctx) return
    const dpr = window.devicePixelRatio || 1
    const r = c.getBoundingClientRect()
    c.width = r.width * dpr; c.height = r.height * dpr
    ctx.scale(dpr, dpr)
    const w = r.width; const h = r.height

    audioCtx = new AudioContext()
    analyserNode = audioCtx.createAnalyser()
    analyserNode.fftSize = 256; analyserNode.smoothingTimeConstant = 0.7
    audioCtx.createMediaStreamSource(s).connect(analyserNode)
    const data = new Uint8Array(analyserNode.frequencyBinCount)

    const bars = 48; const bw = (w/bars)*0.65; const gap = (w/bars)*0.35; const my = h/2
    function draw() {
      if (!analyserNode) return
      animId = requestAnimationFrame(draw)
      analyserNode.getByteFrequencyData(data)
      ctx.fillStyle = "rgba(245,247,250,0.25)"; ctx.fillRect(0,0,w,h)
      let sum = 0; for (let i=0;i<data.length;i++) sum += data[i]
      const avg = sum/data.length
      for (let i=0;i<bars;i++) {
        const v = data[Math.floor(i/bars*data.length)]/255
        const bh = Math.max(v*h*0.42, avg>3?2:1)
        const x = i*(bw+gap)+gap/2
        ctx.fillStyle = "hsla("+(200+i/bars*50)+",75%,55%,0.9)"
        ctx.beginPath(); ctx.roundRect(x,my-bh,bw,bh*2,3); ctx.fill()
      }
      if (avg>3) { ctx.strokeStyle="rgba(74,144,217,"+Math.min(avg/80,0.5)+")"; ctx.lineWidth=2; ctx.beginPath(); ctx.moveTo(0,my); ctx.lineTo(w,my); ctx.stroke() }
    }
    draw()
  })
}

function stopWaveform() {
  if (animId) { cancelAnimationFrame(animId); animId = null }
  if (audioCtx) { audioCtx.close().catch(()=>{}); audioCtx = null }
  analyserNode = null
}

onUnmounted(() => cleanup())

function encodeWav(chunks: Float32Array[], sr: number): Blob {
  let len = 0; for (const c of chunks) len += c.length
  const merged = new Float32Array(len); let off = 0
  for (const c of chunks) { merged.set(c, off); off += c.length }
  const pcm = new Int16Array(merged.length)
  for (let i = 0; i < merged.length; i++) {
    const s = Math.max(-1, Math.min(1, merged[i]))
    pcm[i] = s < 0 ? s * 0x8000 : s * 0x7FFF
  }
  const dataLen = pcm.length * 2
  const buf = new ArrayBuffer(44 + dataLen)
  const v = new DataView(buf)
  function ws(o: number, s: string) { for (let i=0;i<s.length;i++) v.setUint8(o+i,s.charCodeAt(i)) }
  ws(0,"RIFF"); v.setUint32(4,36+dataLen,true); ws(8,"WAVE"); ws(12,"fmt ")
  v.setUint32(16,16,true); v.setUint16(20,1,true); v.setUint16(22,1,true)
  v.setUint32(24,sr,true); v.setUint32(28,sr*2,true); v.setUint16(32,2,true); v.setUint16(34,16,true)
  ws(36,"data"); v.setUint32(40,dataLen,true)
  new Int16Array(buf,44).set(pcm)
  return new Blob([buf], { type: "audio/wav" })
}</script>

<style scoped>
.voice-overlay { position:fixed; inset:0; background:rgba(0,0,0,0.3); display:flex; align-items:center; justify-content:center; z-index:2000; }
.voice-panel { background:#fff; border-radius:16px; width:420px; max-width:90vw; padding:32px 24px; box-shadow:0 8px 40px rgba(0,0,0,0.2); text-align:center; }
.waveform-container { width:100%; height:100px; background:#f5f7fa; border-radius:12px; overflow:hidden; margin-bottom:8px; }
.waveform-canvas { width:100%; height:100%; }
.recording-timer { font-size:28px; font-weight:600; color:#e74c3c; }
.mic-icon { font-size:36px; animation:micBounce 0.6s ease-in-out infinite alternate; }
@keyframes micBounce { from{transform:scale(1)} to{transform:scale(1.15)} }
.state-text { font-size:18px; font-weight:600; margin:0; }
.spinner { width:40px; height:40px; border:3px solid #eee; border-top-color:#4A90D9; border-radius:50%; animation:spin 0.8s linear infinite; margin:0 auto; }
@keyframes spin { to{transform:rotate(360deg)} }
.btn-stop { padding:10px 32px; border:none; border-radius:24px; background:linear-gradient(135deg,#e74c3c,#c0392b); color:#fff; font-size:15px; cursor:pointer; }
.btn-confirm { padding:10px 24px; border:none; border-radius:8px; font-size:14px; cursor:pointer; background:#4A90D9; color:#fff; }
.btn-cancel,.btn-retry { padding:10px 24px; border:none; border-radius:8px; font-size:14px; cursor:pointer; background:#eee; color:#333; }
.btn-retry { background:#4A90D9;color:#fff; }
.result-label { font-size:12px; color:#999; margin-bottom:6px; }
.result-text { font-size:16px; font-weight:500; padding:10px 14px; background:#f5f7fa; border-radius:8px; margin-bottom:16px; text-align:left; }
.event-card { background:#f0f7ff; border:1px solid #cce0ff; border-radius:10px; padding:14px; margin-bottom:12px; text-align:left; }
.event-card-title { font-size:16px; font-weight:600; margin-bottom:8px; }
.event-card-row { font-size:14px; color:#555; }
</style>