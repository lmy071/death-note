<template>
  <div class="page-full-col bg-page text-body">
    <header class="pdf-header">
      <button class="pdf-header__back" @click="goBack" title="返回首页">← 返回</button>
      <h1 class="pdf-header__title">企业级线损管理平台用户帮助手册</h1>
      <a class="pdf-header__download" :href="pdfUrl" download title="下载 PDF">⬇ 下载</a>
    </header>

    <div class="pdf-viewer">
      <iframe
        class="pdf-viewer__frame"
        :src="pdfUrl"
        frameborder="0"
        title="PDF 帮助手册"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()
const pdfUrl = encodeURI('/企业级线损管理平台用户帮助手册v1.0.pdf')

function goBack(): void {
  router.push('/')
}
</script>

<style scoped>
/* ---- Layout ---- */
.page-full-col {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
}

/* ---- Header ---- */
.pdf-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(0, 0, 0, 0.3);
  backdrop-filter: blur(12px);
  flex-shrink: 0;
}
.pdf-header__back {
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.12);
  color: #e6e8ef;
  padding: 6px 14px;
  border-radius: 8px;
  font-size: 13px;
  cursor: pointer;
  transition: background 0.15s;
  white-space: nowrap;
}
.pdf-header__back:hover {
  background: rgba(255, 255, 255, 0.14);
}
.pdf-header__title {
  flex: 1;
  min-width: 0;
  font-size: 15px;
  font-weight: 650;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  text-align: left;
}
.pdf-header__download {
  background: rgba(212, 160, 23, 0.15);
  border: 1px solid rgba(212, 160, 23, 0.3);
  color: #f0c040;
  padding: 6px 14px;
  border-radius: 8px;
  font-size: 13px;
  text-decoration: none;
  cursor: pointer;
  transition: background 0.15s;
  white-space: nowrap;
}
.pdf-header__download:hover {
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
</style>
