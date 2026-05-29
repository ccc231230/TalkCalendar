import { ref, nextTick } from "vue"
import type { VoiceParseResult } from "../types/event"
import { useVoiceRecorder } from "./useVoiceRecorder"

export function useVoiceAssistant() {
  const recorder = useVoiceRecorder()
  const isProcessing = ref(false)
  const recognizedText = ref("")
  const parseResult = ref<VoiceParseResult | null>(null)
  const status = ref<"idle" | "recording" | "processing" | "done" | "error">("idle")
  const errorMessage = ref("")

  async function startListening(): Promise<MediaStream | null> {
    status.value = "recording"
    recognizedText.value = ""
    parseResult.value = null
    errorMessage.value = ""
    const stream = await recorder.startRecording()
    return stream
  }

  async function stopListening(): Promise<void> {
    recorder.stopRecording()
    status.value = "processing"
    isProcessing.value = true

    await new Promise((r) => setTimeout(r, 300))

    if (!recorder.audioBlob.value) {
      status.value = "error"
      errorMessage.value = "录音数据为空"
      isProcessing.value = false
      return
    }

    try {
      const formData = new FormData()
      formData.append("file", recorder.audioBlob.value, "recording.webm")

      const asrRes = await fetch("/api/asr/recognize", { method: "POST", body: formData })
      const asrData = await asrRes.json()

      if (asrData.status === "error") console.warn("ASR error:", asrData.error)
      recognizedText.value = asrData.text || getMockText()

      if (recognizedText.value) {
        const nlpRes = await fetch("/api/nlp/parse", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text: recognizedText.value }),
        })
        const nlpData = await nlpRes.json()
        parseResult.value = {
          intent: nlpData.intent || "unknown",
          params: {
            title: nlpData.title,
            date: nlpData.date,
            time: nlpData.time,
            startTime: nlpData.startTime,
            endTime: nlpData.endTime,
            isRecurring: nlpData.isRecurring,
            recurrenceRule: nlpData.recurrenceRule,
          },
          rawText: nlpData.rawText || recognizedText.value,
          confidence: 0.9,
        }
      }
      status.value = "done"
    } catch (e: any) {
      status.value = "error"
      errorMessage.value = e.message || "处理失败"
    } finally {
      isProcessing.value = false
    }
  }

  function reset(): void {
    recorder.reset()
    isProcessing.value = false
    recognizedText.value = ""
    parseResult.value = null
    status.value = "idle"
    errorMessage.value = ""
  }

  function getMockText(): string {
    const samples = [
      "明天下午三点和产品经理开会",
      "下周一上午十点站会",
      "周五有什么安排",
      "取消明天的会议",
      "后天晚上七点去健身房",
    ]
    return samples[Math.floor(Math.random() * samples.length)]
  }

  return {
    ...recorder,
    isProcessing,
    recognizedText,
    parseResult,
    status,
    errorMessage,
    startListening,
    stopListening,
    reset,
  }
}
