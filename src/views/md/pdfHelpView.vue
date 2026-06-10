<template>
  <div class="page-full-row bg-page text-body">
    <!-- Sidebar — PDF list -->
    <aside class="pdf-sidebar">
      <div class="pdf-sidebar__header">
        <div class="text-16px font-700 tracking-[0.2px] text-left">文档</div>
      </div>
      <div class="pdf-list md-scroll">
        <button
          v-for="pdf in pdfList"
          :key="pdf.name"
          class="pdf-list__item"
          :class="{ 'pdf-list__item--active': pdf.name === activeName }"
          type="button"
          @click="selectPdf(pdf)"
        >
          <span class="pdf-list__icon">📄</span>
          <div class="pdf-list__info">
            <div class="pdf-list__name">{{ pdf.label }}</div>
            <div class="pdf-list__size">{{ pdf.size }}</div>
          </div>
        </button>
      </div>
    </aside>

    <!-- Main — PDF viewer -->
    <main class="pdf-main">
      <template v-if="activePdf">
        <div class="pdf-main__header">
          <div class="pdf-main__title">{{ activePdf.label }}</div>
          <a class="pdf-main__download" :href="activePdf.url" download>⬇ 下载</a>
        </div>
        <div class="pdf-viewer">
          <iframe
            class="pdf-viewer__frame"
            :src="activePdf.url"
            frameborder="0"
            title="PDF Viewer"
          />
        </div>
      </template>
      <div v-else class="pdf-placeholder">从左侧选择文档查看</div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

// ---- PDF manifest ----
// Add new PDFs in public/ here to make them visible in the sidebar
const PUBLIC_PDFS = [
  'zonebox开缸教程（人工石，死石，人造滤材篇） 2.pdf',
]

interface PdfItem {
  name: string
  label: string
  url: string
  size: string
}

function niceLabel(raw: string): string {
  return raw
    .replace(/\.pdf$/i, '')
    .replace(/^[\d\s]+/, '')
    .trim()
}

function formatSize(bytes: number): string {
  if (!bytes) return ''
  if (bytes < 1024) return `${bytes} B`
  const kb = bytes / 1024
  if (kb < 1024) return `${kb.toFixed(0)} KB`
  return `${(kb / 1024).toFixed(1)} MB`
}

const pdfList = computed<PdfItem[]>(() =>
  PUBLIC_PDFS.map(name => ({
    name,
    label: niceLabel(name),
    url: encodeURI(`/${name}`),
    size: '',
  })),
)

const activeName = ref('')
const activePdf = computed<PdfItem | undefined>(() =>
  pdfList.value.find(p => p.name === activeName.value),
)

function selectPdf(pdf: PdfItem): void {
  activeName.value = pdf.name
}
</script>

<style scoped>
/* ---- Sidebar ---- */
.pdf-sidebar {
  width: 280px;
  min-width: 240px;
  max-width: 380px;
  border-right: 1px solid rgba(255, 255, 255, 0.08);
  background: linear-gradient(to bottom, rgba(255, 255, 255, 0.04), rgba(255, 255, 255, 0.02));
  display: flex;
  flex-direction: column;
}
.pdf-sidebar__header {
  padding: 16px 14px 12px;
}

/* ---- PDF list ---- */
.pdf-list {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 6px;
}
.pdf-list__item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 10px 12px;
  border-radius: 10px;
  border: none;
  background: transparent;
  color: var(--text);
  cursor: pointer;
  text-align: left;
  font-family: inherit;
  transition: background 0.15s;
}
.pdf-list__item:hover {
  background: rgba(255, 255, 255, 0.05);
}
.pdf-list__item--active {
  background: rgba(130, 177, 255, 0.1);
  border: 1px solid rgba(130, 177, 255, 0.18);
}
.pdf-list__icon {
  font-size: 18px;
  line-height: 1;
  flex-shrink: 0;
}
.pdf-list__info {
  min-width: 0;
  flex: 1;
}
.pdf-list__name {
  font-size: 13px;
  font-weight: 650;
  line-height: 1.25;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.pdf-list__size {
  font-size: 11px;
  color: rgba(230, 232, 239, 0.45);
  margin-top: 2px;
}

/* ---- Main ---- */
.pdf-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.pdf-main__header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 14px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(0, 0, 0, 0.15);
  flex-shrink: 0;
}
.pdf-main__title {
  flex: 1;
  min-width: 0;
  font-size: 14px;
  font-weight: 700;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  text-align: left;
}
.pdf-main__download {
  background: rgba(212, 160, 23, 0.15);
  border: 1px solid rgba(212, 160, 23, 0.3);
  color: #f0c040;
  padding: 6px 14px;
  border-radius: 8px;
  font-size: 13px;
  text-decoration: none;
  cursor: pointer;
  white-space: nowrap;
  transition: background 0.15s;
  flex-shrink: 0;
}
.pdf-main__download:hover {
  background: rgba(212, 160, 23, 0.25);
}

/* ---- Viewer ---- */
.pdf-viewer {
  flex: 1;
  min-height: 0;
  background: rgba(0, 0, 0, 0.2);
}
.pdf-viewer__frame {
  width: 100%;
  height: 100%;
  border: none;
}

/* Placeholder */
.pdf-placeholder {
  height: 100%;
  display: grid;
  place-items: center;
  color: rgba(230, 232, 239, 0.65);
  border: 1px dashed rgba(255, 255, 255, 0.16);
  border-radius: 14px;
  background: rgba(0, 0, 0, 0.18);
}

/* ---- Scrollbar (mirrors md-scroll) ---- */
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
