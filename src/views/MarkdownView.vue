<script setup lang="ts">
import { ref } from 'vue'
import MarkdownTree from '@/components/markdown/MarkdownTree.vue'
import MarkdownViewer from '@/components/markdown/MarkdownViewer.vue'

const selectedMarkdown = ref('')
</script>

<template>
  <div class="markdown-layout">
    <!-- prettier-ignore -->
    <MarkdownTree
      v-model="selectedMarkdown"
      class="markdown-tree"
    />
    <main class="markdown-document">
      <MarkdownViewer :source="selectedMarkdown" />
    </main>
  </div>
</template>

<style scoped>
.markdown-layout {
  display: grid;
  grid-template-columns: minmax(14rem, 17rem) minmax(0, 1fr);
  align-items: start;
  gap: 1.5rem;
  width: min(100%, 78rem);
  margin-inline: auto;
}

.markdown-tree {
  position: sticky;
  top: 0;
}

.markdown-document {
  min-width: 0;
}

@media (max-width: 767px) {
  .markdown-layout {
    grid-template-columns: minmax(0, 1fr);
  }

  .markdown-tree {
    position: static;
  }
}
</style>
