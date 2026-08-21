<script setup lang="ts">
import { computed, onMounted } from 'vue'
import markdownFiles from 'virtual:markdown-files'
import MarkdownTreeNode from './MarkdownTreeNode.vue'
import { buildMarkdownTree } from './markdown-tree'

const props = defineProps<{
  modelValue: string
}>()

const emit = defineEmits<{
  'update:modelValue': [source: string]
}>()

const tree = computed(() => buildMarkdownTree(markdownFiles))

onMounted(() => {
  if (!props.modelValue && markdownFiles[0]) {
    emit('update:modelValue', markdownFiles[0])
  }
})
</script>

<template>
  <!-- prettier-ignore -->
  <nav
    class="markdown-tree"
    aria-label="Markdown 文档树"
  >
    <div class="markdown-tree__header">
      <div>
        <p class="markdown-tree__eyebrow">
          Documents
        </p>
        <h2 class="markdown-tree__title">
          Markdown
        </h2>
      </div>
      <span
        class="markdown-tree__count"
        :aria-label="`${markdownFiles.length} 个文档`"
      >
        {{ markdownFiles.length }}
      </span>
    </div>

    <ul
      v-if="tree.length"
      class="markdown-tree__list"
    >
      <MarkdownTreeNode
        v-for="node in tree"
        :key="node.id"
        :active-source="modelValue"
        :node="node"
        @select="emit('update:modelValue', $event)"
      />
    </ul>
    <p
      v-else
      class="markdown-tree__empty"
    >
      public/md 中暂无 Markdown 文件
    </p>
  </nav>
</template>

<style scoped>
.markdown-tree {
  width: 100%;
  padding: 1rem;
  border: 1px solid rgb(255 255 255 / 8%);
  border-radius: 1rem;
  background: linear-gradient(180deg, rgb(255 255 255 / 5%), rgb(255 255 255 / 2%));
  box-shadow: 0 18px 45px rgb(0 0 0 / 18%);
}

.markdown-tree__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.25rem 0.35rem 0.85rem;
  border-bottom: 1px solid rgb(255 255 255 / 8%);
}

.markdown-tree__eyebrow,
.markdown-tree__title,
.markdown-tree__empty {
  margin: 0;
}

.markdown-tree__eyebrow {
  color: rgb(230 232 239 / 55%);
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

.markdown-tree__title {
  margin-top: 0.15rem;
  color: #f4f6fa;
  font-size: 1rem;
}

.markdown-tree__count {
  display: grid;
  min-width: 1.75rem;
  height: 1.75rem;
  place-items: center;
  padding-inline: 0.4rem;
  border: 1px solid rgb(192 132 252 / 30%);
  border-radius: 9999px;
  color: #d8b4fe;
  background: rgb(175 64 255 / 10%);
  font-size: 0.75rem;
  font-weight: 700;
}

.markdown-tree__list {
  max-height: calc(100vh - 14rem);
  margin: 0.75rem 0 0;
  padding: 0;
  overflow: auto;
}

.markdown-tree__empty {
  padding: 1.25rem 0.35rem 0.5rem;
  color: rgb(230 232 239 / 58%);
  font-size: 0.85rem;
  line-height: 1.6;
}
</style>
