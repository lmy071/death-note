<script setup lang="ts">
import ActionMenu from '@/components/ActionMenu.vue'
import MarkdownViewer from '@/components/MarkdownViewer.vue'
</script>

<template>
  <div class="relative h-full w-full overflow-y-auto px-6 py-10 pl-22 sm:pl-28">
    <!-- prettier-ignore -->
    <aside
      class="fixed left-3 top-1/2 z-20 -translate-y-1/2 sm:left-5"
      aria-label="快捷菜单"
    >
      <ActionMenu />
    </aside>

    <!-- prettier-ignore -->
    <MarkdownViewer
      class="mx-auto"
      source="/md/vue3/vue3为什么要使用 value.md"
    />
  </div>
</template>
