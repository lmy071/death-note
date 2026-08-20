<script setup lang="ts">
import { RouterLink } from 'vue-router'
</script>

<template>
  <div class="flex flex-col items-center gap-4 p-8">
    <h2 class="text-2xl font-bold text-body">
      About
    </h2>
    <p class="text-dim">
      This is an about page
    </p>
    <RouterLink
      to="/"
      class="btn btn-hover"
    >
      ← Back to Home
    </RouterLink>
  </div>
</template>
