<template>
  <Teleport to="body">
    <Transition name="vp">
      <div v-if="visible" class="vp-overlay" @click.self="close">
        <div class="vp-card">
          <!-- Recording -->
          <template v-if="state === 'recording'">
            <div class="vp-wave"><canvas ref="wc" class="vp-canvas"></canvas></div>
            <div class="vp-timer">{{ fmt(seconds) }}</div>
            <div class="vp-mic">🎤</div>
            <p class="vp-text">正在聆听...</p>
            <button class="vp-btn vp-btn-stop" @click="stopRec">结束录音</button>
          </template>

          <!-- Processing -->
          <template v-if="state === 'processing'">
            <div class="vp-spinner"></div>
            <p class="vp-text">识别中...</p>
          </template>

          <!-- Done -->
          <template v-if="state === 'done'">
            <div class="vp-result-label">识别内容</div>
            <div class="vp-result-text">{{ resultText }}</div>
            <div v-if="parseData" class="vp-event-card">
              <div class="vp-event-title">{{ parseData.title || '未命名' }}</div>
              <div class="vp-event-row">📅 {{ parseData.date || '' }} {{ parseData.time || '' }}</div>
              <div v-if="parseData.isRecurring" class="vp-event-row">🔄 周期性事件</div>
            </div>
            <div class="vp-actions">
              <button class="vp-btn vp-btn-primary" @click="confirm">确认添加</button>
              <button class="vp-btn vp-btn-ghost" @click="close">取消</button>
            </div>
          </template>

          <!-- Error -->
          <template v-if="state === 'error'">
            <p>{{ errMsg }}</p>
            <div class="vp-actions">
              <button class="vp-btn vp-btn-primary" @click="retry">重试</button>
              <button class="vp-btn vp-btn-ghost" @click="close">关闭</button>
            </div>
          </template>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, watch, nextTick, onUnmounted } from "vue"
import type { CreateEventInput } from "../types/event"

const props = defineProps<{ visible: boolean }>()
const emit = defineEmits<{ close: []; created: [input: CreateEventInput] }>()

const state = ref<"idle"|"recording"|"processing"|"done"|"error">("idle")
const seconds = ref(0); const errMsg = ref("")
const resultText = ref(""); const parseData = ref<any>(null)
const wc = ref<HTMLCanvasElement | null>(null)

let stream: MediaStream | null = null
let ac: AudioContext | null = null; let an: AnalyserNode | null = null
let timer: any = null; let aid: number | null = null
let pcm: Float32Array[] = []; let sn: ScriptProcessorNode | null = null; let src: MediaStreamAudioSourceNode | null = null

function fmt(s: number) { return Math.floor(s/60) + ":" + String(s%60).padStart(2,"0") }

watch(() => props.visible, async v => {
  if (v) { state.value="idle"; seconds.value=0; resultText.value=""; parseData.value=null; errMsg.value=""; await nextTick(); startRec() }
  else cleanup()
})

async function startRec() {
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    waveStart(stream)
    pcm = []
    ac = new AudioContext({ sampleRate: 16000 })
    src = ac.createMediaStreamSource(stream)
    sn = ac.createScriptProcessor(4096, 1, 1)
    sn.onaudioprocess = e => pcm.push(new Float32Array(e.inputBuffer.getChannelData(0)))
    src.connect(sn); sn.connect(ac.destination)
    state.value = "recording"; seconds.value = 0
    timer = setInterval(() => seconds.value++, 1000)
  } catch (e: any) { state.value = "error"; errMsg.value = "麦克风失败: " + (e.message||"") }
}

function stopRec() {
  sn?.disconnect(); src?.disconnect(); ac?.close()
  if (timer) { clearInterval(timer); timer = null }
  stream?.getTracks().forEach(t => t.stop()); stream = null
  waveStop(); state.value = "processing"

  setTimeout(async () => {
    const blob = encodeWav(pcm, 16000)
    try {
      const fd = new FormData(); fd.append("file", blob, "r.wav")
      const r1 = await fetch("/api/asr/recognize", { method:"POST", body: fd })
      const d1 = await r1.json()
      if (d1.status === "success" && d1.text) resultText.value = d1.text
      else if (d1.status === "mock") resultText.value = mockText()
      else { state.value="error"; errMsg.value = d1.error || "识别失败"; return }
      if (resultText.value) {
        const r2 = await fetch("/api/nlp/parse", { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({text:resultText.value}) })
        parseData.value = await r2.json()
      }
      state.value = "done"
    } catch (e: any) { state.value="error"; errMsg.value = e.message||"处理失败" }
  }, 300)
}

function retry() { cleanup(); startRec() }
function mockText() { const s=["明天下午三点开会","下周一上午十点站会","周五有什么安排"]; return s[Math.floor(Math.random()*s.length)] }

function confirm() {
  if (!parseData.value) return
  const d = parseData.value
  emit("created", { title: d.title||"未命名", startTime: d.startTime||new Date().toISOString(),
    endTime: d.endTime||new Date(Date.now()+3600000).toISOString(),
    isRecurring: d.isRecurring||false, recurrenceRule: d.recurrenceRule||"", category:"other" })
  cleanup(); emit("close")
}

function close() { waveStop(); cleanup(); emit("close") }

function cleanup() {
  waveStop()
  if (timer) { clearInterval(timer); timer = null }
  sn?.disconnect(); src?.disconnect(); ac?.close()
  stream?.getTracks().forEach(t => t.stop()); stream = null
  sn = null; src = null; ac = null; pcm = []
}

// Waveform
function waveStart(s: MediaStream) {
  nextTick(() => {
    const c = wc.value; if (!c) return
    const ctx = c.getContext("2d"); if (!ctx) return
    const dpr = devicePixelRatio||1; const r = c.getBoundingClientRect()
    c.width=r.width*dpr; c.height=r.height*dpr; ctx.scale(dpr,dpr)
    const w=r.width,h=r.height

    const actx = new AudioContext(); an = actx.createAnalyser()
    an.fftSize=256; an.smoothingTimeConstant=0.7
    actx.createMediaStreamSource(s).connect(an)
    const data = new Uint8Array(an.frequencyBinCount)
    const bars=48,bw=(w/bars)*0.6,gap=(w/bars)*0.4,my=h/2

    function draw() { if(!an)return; aid=requestAnimationFrame(draw)
      an.getByteFrequencyData(data)
      ctx!.fillStyle="rgba(250,249,247,0.2)"; ctx!.fillRect(0,0,w,h)
      let sum=0; for(let i=0;i<data.length;i++) sum+=data[i]
      const avg=sum/data.length
      for(let i=0;i<bars;i++){const v=data[Math.floor(i/bars*data.length)]/255
        const bh=Math.max(v*h*0.42,avg>3?2:1); const x=i*(bw+gap)+gap/2
        ctx!.fillStyle="hsla("+(220+i/bars*40)+",70%,58%,0.85)"
        ctx!.beginPath(); ctx!.roundRect(x,my-bh,bw,bh*2,3); ctx!.fill()}
      if(avg>3){ctx!.strokeStyle="rgba(91,95,227,"+Math.min(avg/80,0.5)+")"
        ctx!.lineWidth=2; ctx!.beginPath(); ctx!.moveTo(0,my); ctx!.lineTo(w,my); ctx!.stroke()}
    }; draw()
  })
}
function waveStop() { if(aid){cancelAnimationFrame(aid);aid=null}; an=null }

onUnmounted(() => cleanup())

// WAV encoder
function encodeWav(c: Float32Array[], sr: number): Blob {
  let l=0; for(const x of c) l+=x.length
  const m=new Float32Array(l); let o=0; for(const x of c){m.set(x,o);o+=x.length}
  const p=new Int16Array(m.length)
  for(let i=0;i<m.length;i++){const s=Math.max(-1,Math.min(1,m[i]));p[i]=s<0?s*0x8000:s*0x7FFF}
  const dl=p.length*2; const b=new ArrayBuffer(44+dl); const v=new DataView(b)
  const ws=(o2:number,s:string)=>{for(let i=0;i<s.length;i++)v.setUint8(o2+i,s.charCodeAt(i))}
  ws(0,"RIFF"); v.setUint32(4,36+dl,true); ws(8,"WAVE"); ws(12,"fmt ")
  v.setUint32(16,16,true); v.setUint16(20,1,true); v.setUint16(22,1,true)
  v.setUint32(24,sr,true); v.setUint32(28,sr*2,true); v.setUint16(32,2,true); v.setUint16(34,16,true)
  ws(36,"data"); v.setUint32(40,dl,true); new Int16Array(b,44).set(p)
  return new Blob([b],{type:"audio/wav"})
}
</script>

<style scoped>
.vp-overlay { position:fixed; inset:0; background:rgba(0,0,0,0.3); backdrop-filter:blur(4px); display:flex; align-items:center; justify-content:center; z-index:2000; }
.vp-card { background:var(--bg-surface); border-radius:var(--radius-xl); width:400px; max-width:92vw; padding:var(--space-8); box-shadow:var(--shadow-xl); text-align:center; }
.vp-wave { width:100%; height:90px; background:var(--bg-primary); border-radius:var(--radius-md); overflow:hidden; margin-bottom:var(--space-4); }
.vp-canvas { width:100%; height:100%; }
.vp-timer { font-size:32px; font-weight:700; color:var(--accent); font-variant-numeric:tabular-nums; margin-bottom:var(--space-2); }
.vp-mic { font-size:32px; animation:vpBounce 0.6s ease-in-out infinite alternate; }
@keyframes vpBounce { from{transform:scale(1)} to{transform:scale(1.12)} }
.vp-text { font-size:17px; font-weight:600; margin:var(--space-2) 0; }
.vp-spinner { width:44px; height:44px; border:3px solid var(--border); border-top-color:var(--accent); border-radius:50%; animation:vpSpin 0.8s linear infinite; margin:0 auto var(--space-4); }
@keyframes vpSpin { to{transform:rotate(360deg)} }
.vp-btn { padding:10px 28px; border:none; border-radius:var(--radius-full); font-size:15px; font-weight:600; font-family:var(--font-sans); cursor:pointer; transition:all var(--transition); }
.vp-btn-stop { background:var(--danger); color:white; }
.vp-btn-stop:hover { background:var(--danger-hover); }
.vp-btn-primary { background:var(--accent); color:white; }
.vp-btn-primary:hover { background:var(--accent-hover); }
.vp-btn-ghost { background:transparent; color:var(--text-secondary); }
.vp-btn-ghost:hover { background:var(--bg-hover); }
.vp-result-label { font-size:11px; color:var(--text-tertiary); text-transform:uppercase; letter-spacing:0.5px; margin-bottom:6px; text-align:left; }
.vp-result-text { font-size:17px; font-weight:500; padding:12px 16px; background:var(--bg-primary); border-radius:var(--radius-md); margin-bottom:var(--space-4); text-align:left; color:var(--text-primary); }
.vp-event-card { background:var(--accent-soft); border-radius:var(--radius-md); padding:14px; margin-bottom:var(--space-4); text-align:left; }
.vp-event-title { font-size:16px; font-weight:600; margin-bottom:6px; }
.vp-event-row { font-size:13px; color:var(--text-secondary); margin:2px 0; }
.vp-actions { display:flex; gap:var(--space-2); justify-content:center; margin-top:var(--space-2); }
.vp-enter-active,.vp-leave-active { transition:all 200ms ease; }
.vp-enter-from,.vp-leave-to { opacity:0; }
.vp-enter-from .vp-card,.vp-leave-to .vp-card { transform:scale(0.95) translateY(8px); }
</style>