<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import DOMPurify from 'dompurify'
import hljs from 'highlight.js'
import { Marked } from 'marked'
import { markedHighlight } from 'marked-highlight'
import LoadingMask from '@/components/ui/LoadingMask.vue'

import 'highlight.js/styles/github-dark.css'

const props = withDefaults(
  defineProps<{
    source: globalThis.File | string
    emptyText?: string
  }>(),
  {
    emptyText: '暂无 Markdown 内容',
  },
)

const parser = new Marked(
  {
    breaks: true,
    gfm: true,
  },
  markedHighlight({
    emptyLangClass: 'hljs',
    langPrefix: 'hljs language-',
    highlight(code, language) {
      if (language && hljs.getLanguage(language)) {
        return hljs.highlight(code, { language }).value
      }

      return hljs.highlightAuto(code).value
    },
  }),
)

const html = ref('')
const error = ref('')
const loading = ref(false)
let requestId = 0

const hasSource = computed(() =>
  typeof props.source === 'string' ? props.source.trim().length > 0 : true,
)

watch(
  () => props.source,
  async (source) => {
    const currentRequest = ++requestId
    error.value = ''
    html.value = ''

    if (typeof source === 'string' && !source.trim()) return

    loading.value = true

    try {
      let markdown: string

      if (source instanceof globalThis.File) {
        markdown = await source.text()
      } else {
        const response = await globalThis.fetch(source)
        if (!response.ok) {
          throw new Error(`加载失败（HTTP ${response.status}）`)
        }
        markdown = await response.text()
      }

      const rendered = await parser.parse(markdown)
      if (currentRequest === requestId) {
        html.value = DOMPurify.sanitize(rendered)
      }
    } catch (reason) {
      if (currentRequest === requestId) {
        error.value = reason instanceof Error ? reason.message : 'Markdown 文件加载失败'
      }
    } finally {
      if (currentRequest === requestId) loading.value = false
    }
  },
  { immediate: true },
)
</script>

<template>
  <section class="markdown-viewer" aria-live="polite">
    <LoadingMask :visible="loading" text="正在加载 Markdown…" />
    <p v-if="error" class="markdown-state markdown-error" role="alert">
      {{ error }}
    </p>
    <p v-else-if="!hasSource" class="markdown-state">
      {{ emptyText }}
    </p>
    <article v-else class="markdown-body" v-html="html" />
  </section>
</template>

<style scoped>
.markdown-viewer {
  width: min(100%, 920px);
}

.markdown-state {
  margin: 0;
  padding: 2rem;
  color: #9ca3af;
  text-align: center;
}

.markdown-error {
  color: #fca5a5;
}

.markdown-body {
  color: #d7dce5;
  font-size: 1rem;
  line-height: 1.8;
  overflow-wrap: anywhere;
}

.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3),
.markdown-body :deep(h4) {
  margin: 1.6em 0 0.65em;
  color: #f4f6fa;
  line-height: 1.3;
}

.markdown-body :deep(h1) {
  padding-bottom: 0.45em;
  border-bottom: 1px solid #2d3545;
  font-size: 2rem;
}

.markdown-body :deep(h2) {
  font-size: 1.45rem;
}

.markdown-body :deep(p),
.markdown-body :deep(ul),
.markdown-body :deep(ol),
.markdown-body :deep(blockquote) {
  margin: 0.85em 0;
}

.markdown-body :deep(a) {
  color: #82b1ff;
  text-decoration: underline;
  text-underline-offset: 0.2em;
}

.markdown-body :deep(blockquote) {
  padding: 0.2em 1em;
  color: #aeb7c7;
  border-left: 4px solid #52627a;
}

.markdown-body :deep(code:not(.hljs)) {
  padding: 0.15em 0.35em;
  border-radius: 0.3rem;
  background: #202838;
  font-size: 0.9em;
}

.markdown-body :deep(pre) {
  margin: 1.1em 0;
  overflow-x: auto;
  border: 1px solid #30394a;
  border-radius: 0.65rem;
  background: #0d1117;
}

.markdown-body :deep(pre code) {
  padding: 1rem;
  background: transparent;
}

.markdown-body :deep(img) {
  height: auto;
  margin: 1.25rem auto;
  border-radius: 0.5rem;
}

.markdown-body :deep(table) {
  display: block;
  max-width: 100%;
  overflow-x: auto;
  border-collapse: collapse;
}

.markdown-body :deep(th),
.markdown-body :deep(td) {
  padding: 0.55rem 0.75rem;
  border: 1px solid #364052;
}
</style>
