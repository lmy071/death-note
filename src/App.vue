<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'
</script>

<template>
  <div class="page-full">
    <header class="flex items-center gap-4 px-6 h-16 border-card bg-card">
      <h1 class="text-lg font-bold text-body">
        death-note
      </h1>
      <nav class="flex gap-4">
        <RouterLink
          to="/"
          class="text-dim hover:text-body transition-card"
        >
          Home
        </RouterLink>
        <RouterLink
          to="/about"
          class="text-dim hover:text-body transition-card"
        >
          About
        </RouterLink>
      </nav>
    </header>

    <main class="flex-1 w-full flex flex-col items-center justify-center bg-page">
      <RouterView />
    </main>
  </div>
</template>
