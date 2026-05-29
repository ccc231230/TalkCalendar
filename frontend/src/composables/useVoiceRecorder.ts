import { ref } from "vue"

export function useVoiceRecorder() {
  const isRecording = ref(false)
  const audioBlob = ref<Blob | null>(null)
  const error = ref<string | null>(null)
  const mediaStream = ref<MediaStream | null>(null)
  const recordingSeconds = ref(0)

  let audioContext: AudioContext | null = null
  let scriptNode: ScriptProcessorNode | null = null
  let source: MediaStreamAudioSourceNode | null = null
  let samples: Float32Array[] = []
  let timer: ReturnType<typeof setInterval> | null = null
  let sampleRate = 16000

  async function startRecording(): Promise<MediaStream | null> {
    error.value = null
    recordingSeconds.value = 0
    samples = []
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      mediaStream.value = stream
      sampleRate = 16000

      audioContext = new AudioContext({ sampleRate })
      source = audioContext.createMediaStreamSource(stream)

      // Downsample to 16kHz if needed
      scriptNode = audioContext.createScriptProcessor(4096, 1, 1)
      scriptNode.onaudioprocess = (e) => {
        if (!isRecording.value) return
        const input = e.inputBuffer.getChannelData(0)
        samples.push(new Float32Array(input))
      }

      source.connect(scriptNode)
      scriptNode.connect(audioContext.destination)

      isRecording.value = true
      timer = setInterval(() => { recordingSeconds.value++ }, 1000)
      return stream
    } catch (e: any) {
      error.value = "麦克风访问失败: " + (e.message || "")
      return null
    }
  }

  function stopRecording(): Blob | null {
    isRecording.value = false
    if (timer) { clearInterval(timer); timer = null }

    // Disconnect audio nodes
    if (scriptNode) { scriptNode.disconnect(); scriptNode = null }
    if (source) { source.disconnect(); source = null }
    if (audioContext) { audioContext.close(); audioContext = null }
    if (mediaStream.value) {
      mediaStream.value.getTracks().forEach((t) => t.stop())
      mediaStream.value = null
    }

    // Convert samples to WAV
    if (samples.length === 0) return null

    const wav = encodeWAV(samples, sampleRate)
    audioBlob.value = wav
    return wav
  }

  function reset(): void {
    if (timer) { clearInterval(timer); timer = null }
    if (scriptNode) { scriptNode.disconnect(); scriptNode = null }
    if (source) { source.disconnect(); source = null }
    if (audioContext) { audioContext.close(); audioContext = null }
    if (mediaStream.value) {
      mediaStream.value.getTracks().forEach((t) => t.stop())
      mediaStream.value = null
    }
    audioBlob.value = null
    error.value = null
    recordingSeconds.value = 0
    samples = []
  }

  return {
    isRecording,
    audioBlob,
    error,
    mediaStream,
    recordingSeconds,
    startRecording,
    stopRecording,
    reset,
  }
}

function encodeWAV(chunks: Float32Array[], sampleRate: number): Blob {
  // Flatten all chunks
  let totalLen = 0
  for (const c of chunks) totalLen += c.length
  const merged = new Float32Array(totalLen)
  let offset = 0
  for (const c of chunks) {
    merged.set(c, offset)
    offset += c.length
  }

  // Convert to 16-bit PCM
  const pcm = new Int16Array(merged.length)
  for (let i = 0; i < merged.length; i++) {
    const s = Math.max(-1, Math.min(1, merged[i]))
    pcm[i] = s < 0 ? s * 0x8000 : s * 0x7FFF
  }

  // WAV header
  const dataLen = pcm.length * 2
  const buffer = new ArrayBuffer(44 + dataLen)
  const view = new DataView(buffer)

  function writeStr(off: number, str: string) {
    for (let i = 0; i < str.length; i++) view.setUint8(off + i, str.charCodeAt(i))
  }

  writeStr(0, "RIFF")
  view.setUint32(4, 36 + dataLen, true)
  writeStr(8, "WAVE")
  writeStr(12, "fmt ")
  view.setUint32(16, 16, true)       // chunk size
  view.setUint16(20, 1, true)        // PCM
  view.setUint16(22, 1, true)        // mono
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate * 2, true) // byte rate
  view.setUint16(32, 2, true)        // block align
  view.setUint16(34, 16, true)       // bits per sample
  writeStr(36, "data")
  view.setUint32(40, dataLen, true)

  // Write PCM data
  const pcmView = new Int16Array(buffer, 44)
  pcmView.set(pcm)

  return new Blob([buffer], { type: "audio/wav" })
}
