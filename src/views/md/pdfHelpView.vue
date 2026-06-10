<template>
  <div class="page-full-row bg-page text-body">
    <!-- Sidebar — PDF list -->
    <aside class="pdf-sidebar">
      <div class="pdf-sidebar__header">
        <div class="text-16px font-700 tracking-[0.2px] text-left">文档</div>
        <div class="text-11px text-dim-3 mt-4px text-left">双击在新标签页中打开</div>
      </div>
      <div class="pdf-list md-scroll">
        <div
          v-for="pdf in pdfList"
          :key="pdf.name"
          class="pdf-list__item"
          :class="{ 'pdf-list__item--active': pdf.name === activeName }"
          @dblclick="openPdf(pdf)"
        >
          <span class="pdf-list__icon">📄</span>
          <div class="pdf-list__info" @click="activeName = pdf.name">
            <div class="pdf-list__name">{{ pdf.label }}</div>
            <div class="pdf-list__size">{{ pdf.size }}</div>
          </div>
          <a
            class="pdf-list__dl"
            :href="pdf.url"
            download
            title="下载"
            @click.stop
          >⬇</a>
        </div>
        <div v-if="pdfList.length === 0" class="pdf-list__empty">
          暂无文档
        </div>
      </div>
    </aside>

    <!-- Main — info area -->
    <main class="pdf-main">
      <div class="pdf-placeholder">
        <div class="pdf-placeholder__inner">
          <div class="pdf-placeholder__icon">📄</div>
          <div class="pdf-placeholder__title">PDF 手册</div>
          <div class="pdf-placeholder__hint">双击左侧文档在新标签页中查看</div>
          <div class="pdf-placeholder__hint">点击 ⬇ 图标下载文件</div>
        </div>
      </div>
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

const pdfList = computed<PdfItem[]>(() =>
  PUBLIC_PDFS.map(name => ({
    name,
    label: niceLabel(name),
    url: encodeURI(`/${name}`),
    size: '',
  })),
)

const activeName = ref('')

function openPdf(pdf: PdfItem): void {
  activeName.value = pdf.name
  window.open(pdf.url, '_blank')
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
.pdf-list__empty {
  padding: 24px 12px;
  text-align: center;
  color: rgba(230, 232, 239, 0.45);
  font-size: 13px;
}
.pdf-list__item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 10px 12px;
  border-radius: 10px;
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
  user-select: none;
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
  user-select: none;
}
.pdf-list__size {
  font-size: 11px;
  color: rgba(230, 232, 239, 0.45);
  margin-top: 2px;
}
.pdf-list__dl {
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  border-radius: 6px;
  font-size: 14px;
  color: rgba(240, 192, 64, 0.7);
  text-decoration: none;
  transition: all 0.15s;
  opacity: 0;
}
.pdf-list__item:hover .pdf-list__dl {
  opacity: 1;
}
.pdf-list__dl:hover {
  background: rgba(240, 192, 64, 0.12);
  color: #f0c040;
}

/* ---- Main ---- */
.pdf-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

/* Placeholder */
.pdf-placeholder {
  height: 100%;
  display: grid;
  place-items: center;
  background: rgba(0, 0, 0, 0.18);
}
.pdf-placeholder__inner {
  text-align: center;
  user-select: none;
}
.pdf-placeholder__icon {
  font-size: 48px;
  margin-bottom: 12px;
  opacity: 0.5;
}
.pdf-placeholder__title {
  font-size: 18px;
  font-weight: 700;
  margin-bottom: 16px;
  color: rgba(230, 232, 239, 0.7);
}
.pdf-placeholder__hint {
  font-size: 13px;
  color: rgba(230, 232, 239, 0.4);
  line-height: 1.7;
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
