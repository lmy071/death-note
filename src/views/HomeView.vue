<template>
  <div class="home">
    <header class="home-header">
      <h1 class="home-title">Death Note</h1>
      <p class="home-subtitle">LeetCode 题解 · 共 {{ items.length }} 题</p>
      <input
        v-model.trim="query"
        class="home-search"
        type="search"
        placeholder="搜索题目…"
      />
    </header>

    <main class="waterfall">
      <div
        v-for="item in filteredItems"
        :key="item.key"
        class="waterfall-card"
        @click="goDetail()"
      >
        <div class="card-head">
          <span class="card-num">{{ item.order }}</span>
          <h3 class="card-name" :title="item.name">{{ item.name }}</h3>
        </div>
        <pre class="card-code"><code>{{ item.preview }}</code></pre>
        <div class="card-meta">
          <span>{{ item.lines }} 行</span>
          <span class="meta-dot">·</span>
          <span>{{ formatBytes(item.bytes) }}</span>
          <span class="meta-dot">·</span>
          <span class="card-link">查看 →</span>
        </div>
      </div>
    </main>

    <div v-if="filteredItems.length === 0 && query" class="home-empty">
      没有匹配的题目
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

/* ---- 数据采集：glob src/leetCode/*.js ---- */
const rawGlob = import.meta.glob('../leetCode/*.js', { query: '?raw', eager: true })
const rawModules = Object.fromEntries(
  Object.entries(rawGlob).map(([k, mod]) => [k, mod.default])
)

function baseName(p) {
  const idx = p.lastIndexOf('/')
  return idx >= 0 ? p.slice(idx + 1) : p
}

function extractNumber(name) {
  const m = String(name).match(/^\s*(\d+)\s*[\.\s]/)
  return m ? Number(m[1]) : Number.POSITIVE_INFINITY
}

function countLines(s) {
  const str = String(s ?? '')
  if (!str) return 0
  return str.endsWith('\n') ? str.split('\n').length - 1 : str.split('\n').length
}

function toBytes(s) {
  return String(s).length
}

function takePreview(code, maxLines = 6) {
  const lines = String(code ?? '').split('\n')
  const taken = lines.slice(0, maxLines).join('\n')
  return lines.length > maxLines ? taken + '\n…' : taken
}

const items = computed(() => {
  const list = Object.entries(rawModules).map(([key, code]) => {
    const name = baseName(key)
    const text = String(code ?? '')
    return {
      key,
      name,
      order: extractNumber(name),
      bytes: toBytes(text),
      lines: countLines(text),
      preview: takePreview(text),
      code: text
    }
  })
  list.sort((a, b) => {
    if (a.order !== b.order) return a.order - b.order
    return a.name.localeCompare(b.name, 'zh-Hans-CN-u-co-pinyin')
  })
  return list
})

const query = ref('')
const filteredItems = computed(() => {
  const q = query.value.toLowerCase()
  if (!q) return items.value
  return items.value.filter(x => x.name.toLowerCase().includes(q))
})

function formatBytes(bytes) {
  const b = Number(bytes || 0)
  if (b < 1024) return `${b} B`
  const kb = b / 1024
  if (kb < 1024) return `${kb.toFixed(1)} KB`
  return `${(kb / 1024).toFixed(1)} MB`
}

function goDetail() {
  router.push('/code/leet-code')
}
</script>

<style scoped>
.home {
  min-height: 100vh;
  width: 100vw;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40px 20px 60px;
  box-sizing: border-box;
  background: radial-gradient(circle at top, #151b2f 0, #050816 55%, #02010a 100%);
}

/* ---- Header ---- */
.home-header {
  text-align: center;
  margin-bottom: 32px;
  max-width: 480px;
  width: 100%;
}
.home-title {
  font-size: 32px;
  font-weight: 800;
  color: #e6e8ef;
  margin: 0 0 8px;
}
.home-subtitle {
  font-size: 14px;
  color: rgba(230, 232, 239, 0.75);
  margin: 0 0 16px;
}
.home-search {
  width: 100%;
  height: 36px;
  padding: 0 12px;
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(0, 0, 0, 0.25);
  color: #e6e8ef;
  outline: none;
}
.home-search::placeholder {
  color: rgba(230, 232, 239, 0.55);
}
.home-search:focus {
  border-color: rgba(130, 177, 255, 0.55);
  box-shadow: 0 0 0 3px rgba(130, 177, 255, 0.14);
}

/* ---- Waterfall ---- */
.waterfall {
  column-count: 4;
  column-gap: 16px;
  max-width: 1400px;
  width: 100%;
  padding: 0;
}

@media (max-width: 1200px) {
  .waterfall { column-count: 3; }
}
@media (max-width: 860px) {
  .waterfall { column-count: 2; }
}
@media (max-width: 500px) {
  .waterfall { column-count: 1; }
}

/* ---- Card ---- */
.waterfall-card {
  break-inside: avoid;
  margin-bottom: 16px;
  padding: 16px;
  border-radius: 14px;
  background: rgba(10, 16, 32, 0.95);
  border: 1px solid rgba(255, 255, 255, 0.08);
  cursor: pointer;
  transition: transform 0.18s ease-out,
              box-shadow 0.18s ease-out,
              border-color 0.18s ease-out,
              background 0.18s ease-out;
}
.waterfall-card:hover {
  transform: translateY(-3px) translateZ(0);
  background: rgba(18, 28, 60, 0.98);
  border-color: rgba(130, 177, 255, 0.6);
  box-shadow: 0 16px 35px rgba(2, 8, 38, 0.8);
}

/* Card head */
.card-head {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 10px;
}
.card-num {
  flex-shrink: 0;
  min-width: 28px;
  height: 22px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.3px;
  padding: 0 6px;
  border-radius: 6px;
  background: rgba(130, 177, 255, 0.15);
  color: rgba(200, 218, 255, 0.95);
  border: 1px solid rgba(130, 177, 255, 0.25);
}
.card-name {
  font-size: 13px;
  font-weight: 650;
  line-height: 1.35;
  color: #e6e8ef;
  margin: 0;
  word-break: break-all;
}

/* Code preview */
.card-code {
  margin: 0 0 10px;
  padding: 10px;
  border-radius: 10px;
  background: rgba(0, 0, 0, 0.35);
  border: 1px solid rgba(255, 255, 255, 0.06);
  overflow: hidden;
  text-align: left;
}
.card-code code {
  display: block;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas,
    'Liberation Mono', 'Courier New', monospace;
  font-size: 11.5px;
  line-height: 1.5;
  color: rgba(230, 232, 239, 0.72);
  white-space: pre;
  overflow: hidden;
}

/* Card meta */
.card-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: rgba(230, 232, 239, 0.6);
}
.meta-dot {
  color: rgba(255, 255, 255, 0.2);
}
.card-link {
  margin-left: auto;
  color: rgba(130, 177, 255, 0.85);
  font-weight: 600;
  transition: color 0.15s;
}
.waterfall-card:hover .card-link {
  color: rgba(160, 200, 255, 1);
}

/* Empty */
.home-empty {
  margin-top: 40px;
  color: rgba(230, 232, 239, 0.6);
  font-size: 14px;
}
</style>
