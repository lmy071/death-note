<template>
  <div class="page-full-row bg-page text-body">
    <!-- Sidebar -->
    <aside class="w-[340px] min-w-[280px] max-w-[420px] border-r border-card bg-sidebar flex flex-col">
      <div class="pt-16px px-14px pb-12px grid gap-10px">
        <div class="text-16px font-700 tracking-[0.2px] text-left">LeetCode 题解</div>
        <input
          v-model.trim="query"
          class="input-search"
          type="search"
          placeholder="搜索文件名…"
        />
      </div>

      <div class="lc-scroll p-6px overflow-auto" role="list">
        <button
          v-for="item in filteredItems"
          :key="item.key"
          class="list-item"
          :class="{ 'list-item-active': item.key === activeKey }"
          type="button"
          @click="select(item.key)"
        >
          <div class="text-13px font-650 leading-[1.2] truncate" :title="item.name">{{ item.name }}</div>
          <div class="text-12px text-dim-3">
            <span>{{ item.lines }} 行</span>
            <span class="mx-6px">·</span>
            <span>{{ formatBytes(item.bytes) }}</span>
          </div>
        </button>

        <div v-if="filteredItems.length === 0" class="p-[18px_12px] text-dim-3">
          没有匹配的文件
        </div>
      </div>
    </aside>

    <!-- Main -->
    <main class="lc-main">
      <div class="lc-main__header">
        <div class="lc-main__title">
          <div class="lc-main__filenameRow">
            <div class="lc-main__filename">{{ activeItem?.name ?? '未选择文件' }}</div>
            <span v-if="activeItem" class="badge" title="预览高亮固定为 JavaScript">JavaScript</span>
          </div>
          <div class="lc-main__subtitle" v-if="activeItem">{{ activeItem.path }}</div>
        </div>

        <div class="lc-actions">
          <button class="btn btn-hover" type="button" :disabled="!activeCode" @click="copyActive()">复制代码</button>
        </div>
      </div>

      <div class="lc-codeWrap">
        <pre v-if="activeCode" class="lc-pre"><code class="hljs lc-pre__code" v-html="highlightedHtml" /></pre>
        <div class="lc-placeholder" v-else>从左侧选择一个文件查看源码</div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import hljs from 'highlight.js/lib/core'
import javascript from 'highlight.js/lib/languages/javascript'
import 'highlight.js/styles/github-dark.css'

hljs.registerLanguage('javascript', javascript)

interface LeetCodeItem {
  key: string
  name: string
  path: string
  order: number
  bytes: number
  lines: number
  code: string
}

const rawGlob = import.meta.glob<{ default: string }>('../../leetCode/*.js', { query: '?raw', eager: true })
const rawModules: Record<string, string> = Object.fromEntries(
  Object.entries(rawGlob).map(([k, mod]) => [k, mod.default])
)

function baseName(p: string): string {
  const idx = p.lastIndexOf('/')
  return idx >= 0 ? p.slice(idx + 1) : p
}

function extractLeadingNumber(name: string): number {
  const m = String(name).match(/^\s*(\d+)\s*\./)
  return m ? Number(m[1]) : Number.POSITIVE_INFINITY
}

function toBytes(s: string): number { return String(s).length }
function countLines(s: string | undefined): number {
  const str = String(s ?? '')
  if (!str) return 0
  return str.endsWith('\n') ? str.split('\n').length - 1 : str.split('\n').length
}

const items = computed<LeetCodeItem[]>(() => {
  const list = Object.entries(rawModules).map(([key, code]) => {
    const name = baseName(key)
    const text = String(code ?? '')
    return {
      key, name,
      path: `src/leetCode/${name}`,
      order: extractLeadingNumber(name),
      bytes: toBytes(text),
      lines: countLines(text),
      code: text,
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

const filteredItems = computed<LeetCodeItem[]>(() => {
  const q = query.value.toLowerCase()
  if (!q) return items.value
  return items.value.filter((x) => x.name.toLowerCase().includes(q))
})

const activeItem = computed<LeetCodeItem | undefined>(() => items.value.find((x) => x.key === activeKey.value))
const activeCode = computed<string>(() => activeItem.value?.code ?? '')

const highlightedHtml = computed<string>(() => {
  const code = activeCode.value
  if (!code) return ''
  try {
    return hljs.highlight(code, { language: 'javascript', ignoreIllegals: true }).value
  } catch {
    return code.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  }
})

function select(key: string): void { activeKey.value = key }

function formatBytes(bytes: number): string {
  const b = Number(bytes || 0)
  if (b < 1024) return `${b} B`
  const kb = b / 1024
  if (kb < 1024) return `${kb.toFixed(1)} KB`
  return `${(kb / 1024).toFixed(1)} MB`
}

async function copyActive(): Promise<void> {
  const text = activeCode.value
  if (!text) return
  try { await navigator.clipboard.writeText(text) } catch {
    const ta = document.createElement('textarea')
    ta.value = text; ta.style.position = 'fixed'; ta.style.left = '-9999px'
    document.body.appendChild(ta); ta.focus(); ta.select()
    document.execCommand('copy'); document.body.removeChild(ta)
  }
}
</script>

<style scoped>
.lc-scroll { padding: 6px; overflow: auto; }
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
.lc-main__title { min-width: 0; text-align: left; }
.lc-main__filenameRow { display: flex; align-items: center; gap: 10px; min-width: 0; }
.lc-main__filename {
  font-weight: 750;
  font-size: 14px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  min-width: 0;
  flex: 1;
}
.lc-main__subtitle {
  margin-top: 2px;
  font-size: 12px;
  color: rgba(230, 232, 239, 0.65);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.lc-actions { display: flex; gap: 10px; }
.lc-codeWrap {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 14px 16px 18px;
}
.lc-pre {
  margin: 0;
  padding: 14px;
  border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(0, 0, 0, 0.35);
  overflow: auto;
  line-height: 1.55;
  font-size: 12px;
  text-align: left;
  tab-size: 2;
  white-space: pre;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
}
.lc-pre__code { display: block; }
.lc-pre :deep(.hljs) { background: transparent !important; padding: 0; }
.lc-placeholder {
  height: 100%;
  display: grid;
  place-items: center;
  color: rgba(230, 232, 239, 0.65);
  border: 1px dashed rgba(255, 255, 255, 0.16);
  border-radius: 14px;
  background: rgba(0, 0, 0, 0.18);
}
/* ---- scrollbar ---- */
.lc-scroll, .lc-codeWrap, .lc-pre {
  scrollbar-width: thin;
  scrollbar-color: rgba(130, 177, 255, 0.5) rgba(255, 255, 255, 0.06);
}
.lc-scroll::-webkit-scrollbar, .lc-codeWrap::-webkit-scrollbar, .lc-pre::-webkit-scrollbar { width: 9px; height: 9px; }
.lc-scroll::-webkit-scrollbar-track, .lc-codeWrap::-webkit-scrollbar-track, .lc-pre::-webkit-scrollbar-track { background: rgba(0, 0, 0, 0.2); border-radius: 999px; }
.lc-scroll::-webkit-scrollbar-thumb, .lc-codeWrap::-webkit-scrollbar-thumb, .lc-pre::-webkit-scrollbar-thumb {
  border-radius: 999px; border: 2px solid transparent; background-clip: content-box;
  background-color: rgba(130, 177, 255, 0.38);
}
.lc-scroll::-webkit-scrollbar-thumb:hover, .lc-codeWrap::-webkit-scrollbar-thumb:hover, .lc-pre::-webkit-scrollbar-thumb:hover { background-color: rgba(130, 177, 255, 0.58); }
.lc-scroll::-webkit-scrollbar-corner, .lc-codeWrap::-webkit-scrollbar-corner, .lc-pre::-webkit-scrollbar-corner { background: transparent; }
</style>
