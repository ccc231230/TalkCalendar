<template>
  <div class="sp-root">
    <div class="sp-header">
      <span class="sp-icon">📅</span>
      <span>推荐时段</span>
      <span v-if="loading" class="sp-loading">搜索中...</span>
    </div>
    <div class="sp-list">
      <button
        v-for="(slot, i) in slots"
        :key="i"
        class="sp-card"
        :class="{ top: i === 0 }"
        @click="pick(slot)"
      >
        <div class="sp-card-top">
          <span class="sp-date">{{ slot.date }} {{ dayLabel(slot.day_of_week) }}</span>
          <span class="sp-badge" :class="scoreBadge(slot.score)">{{ Math.round(slot.score) }}分</span>
        </div>
        <div class="sp-time">
          <span class="sp-clock">🕐</span>
          {{ slot.start }} - {{ slot.end }}
        </div>
        <div class="sp-meta">
          <span>⏱ {{ slot.duration_minutes }}分钟</span>
          <span v-if="slot.duration_minutes >= 180">· 大块时间</span>
          <span v-if="isMorning(slot.start)">· 上午</span>
        </div>
      </button>
    </div>
    <div v-if="!loading && slots.length === 0" class="sp-empty">
      未找到符合条件的空闲时段
    </div>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{
  slots: any[]
  loading?: boolean
}>()

const emit = defineEmits<{ select: [slot: any] }>()

const wd = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

function dayLabel(d: number) { return wd[d] || "" }
function isMorning(t: string) { return parseInt(t) < 12 }

function scoreBadge(score: number): string {
  if (score >= 80) return "high"
  if (score >= 60) return "mid"
  return "low"
}

function pick(slot: any) { emit("select", slot) }
</script>

<style scoped>
.sp-root {
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--bg-surface);
  overflow: hidden;
}
.sp-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 14px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  background: var(--bg-primary);
  border-bottom: 1px solid var(--border);
}
.sp-icon { font-size: 14px; }
.sp-loading { margin-left: auto; font-weight: 400; color: var(--text-tertiary); font-size: 12px; }
.sp-list { padding: 8px; display: flex; flex-direction: column; gap: 6px; }
.sp-card {
  display: block;
  width: 100%;
  text-align: left;
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 10px 12px;
  background: var(--bg-primary);
  cursor: pointer;
  font-family: var(--font-sans);
  transition: all 150ms;
  color: var(--text-primary);
}
.sp-card:hover { border-color: var(--accent); box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
.sp-card.top { border-color: var(--accent); background: var(--accent-soft); }
.sp-card-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}
.sp-date { font-size: 13px; font-weight: 600; }
.sp-badge {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 10px;
}
.sp-badge.high { background: #d4edda; color: #155724; }
.sp-badge.mid { background: #fff3cd; color: #856404; }
.sp-badge.low { background: #f8d7da; color: #721c24; }
.sp-time { font-size: 18px; font-weight: 700; color: var(--text-primary); margin: 2px 0; }
.sp-clock { font-size: 16px; }
.sp-meta { font-size: 12px; color: var(--text-tertiary); display: flex; gap: 6px; flex-wrap: wrap; }
.sp-empty { padding: 20px; text-align: center; color: var(--text-tertiary); font-size: 14px; }
</style>
