<script setup lang="ts">
import ActionMenu from '@/components/ActionMenu.vue'
import type { ActionMenuItem } from '@/components/action-menu'
import MarkdownViewer from '@/components/MarkdownViewer.vue'

const actionMenuItems = [
  {
    icon: {
      paths: ['M4 4l11.733 16h4.267l-11.733 -16z', 'M4 20l6.768 -6.768m2.46 -2.46l6.772 -6.772'],
    },
    name: 'X',
    url: 'https://x.com',
  },
  {
    icon: {
      paths: [
        'M9 19c-4.3 1.4 -4.3 -2.5 -6 -3m12 5v-3.5c0 -1 .1 -1.4 -.5 -2c2.8 -.3 5.5 -1.4 5.5 -6a4.6 4.6 0 0 0 -1.3 -3.2a4.2 4.2 0 0 0 -.1 -3.2s-1.1 -.3 -3.5 1.3a12.3 12.3 0 0 0 -6.2 0c-2.4 -1.6 -3.5 -1.3 -3.5 -1.3a4.2 4.2 0 0 0 -.1 3.2a4.6 4.6 0 0 0 -1.3 3.2c0 4.6 2.7 5.7 5.5 6c-.6 .6 -.6 1.2 -.5 2v3.5',
      ],
    },
    name: 'GitHub',
    url: 'https://github.com/lmy071/death-note',
  },
  {
    icon: {
      paths: [
        'M8 12a1 1 0 1 0 2 0a1 1 0 0 0 -2 0',
        'M14 12a1 1 0 1 0 2 0a1 1 0 0 0 -2 0',
        'M15.5 17c0 1 1.5 3 2 3c1.5 0 2.833 -1.667 3.5 -3c.667 -1.667 .5 -5.833 -1.5 -11.5c-1.457 -1.015 -3 -1.34 -4.5 -1.5l-.972 1.923a11.913 11.913 0 0 0 -4.053 0l-.975 -1.923c-1.5 .16 -3.043 .485 -4.5 1.5c-2 5.667 -2.167 9.833 -1.5 11.5c.667 1.333 2 3 3.5 3c.5 0 2 -2 2 -3',
        'M7 16.5c3.5 1 6.5 1 10 0',
      ],
    },
    name: 'Discord',
    url: 'https://discord.com',
  },
] satisfies ActionMenuItem[]
</script>

<template>
  <div class="relative h-full w-full overflow-y-auto px-6 py-10 pl-22 sm:pl-28">
    <!-- prettier-ignore -->
    <aside
      class="fixed left-3 top-1/2 z-20 -translate-y-1/2 sm:left-5"
      aria-label="快捷菜单"
    >
      <ActionMenu :items="actionMenuItems" />
    </aside>

    <!-- prettier-ignore -->
    <MarkdownViewer
      class="mx-auto"
      source="/md/vue3/vue3为什么要使用 value.md"
    />
  </div>
</template>
