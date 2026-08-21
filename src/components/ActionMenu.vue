<script setup lang="ts">
import type { ActionMenuIcon, ActionMenuItem } from './action-menu'

defineProps<{
  items: readonly ActionMenuItem[]
}>()

function isImageIcon(icon: ActionMenuIcon): icon is string {
  return typeof icon === 'string'
}

function isExternalUrl(url: string) {
  return /^(?:https?:)?\/\//.test(url)
}
</script>

<template>
  <!-- prettier-ignore -->
  <nav
    v-if="items.length"
    class="action-wrap"
    aria-label="社交菜单"
  >
    <a
      v-for="item in items"
      :key="`${item.name}:${item.url}`"
      class="action"
      :href="item.url"
      :aria-label="item.name"
      :title="item.name"
      :target="isExternalUrl(item.url) ? '_blank' : undefined"
      :rel="isExternalUrl(item.url) ? 'noopener noreferrer' : undefined"
    >
      <span
        class="action-icon"
        aria-hidden="true"
      >
        <img
          v-if="isImageIcon(item.icon)"
          class="action-icon-graphic"
          :src="item.icon"
          alt=""
        >
        <svg
          v-else
          class="action-icon-graphic"
          xmlns="http://www.w3.org/2000/svg"
          :viewBox="item.icon.viewBox ?? '0 0 24 24'"
          stroke-linejoin="round"
          stroke-linecap="round"
          stroke-width="2"
          stroke="currentColor"
          fill="none"
        >
          <path
            v-for="path in item.icon.paths"
            :key="path"
            :d="path"
          />
        </svg>
      </span>
      <span
        class="action-content"
        aria-hidden="true"
      >
        <span class="action-label">{{ item.name }}</span>
      </span>
    </a>

    <!-- prettier-ignore -->
    <div
      class="backdrop"
      aria-hidden="true"
    />
  </nav>
</template>

<style scoped>
.action-wrap {
  position: relative;
  z-index: 10;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border-radius: 9999px;
  isolation: isolate;
}

.backdrop {
  position: absolute;
  z-index: -1;
  display: flex;
  width: 100%;
  height: 100%;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border-radius: 9999px;
}

.backdrop::before {
  position: absolute;
  width: 10.5rem;
  height: 10.5rem;
  border-radius: 9999px;
  background: linear-gradient(144deg, #af40ff, #4f46e5);
  animation: action-menu-rotate 1.5s linear infinite;
  content: '';
}

.backdrop::after {
  position: absolute;
  z-index: 1;
  width: 100%;
  height: 100%;
  border-radius: 9999px;
  background: rgb(11 16 32 / 38%);
  backdrop-filter: blur(8px);
  content: '';
}

.action {
  --light-size: 60px;
  --light-radius: 9999px;
  --light-left: 14px;
  --light-start: transparent;
  --light-accent: #af40ff;

  position: relative;
  display: flex;
  width: 3.5rem;
  height: 3.5rem;
  align-items: center;
  justify-content: center;
  padding: 0.5rem;
  border: 0;
  border-radius: 9999px;
  color: #444;
  background: transparent;
  cursor: pointer;
  transition:
    color 300ms ease,
    transform 300ms ease,
    background-color 300ms ease;
}

.action-icon {
  position: relative;
  z-index: 2;
  width: 100%;
  height: 100%;
  padding: 0.5rem;
  border-radius: 9999px;
  background: #f1f1f1;
  transition:
    color 300ms ease,
    transform 300ms ease,
    background-color 300ms ease;
}

.action-icon-graphic {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.action-content {
  --light-size: 100px;
  --light-radius: 6px;
  --light-left: 0;
  --light-start: #fff;
  --light-accent: #af40ff;

  position: absolute;
  left: 0;
  z-index: -1;
  display: flex;
  width: max-content;
  height: 1.75rem;
  align-items: center;
  justify-content: center;
  padding: 8px 1px;
  overflow: hidden;
  border: 1px solid #ccc;
  border-radius: 6px;
  color: #000;
  font-size: 0.875rem;
  font-weight: 600;
  line-height: 1.25rem;
  opacity: 0;
  text-transform: capitalize;
  transition:
    left 400ms ease,
    opacity 400ms ease;
}

.action-label {
  position: relative;
  z-index: 1;
  padding-inline: 4px;
  border-radius: calc(var(--light-radius) - 2px);
  background: #fff;
}

.action::after,
.action-content::after {
  position: absolute;
  left: var(--light-left);
  width: 0;
  height: 0;
  border-radius: var(--light-radius);
  opacity: 0;
  background: conic-gradient(
    from 45deg at 50% 50%,
    var(--light-start),
    var(--light-accent),
    var(--light-start),
    var(--light-start),
    var(--light-start),
    var(--light-accent),
    var(--light-start),
    var(--light-start),
    var(--light-start)
  );
  content: '';
  transition:
    width 50ms ease 200ms,
    height 50ms ease 200ms,
    opacity 50ms ease 200ms;
}

.action:is(:hover, :focus-visible) .action-icon {
  color: #000;
  background: #fff;
  transform: scale(1.4) translate3d(12px, 0, 12px);
}

.action:is(:hover, :focus-visible)::after,
.action:is(:hover, :focus-visible) .action-content::after {
  width: var(--light-size);
  height: var(--light-size);
  opacity: 1;
  animation: action-menu-rotate 4s linear infinite;
}

.action:is(:hover, :focus-visible) .action-content {
  left: calc(100% + 24px);
  z-index: 3;
  width: max-content;
  color: #000;
  background: #fff;
  opacity: 1;
}

.action:focus-visible {
  outline: 2px solid #c084fc;
  outline-offset: 4px;
}

@keyframes action-menu-rotate {
  to {
    transform: rotate(1turn);
  }
}

@media (max-width: 639px) {
  .action {
    width: 3rem;
    height: 3rem;
    padding: 0.375rem;
  }

  .action:is(:hover, :focus-visible) .action-content {
    left: calc(100% + 18px);
  }
}

@media (prefers-reduced-motion: reduce) {
  .backdrop::before,
  .action::after,
  .action-content::after {
    animation: none !important;
  }

  .action,
  .action-icon,
  .action-content {
    transition-duration: 0.01ms !important;
  }
}
</style>
