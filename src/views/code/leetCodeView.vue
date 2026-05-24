<template>
  <div page-full-row bg-page text-body>
    <aside w-340px min-w-280px max-w-420px border-r border-card bg-sidebar flex flex-col>
      <div p-16px_14px_12px grid gap-10px>
        <div text-16px font-700 tracking-[0.2px] text-left>LeetCode 题解</div>
        <input
          v-model.trim="query"
          class="input-search"
          type="search"
          placeholder="搜索文件名…"
        />
      </div>

      <div class="lc-scroll" p-6px overflow-auto role="list">
        <button
          v-for="item in filteredItems"
          :key="item.key"
          class="list-item"
          :class="{ 'list-item-active': item.key === activeKey }"
          type="button"
          @click="select(item.key)"
        >
          <div text-13px font-650 leading-[1.2] truncate :title="item.name">{{ item.name }}</div>
          <div text-12px text-dim-3>
            <span>{{ item.lines }} 行</span>
            <span mx-6px>·</span>
            <span>{{ formatBytes(item.bytes) }}</span>
          </div>
        </button>

        <div v-if="filteredItems.length === 0" p-18px_12px text-dim-3>
          没有匹配的文件
        </div>
      </div>
    </aside>

    <main class="lc-main">
      <div class="lc-main__header">
        <div class="lc-main__title">
          <div class="lc-main__filenameRow">
            <div class="lc-main__filename">{{ activeItem?.name ?? '未选择文件' }}</div>
            <span
              v-if="activeItem"
              class="lc-lang"
              title="预览高亮固定为 JavaScript"
            >JavaScript</span>
          </div>
          <div class="lc-main__subtitle" v-if="activeItem">
            {{ activeItem.path }}
          </div>
        </div>

        <div class="lc-actions">
          <button
            class="lc-btn"
            type="button"
            :disabled="!activeCode"
            @click="copyActive()"
          >
            复制代码
          </button>
        </div>
      </div>

      <div class="lc-codeWrap">
        <pre v-if="activeCode" class="lc-pre"><code class="hljs lc-pre__code" v-html="highlightedHtml"></code></pre>
        <div class="lc-placeholder" v-else>从左侧选择一个文件查看源码</div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import hljs from 'highlight.js/lib/core'
import javascript from 'highlight.js/lib/languages/javascript'
import 'highlight.js/styles/github-dark.css'

hljs.registerLanguage('javascript', javascript)

// Vite 方案：import.meta.glob + ?raw 批量收集 src/leetCode/*.js 源码字符串
const rawGlob = import.meta.glob('../../leetCode/*.js', { query: '?raw', eager: true })
const rawModules = Object.fromEntries(
  Object.entries(rawGlob).map(([k, mod]) => [k, mod.default])
)

function baseName(p) {
  const s = String(p)
  const idx = s.lastIndexOf('/')
  return idx >= 0 ? s.slice(idx + 1) : s
}

function extractLeadingNumber(name) {
  // 支持 "1009. xxx.js" / "1.两数之和.js" / "26. 删除....js"
  const m = String(name).match(/^\s*(\d+)\s*\./)
  return m ? Number(m[1]) : Number.POSITIVE_INFINITY
}

function toBytes(s) {
  // 仅用于展示大概大小，UTF-8 多字节会略有误差但可接受
  return String(s).length
}

function countLines(s) {
  const str = String(s ?? '')
  if (!str) return 0
  return str.endsWith('\n') ? str.split('\n').length - 1 : str.split('\n').length
}

const items = computed(() => {
  const list = Object.entries(rawModules).map(([key, code]) => {
    const name = baseName(key)
    const text = String(code ?? '')
    return {
      key,
      path: `src/leetCode/${name}`,
      name,
      order: extractLeadingNumber(name),
      bytes: toBytes(text),
      lines: countLines(text),
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
const activeKey = ref(items.value[0]?.key ?? '')

const filteredItems = computed(() => {
  const q = query.value.toLowerCase()
  if (!q) return items.value
  return items.value.filter((x) => x.name.toLowerCase().includes(q))
})

const activeItem = computed(() => items.value.find((x) => x.key === activeKey.value))
const activeCode = computed(() => activeItem.value?.code ?? '')

/** 右侧预览固定按 JavaScript 高亮（题解文件均为 .js） */
const highlightedHtml = computed(() => {
  const code = activeCode.value
  if (!code) return ''
  return hljs.highlight(code, { language: 'javascript', ignoreIllegals: true }).value
})

function select(key) {
  activeKey.value = key
}

function formatBytes(bytes) {
  const b = Number(bytes || 0)
  if (b < 1024) return `${b} B`
  const kb = b / 1024
  if (kb < 1024) return `${kb.toFixed(1)} KB`
  const mb = kb / 1024
  return `${mb.toFixed(1)} MB`
}

async function copyActive() {
  const text = activeCode.value
  if (!text) return
  try {
    await navigator.clipboard.writeText(text)
  } catch {
    // 兼容性兜底（某些环境不支持 clipboard API）
    const ta = document.createElement('textarea')
    ta.value = text
    ta.style.position = 'fixed'
    ta.style.left = '-9999px'
    ta.style.top = '-9999px'
    document.body.appendChild(ta)
    ta.focus()
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
  }
}
</script>

<style scoped>
.lc-page {
  height: 100vh;
  width: 100vw;
  display: flex;
  background: #0b1020;
  color: #e6e8ef;
  overflow: hidden;
}

.lc-sidebar {
  width: 340px;
  min-width: 280px;
  max-width: 420px;
  border-right: 1px solid rgba(255, 255, 255, 0.08);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.04), rgba(255, 255, 255, 0.02));
  display: flex;
  flex-direction: column;
}

.lc-sidebar__header {
  padding: 16px 14px 12px;
  display: grid;
  gap: 10px;
}

.lc-title {
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 0.2px;
  text-align: left;
}

.lc-search {
  width: 100%;
  height: 36px;
  padding: 0 12px;
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(0, 0, 0, 0.25);
  color: #e6e8ef;
  outline: none;
}
.lc-search::placeholder {
  color: rgba(230, 232, 239, 0.55);
}
.lc-search:focus {
  border-color: rgba(130, 177, 255, 0.55);
  box-shadow: 0 0 0 3px rgba(130, 177, 255, 0.14);
}

.lc-list {
  padding: 6px;
  overflow: auto;
}

.lc-item {
  width: 100%;
  text-align: left;
  padding: 10px 10px;
  border-radius: 12px;
  border: 1px solid transparent;
  background: transparent;
  color: inherit;
  cursor: pointer;
  display: grid;
  gap: 6px;
}
.lc-item:hover {
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(255, 255, 255, 0.08);
}
.lc-item.is-active {
  background: rgba(130, 177, 255, 0.14);
  border-color: rgba(130, 177, 255, 0.28);
}

.lc-item__name {
  font-size: 13px;
  font-weight: 650;
  line-height: 1.2;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.lc-item__meta {
  font-size: 12px;
  color: rgba(230, 232, 239, 0.7);
}
.lc-dot {
  margin: 0 6px;
}

.lc-empty {
  padding: 18px 12px;
  color: rgba(230, 232, 239, 0.7);
}

.lc-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.lc-main__header {
  padding: 14px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(0, 0, 0, 0.15);
}

.lc-main__title {
  min-width: 0;
  text-align: left;
}

.lc-main__filenameRow {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.lc-main__filename {
  font-weight: 750;
  font-size: 14px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  min-width: 0;
  flex: 1;
}

.lc-lang {
  flex-shrink: 0;
  font-size: 11px;
  font-weight: 650;
  letter-spacing: 0.2px;
  padding: 3px 8px;
  border-radius: 999px;
  border: 1px solid rgba(130, 177, 255, 0.35);
  color: rgba(200, 218, 255, 0.95);
  background: rgba(130, 177, 255, 0.12);
}

.lc-main__subtitle {
  margin-top: 2px;
  font-size: 12px;
  color: rgba(230, 232, 239, 0.65);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.lc-actions {
  display: flex;
  gap: 10px;
}

.lc-btn {
  height: 34px;
  padding: 0 12px;
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  background: rgba(255, 255, 255, 0.06);
  color: #e6e8ef;
  cursor: pointer;
}
.lc-btn:hover:enabled {
  background: rgba(255, 255, 255, 0.09);
}
.lc-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.lc-codeWrap {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 14px 16px 18px;
}

.lc-pre {
  margin: 0;
  padding: 14px 14px;
  border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(0, 0, 0, 0.35);
  overflow: auto;
  line-height: 1.55;
  font-size: 12px;
  text-align: left;
  tab-size: 2;
  white-space: pre;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono',
    'Courier New', monospace;
}

.lc-pre__code {
  display: block;
}

.lc-pre :deep(.hljs) {
  background: transparent !important;
  padding: 0;
}

/* 滚动条：与主题色一致，细轨道 + 圆角滑块 */
.lc-list,
.lc-codeWrap,
.lc-pre {
  scrollbar-width: thin;
  scrollbar-color: rgba(130, 177, 255, 0.5) rgba(255, 255, 255, 0.06);
}

.lc-list::-webkit-scrollbar,
.lc-codeWrap::-webkit-scrollbar,
.lc-pre::-webkit-scrollbar {
  width: 9px;
  height: 9px;
}

.lc-list::-webkit-scrollbar-track,
.lc-codeWrap::-webkit-scrollbar-track,
.lc-pre::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 999px;
}

.lc-list::-webkit-scrollbar-thumb,
.lc-codeWrap::-webkit-scrollbar-thumb,
.lc-pre::-webkit-scrollbar-thumb {
  border-radius: 999px;
  border: 2px solid transparent;
  background-clip: content-box;
  background-color: rgba(130, 177, 255, 0.38);
}

.lc-list::-webkit-scrollbar-thumb:hover,
.lc-codeWrap::-webkit-scrollbar-thumb:hover,
.lc-pre::-webkit-scrollbar-thumb:hover {
  background-color: rgba(130, 177, 255, 0.58);
}

.lc-list::-webkit-scrollbar-corner,
.lc-codeWrap::-webkit-scrollbar-corner,
.lc-pre::-webkit-scrollbar-corner {
  background: transparent;
}

.lc-placeholder {
  height: 100%;
  display: grid;
  place-items: center;
  color: rgba(230, 232, 239, 0.65);
  border: 1px dashed rgba(255, 255, 255, 0.16);
  border-radius: 14px;
  background: rgba(0, 0, 0, 0.18);
}
</style>
