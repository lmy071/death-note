<script setup lang="ts">
import { ref } from 'vue'

const count = ref(0)
</script>

<template>
  <div class="flex flex-col items-center gap-6 p-8">
    <div class="flex flex-col items-center gap-2">
      <h2 class="text-2xl font-bold text-body">
        Death Note
      </h2>
      <p class="text-dim">
        Vue 3 + Vite + TypeScript + UnoCSS 标准模板
      </p>
    </div>

    <button
      class="btn btn-hover btn-disabled"
      type="button"
      @click="count++"
    >
      count is {{ count }}
    </button>

    <RouterLink
      to="/about"
      class="btn btn-hover"
    >
      Go to About →
    </RouterLink>
  </div>
</template>
