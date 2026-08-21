<script setup lang="ts">
import type { MarkdownTreeNode } from './markdown-tree'

defineProps<{
  activeSource: string
  node: MarkdownTreeNode
}>()

const emit = defineEmits<{
  select: [source: string]
}>()
</script>

<template>
  <!-- prettier-ignore -->
  <li class="tree-node">
    <details
      v-if="node.type === 'directory'"
      class="tree-directory"
      open
    >
      <summary class="tree-directory__label">
        <span
          class="tree-directory__chevron"
          aria-hidden="true"
        >›</span>
        <span
          class="tree-directory__icon"
          aria-hidden="true"
        >▰</span>
        <span>{{ node.name }}</span>
      </summary>
      <ul class="tree-children">
        <MarkdownTreeNode
          v-for="child in node.children"
          :key="child.id"
          :active-source="activeSource"
          :node="child"
          @select="emit('select', $event)"
        />
      </ul>
    </details>

    <button
      v-else
      class="tree-file"
      :class="{ 'tree-file--active': node.source === activeSource }"
      type="button"
      :aria-current="node.source === activeSource ? 'page' : undefined"
      @click="node.source && emit('select', node.source)"
    >
      <span
        class="tree-file__icon"
        aria-hidden="true"
      >#</span>
      <span class="tree-file__name">{{ node.name }}</span>
    </button>
  </li>
</template>

<style scoped>
.tree-node,
.tree-children {
  margin: 0;
  padding: 0;
  list-style: none;
}

.tree-children {
  padding-left: 0.8rem;
}

.tree-directory__label,
.tree-file {
  display: flex;
  width: 100%;
  min-height: 2.25rem;
  align-items: center;
  gap: 0.5rem;
  padding: 0.4rem 0.55rem;
  border: 1px solid transparent;
  border-radius: 0.65rem;
  color: rgb(230 232 239 / 76%);
  font: inherit;
  text-align: left;
}

.tree-directory__label {
  cursor: pointer;
  user-select: none;
}

.tree-directory__label::-webkit-details-marker {
  display: none;
}

.tree-directory__chevron {
  color: #93a4c5;
  transform: rotate(0deg);
  transition: transform 160ms ease;
}

.tree-directory[open] > .tree-directory__label .tree-directory__chevron {
  transform: rotate(90deg);
}

.tree-directory__icon {
  color: #c084fc;
  font-size: 0.72rem;
}

.tree-file {
  background: transparent;
  cursor: pointer;
}

.tree-file:hover {
  color: #f4f6fa;
  border-color: rgb(255 255 255 / 8%);
  background: rgb(255 255 255 / 5%);
}

.tree-file--active {
  color: #fff;
  border-color: rgb(130 177 255 / 32%);
  background: rgb(130 177 255 / 14%);
}

.tree-file:focus-visible,
.tree-directory__label:focus-visible {
  outline: 2px solid #82b1ff;
  outline-offset: 2px;
}

.tree-file__icon {
  flex: 0 0 auto;
  color: #82b1ff;
  font-family: ui-monospace, monospace;
  font-weight: 700;
}

.tree-file__name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (prefers-reduced-motion: reduce) {
  .tree-directory__chevron {
    transition: none;
  }
}
</style>
