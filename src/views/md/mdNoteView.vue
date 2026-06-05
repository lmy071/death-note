<template>
  <div class="page-full-row bg-page text-body">
    <!-- Sidebar -->
    <aside class="md-sidebar">
      <div class="md-sidebar__header">
        <div class="text-16px font-700 tracking-[0.2px] text-left">笔记</div>
        <input
          v-model.trim="query"
          class="input-search"
          type="search"
          placeholder="搜索笔记…"
        />
      </div>

      <div class="md-tree md-scroll">
        <template v-for="group in filteredTree" :key="group.name">
          <div class="md-tree__group" @click="toggleGroup(group.name)">
            <span class="md-tree__arrow" :class="{ 'md-tree__arrow--open': openGroups.has(group.name) }">▶</span>
            <span class="md-tree__folder">📁</span>
            <span class="md-tree__group-name">{{ group.name }}</span>
            <span class="md-tree__count">{{ group.children.length }}</span>
          </div>
          <div v-show="openGroups.has(group.name)" class="md-tree__children">
            <button
              v-for="item in group.children"
              :key="item.key"
              class="list-item md-tree__item"
              :class="{ 'list-item-active': item.key === activeKey }"
              type="button"
              @click.stop="select(item.key)"
            >
              <div class="text-13px font-650 leading-[1.2] truncate" :title="item.name">{{ item.name }}</div>
              <div class="text-12px text-dim-3">{{ formatBytes(item.bytes) }}</div>
            </button>
          </div>
        </template>
        <div v-if="filteredTree.length === 0" class="p-[18px_12px] text-dim-3">
          没有匹配的笔记
        </div>
      </div>
    </aside>

    <!-- Main -->
    <main class="md-main">
      <div class="md-main__header">
        <div class="md-main__title">
          <div class="md-main__filenameRow">
            <div class="md-main__filename">{{ activeItem?.name ?? '未选择笔记' }}</div>
            <span v-if="activeItem" class="badge">{{ activeItem.group }}</span>
          </div>
          <div class="md-main__subtitle" v-if="activeItem">{{ activeItem.path }}</div>
        </div>
      </div>

      <div class="md-content-wrap md-scroll">
        <article v-if="renderedHtml" class="md-article" v-html="renderedHtml" />
        <div class="md-placeholder" v-else>从左侧选择一篇笔记查看内容</div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { Marked } from 'marked'
import { markedHighlight } from 'marked-highlight'
import hljs from 'highlight.js/lib/core'
import javascript from 'highlight.js/lib/languages/javascript'
import html from 'highlight.js/lib/languages/xml'
import css from 'highlight.js/lib/languages/css'
import json from 'highlight.js/lib/languages/json'
import 'highlight.js/styles/github-dark.css'

hljs.registerLanguage('javascript', javascript)
hljs.registerLanguage('js', javascript)
hljs.registerLanguage('html', html)
hljs.registerLanguage('xml', html)
hljs.registerLanguage('vue', html)
hljs.registerLanguage('css', css)
hljs.registerLanguage('json', json)

const marked = new Marked(
  markedHighlight({
    langPrefix: 'hljs language-',
    highlight(code, lang) {
      if (lang && hljs.getLanguage(lang)) {
        try { return hljs.highlight(code, { language: lang, ignoreIllegals: true }).value } catch {}
      }
      try { return hljs.highlightAuto(code).value } catch {}
      return code.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    }
  })
)

marked.setOptions({ gfm: true, breaks: false })

// ---- Scan md files ----
const rawGlob = import.meta.glob('../../md/**/*.md', { query: '?raw', eager: true })
const rawModules = Object.fromEntries(
  Object.entries(rawGlob).map(([k, mod]) => [k, mod.default])
)

function baseName(p) {
  const idx = p.lastIndexOf('/')
  return idx >= 0 ? p.slice(idx + 1) : p
}

function extractGroup(key) {
  // ../../md/vue3解析/v-model的实现.md → vue3解析
  const parts = key.split('/')
  // find 'md' segment, next is the group
  const mdIdx = parts.indexOf('md')
  if (mdIdx >= 0 && parts[mdIdx + 1]) return parts[mdIdx + 1]
  return '未分类'
}

function toBytes(s) { return new Blob([s]).size }

const items = computed(() => {
  return Object.entries(rawModules).map(([key, code]) => {
    const name = baseName(key).replace(/\.md$/, '')
    const text = String(code ?? '')
    return {
      key, name,
      group: extractGroup(key),
      path: `src/md/${extractGroup(key)}/${name}.md`,
      bytes: toBytes(text),
      code: text,
    }
  })
})

// ---- Tree structure ----
const tree = computed(() => {
  const map = new Map()
  for (const item of items.value) {
    if (!map.has(item.group)) map.set(item.group, [])
    map.get(item.group).push(item)
  }
  return Array.from(map.entries())
    .sort(([a], [b]) => a.localeCompare(b, 'zh-Hans-CN-u-co-pinyin'))
    .map(([name, children]) => ({ name, children }))
})

const query = ref('')
const openGroups = ref(new Set(tree.value.map(g => g.name)))
const activeKey = ref('')

const filteredTree = computed(() => {
  const q = query.value.toLowerCase()
  if (!q) return tree.value
  return tree.value
    .map(g => ({
      ...g,
      children: g.children.filter(x => x.name.toLowerCase().includes(q) || x.group.toLowerCase().includes(q))
    }))
    .filter(g => g.children.length > 0)
})

const activeItem = computed(() => items.value.find(x => x.key === activeKey.value))

const renderedHtml = computed(() => {
  const code = activeItem.value?.code
  if (!code) return ''
  try { return marked.parse(code) } catch { return '' }
})

function toggleGroup(name) {
  const s = new Set(openGroups.value)
  if (s.has(name)) s.delete(name); else s.add(name)
  openGroups.value = s
}

function select(key) { activeKey.value = key }

function formatBytes(bytes) {
  const b = Number(bytes || 0)
  if (b < 1024) return `${b} B`
  const kb = b / 1024
  if (kb < 1024) return `${kb.toFixed(1)} KB`
  return `${(kb / 1024).toFixed(1)} MB`
}
</script>

<style scoped>
/* ---- Sidebar ---- */
.md-sidebar {
  width: 280px;
  min-width: 240px;
  max-width: 380px;
  border-right: 1px solid rgba(255, 255, 255, 0.08);
  background: linear-gradient(to bottom, rgba(255, 255, 255, 0.04), rgba(255, 255, 255, 0.02));
  display: flex;
  flex-direction: column;
}
.md-sidebar__header {
  padding: 16px 14px 12px;
  display: grid;
  gap: 10px;
}

/* ---- Tree ---- */
.md-tree { padding: 6px; overflow: auto; flex: 1; min-height: 0; }
.md-tree__group {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 10px;
  border-radius: 10px;
  cursor: pointer;
  user-select: none;
  font-size: 13px;
  font-weight: 650;
  transition: background 0.15s;
}
.md-tree__group:hover { background: rgba(255, 255, 255, 0.05); }
.md-tree__arrow {
  font-size: 9px;
  color: rgba(230, 232, 239, 0.5);
  transition: transform 0.2s ease;
  width: 12px;
  text-align: center;
}
.md-tree__arrow--open { transform: rotate(90deg); }
.md-tree__folder { font-size: 14px; line-height: 1; }
.md-tree__group-name { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.md-tree__count {
  font-size: 11px;
  color: rgba(230, 232, 239, 0.45);
  background: rgba(255, 255, 255, 0.06);
  padding: 1px 7px;
  border-radius: 999px;
}
.md-tree__children { padding-left: 18px; }
.md-tree__item { padding: 8px 10px; }

/* ---- Main ---- */
.md-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.md-main__header {
  padding: 14px 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(0, 0, 0, 0.15);
}
.md-main__title { min-width: 0; text-align: left; }
.md-main__filenameRow { display: flex; align-items: center; gap: 10px; min-width: 0; }
.md-main__filename {
  font-weight: 750;
  font-size: 14px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  min-width: 0;
  flex: 1;
}
.md-main__subtitle {
  margin-top: 2px;
  font-size: 12px;
  color: rgba(230, 232, 239, 0.65);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ---- Content ---- */
.md-content-wrap {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 24px 32px 40px;
}
.md-article {
  max-width: 820px;
  margin: 0 auto;
  text-align: left;
  font-size: 14px;
  line-height: 1.75;
  color: #e6e8ef;
}

/* Markdown rendered styles */
.md-article :deep(h1) {
  font-size: 26px;
  font-weight: 800;
  margin: 0 0 20px;
  padding-bottom: 10px;
  border-bottom: 2px solid rgba(130, 177, 255, 0.2);
}
.md-article :deep(h2) {
  font-size: 20px;
  font-weight: 700;
  margin: 32px 0 14px;
  padding-bottom: 6px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}
.md-article :deep(h3) {
  font-size: 16px;
  font-weight: 650;
  margin: 24px 0 10px;
}
.md-article :deep(p) { margin: 0 0 14px; }
.md-article :deep(a) {
  color: rgba(130, 177, 255, 0.9);
  text-decoration: none;
  border-bottom: 1px solid rgba(130, 177, 255, 0.3);
  transition: color 0.15s, border-color 0.15s;
}
.md-article :deep(a:hover) { color: rgba(160, 200, 255, 1); border-bottom-color: rgba(160, 200, 255, 0.6); }
.md-article :deep(strong) { color: #fff; font-weight: 650; }
.md-article :deep(code) {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 0.88em;
  padding: 2px 7px;
  border-radius: 6px;
  background: rgba(130, 177, 255, 0.1);
  border: 1px solid rgba(130, 177, 255, 0.15);
  color: rgba(200, 218, 255, 0.95);
}
.md-article :deep(pre) {
  margin: 14px 0;
  padding: 14px 16px;
  border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(0, 0, 0, 0.35);
  overflow: auto;
  line-height: 1.55;
  font-size: 13px;
}
.md-article :deep(pre code) {
  padding: 0;
  border: none;
  background: transparent;
  color: inherit;
  font-size: inherit;
}
.md-article :deep(blockquote) {
  margin: 14px 0;
  padding: 10px 16px;
  border-left: 3px solid rgba(130, 177, 255, 0.4);
  background: rgba(130, 177, 255, 0.06);
  border-radius: 0 10px 10px 0;
  color: rgba(230, 232, 239, 0.85);
}
.md-article :deep(ul), .md-article :deep(ol) { padding-left: 22px; margin: 0 0 14px; }
.md-article :deep(li) { margin: 4px 0; }
.md-article :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 14px 0;
  font-size: 13px;
}
.md-article :deep(th), .md-article :deep(td) {
  padding: 8px 12px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  text-align: left;
}
.md-article :deep(th) {
  background: rgba(130, 177, 255, 0.1);
  font-weight: 650;
}
.md-article :deep(tr:nth-child(even)) { background: rgba(255, 255, 255, 0.02); }
.md-article :deep(hr) {
  border: none;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  margin: 24px 0;
}
.md-article :deep(img) {
  max-width: 100%;
  border-radius: 10px;
  margin: 10px 0;
}

/* Placeholder */
.md-placeholder {
  height: 100%;
  display: grid;
  place-items: center;
  color: rgba(230, 232, 239, 0.65);
  border: 1px dashed rgba(255, 255, 255, 0.16);
  border-radius: 14px;
  background: rgba(0, 0, 0, 0.18);
}

/* ---- Scrollbar ---- */
.md-scroll {
  scrollbar-width: thin;
  scrollbar-color: rgba(130, 177, 255, 0.5) rgba(255, 255, 255, 0.06);
}
.md-scroll::-webkit-scrollbar { width: 9px; height: 9px; }
.md-scroll::-webkit-scrollbar-track { background: rgba(0, 0, 0, 0.2); border-radius: 999px; }
.md-scroll::-webkit-scrollbar-thumb {
  border-radius: 999px;
  border: 2px solid transparent;
  background-clip: content-box;
  background-color: rgba(130, 177, 255, 0.38);
}
.md-scroll::-webkit-scrollbar-thumb:hover { background-color: rgba(130, 177, 255, 0.58); }
.md-scroll::-webkit-scrollbar-corner { background: transparent; }
</style>
