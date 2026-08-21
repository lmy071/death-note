<script setup lang="ts">
import { ref } from 'vue'

type ActionName = 'x' | 'github' | 'discord'

const emit = defineEmits<{
  select: [action: ActionName]
}>()

const activeAction = ref<ActionName | null>(null)

function selectAction(action: ActionName) {
  activeAction.value = action
  emit('select', action)
}
</script>

<template>
  <!-- prettier-ignore -->
  <nav
    class="action-wrap"
    aria-label="社交菜单"
  >
    <button
      class="action"
      type="button"
      aria-label="X"
      :aria-pressed="activeAction === 'x'"
      @click="selectAction('x')"
    >
      <svg
        class="action-icon"
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 24 24"
        stroke-linejoin="round"
        stroke-linecap="round"
        stroke-width="2"
        stroke="currentColor"
        fill="none"
        aria-hidden="true"
      >
        <path d="M4 4l11.733 16h4.267l-11.733 -16z" />
        <path d="M4 20l6.768 -6.768m2.46 -2.46l6.772 -6.772" />
      </svg>
      <!-- prettier-ignore -->
      <span
        class="action-content"
        data-content="x"
        aria-hidden="true"
      />
    </button>

    <button
      class="action"
      type="button"
      aria-label="GitHub"
      :aria-pressed="activeAction === 'github'"
      @click="selectAction('github')"
    >
      <svg
        class="action-icon"
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 24 24"
        stroke-linejoin="round"
        stroke-linecap="round"
        stroke-width="2"
        stroke="currentColor"
        fill="none"
        aria-hidden="true"
      >
        <path
          d="M9 19c-4.3 1.4 -4.3 -2.5 -6 -3m12 5v-3.5c0 -1 .1 -1.4 -.5 -2c2.8 -.3 5.5 -1.4 5.5 -6a4.6 4.6 0 0 0 -1.3 -3.2a4.2 4.2 0 0 0 -.1 -3.2s-1.1 -.3 -3.5 1.3a12.3 12.3 0 0 0 -6.2 0c-2.4 -1.6 -3.5 -1.3 -3.5 -1.3a4.2 4.2 0 0 0 -.1 3.2a4.6 4.6 0 0 0 -1.3 3.2c0 4.6 2.7 5.7 5.5 6c-.6 .6 -.6 1.2 -.5 2v3.5"
        />
      </svg>
      <!-- prettier-ignore -->
      <span
        class="action-content"
        data-content="github"
        aria-hidden="true"
      />
    </button>

    <button
      class="action"
      type="button"
      aria-label="Discord"
      :aria-pressed="activeAction === 'discord'"
      @click="selectAction('discord')"
    >
      <svg
        class="action-icon"
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 24 24"
        stroke-linejoin="round"
        stroke-linecap="round"
        stroke-width="2"
        stroke="currentColor"
        fill="none"
        aria-hidden="true"
      >
        <path d="M8 12a1 1 0 1 0 2 0a1 1 0 0 0 -2 0" />
        <path d="M14 12a1 1 0 1 0 2 0a1 1 0 0 0 -2 0" />
        <path
          d="M15.5 17c0 1 1.5 3 2 3c1.5 0 2.833 -1.667 3.5 -3c.667 -1.667 .5 -5.833 -1.5 -11.5c-1.457 -1.015 -3 -1.34 -4.5 -1.5l-.972 1.923a11.913 11.913 0 0 0 -4.053 0l-.975 -1.923c-1.5 .16 -3.043 .485 -4.5 1.5c-2 5.667 -2.167 9.833 -1.5 11.5c.667 1.333 2 3 3.5 3c.5 0 2 -2 2 -3"
        />
        <path d="M7 16.5c3.5 1 6.5 1 10 0" />
      </svg>
      <!-- prettier-ignore -->
      <span
        class="action-content"
        data-content="discord"
        aria-hidden="true"
      />
    </button>

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
  opacity: 0;
  transition:
    left 400ms ease,
    opacity 400ms ease;
}

.action-content::before {
  z-index: 1;
  padding-inline: 4px;
  border-radius: calc(var(--light-radius) - 2px);
  font-size: 0.875rem;
  font-weight: 600;
  line-height: 1.25rem;
  text-transform: capitalize;
  background: #fff;
  content: attr(data-content);
  transform: translateX(-100%);
  transition: transform 300ms ease;
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

.action:is(:hover, :focus-visible) .action-icon,
.action[aria-pressed='true'] .action-icon {
  color: #000;
  background: #fff;
  transform: scale(1.4) translate3d(12px, 0, 12px);
}

.action:is(:hover, :focus-visible)::after,
.action:is(:hover, :focus-visible) .action-content::after,
.action[aria-pressed='true']::after,
.action[aria-pressed='true'] .action-content::after {
  width: var(--light-size);
  height: var(--light-size);
  opacity: 1;
  animation: action-menu-rotate 4s linear infinite;
}

.action:is(:hover, :focus-visible) .action-content,
.action[aria-pressed='true'] .action-content {
  left: calc(100% + 24px);
  z-index: 3;
  width: max-content;
  color: #000;
  background: #fff;
  opacity: 1;
}

.action:is(:hover, :focus-visible) .action-content::before,
.action[aria-pressed='true'] .action-content::before {
  transform: translateX(0);
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

  .action:is(:hover, :focus-visible) .action-content,
  .action[aria-pressed='true'] .action-content {
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
  .action-content,
  .action-content::before {
    transition-duration: 0.01ms !important;
  }
}
</style>
