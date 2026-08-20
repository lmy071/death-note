<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'

type ButtonSize = 'x-small' | 'small' | 'default' | 'large' | 'x-large'
type ButtonVariant = 'elevated' | 'flat' | 'tonal' | 'outlined' | 'text' | 'plain'

interface Ripple {
  id: number
  size: number
  x: number
  y: number
}

const props = withDefaults(
  defineProps<{
    block?: boolean
    color?: string
    disabled?: boolean
    icon?: boolean
    loading?: boolean
    rounded?: boolean | 'sm' | 'md' | 'lg' | 'xl' | 'pill'
    size?: ButtonSize
    type?: 'button' | 'submit' | 'reset'
    variant?: ButtonVariant
  }>(),
  {
    color: '#82b1ff',
    rounded: 'md',
    size: 'default',
    type: 'button',
    variant: 'elevated',
  },
)

const ripples = ref<Ripple[]>([])
const rippleTimers = new Map<number, ReturnType<typeof globalThis.setTimeout>>()
let rippleId = 0

const classes = computed(() => [
  `animated-button--${props.variant}`,
  `animated-button--${props.size}`,
  `animated-button--rounded-${props.rounded === true ? 'pill' : props.rounded || 'none'}`,
  {
    'animated-button--block': props.block,
    'animated-button--icon': props.icon,
    'animated-button--loading': props.loading,
  },
])

const buttonStyle = computed(() => ({ '--button-color': props.color }))

function createRipple(event: globalThis.PointerEvent) {
  if (props.disabled || props.loading) return

  const target = event.currentTarget as globalThis.HTMLButtonElement
  const bounds = target.getBoundingClientRect()
  const size = Math.max(bounds.width, bounds.height) * 1.65
  const id = ++rippleId

  ripples.value.push({
    id,
    size,
    x: event.clientX - bounds.left - size / 2,
    y: event.clientY - bounds.top - size / 2,
  })

  rippleTimers.set(
    id,
    globalThis.setTimeout(() => {
      ripples.value = ripples.value.filter((ripple) => ripple.id !== id)
      rippleTimers.delete(id)
    }, 650),
  )
}

onBeforeUnmount(() => {
  rippleTimers.forEach((timer) => globalThis.clearTimeout(timer))
})
</script>

<template>
  <button
    class="animated-button"
    :class="classes"
    :style="buttonStyle"
    :type="type"
    :disabled="disabled || loading"
    :aria-busy="loading || undefined"
    @pointerdown="createRipple"
  >
    <span class="animated-button__glow" aria-hidden="true" />
    <span class="animated-button__shine" aria-hidden="true" />

    <span
      v-for="ripple in ripples"
      :key="ripple.id"
      class="animated-button__ripple"
      :style="{
        width: `${ripple.size}px`,
        height: `${ripple.size}px`,
        left: `${ripple.x}px`,
        top: `${ripple.y}px`,
      }"
      aria-hidden="true"
    />

    <span v-if="loading" class="animated-button__loader" aria-hidden="true">
      <slot name="loader">
        <span class="animated-button__spinner" />
      </slot>
    </span>

    <span class="animated-button__content" :class="{ 'animated-button__content--hidden': loading }">
      <span v-if="$slots.prepend" class="animated-button__affix">
        <slot name="prepend" />
      </span>
      <slot />
      <span v-if="$slots.append" class="animated-button__affix">
        <slot name="append" />
      </span>
    </span>
  </button>
</template>

<style scoped>
.animated-button {
  --button-color: #82b1ff;
  --button-height: 40px;
  --button-padding: 0 20px;
  --button-radius: 10px;
  --button-font-size: 0.875rem;

  position: relative;
  isolation: isolate;
  display: inline-grid;
  min-width: 64px;
  height: var(--button-height);
  padding: var(--button-padding);
  overflow: hidden;
  border: 0;
  border-radius: var(--button-radius);
  color: white;
  background: var(--button-color);
  box-shadow:
    0 2px 5px rgb(0 0 0 / 24%),
    0 5px 14px color-mix(in srgb, var(--button-color) 28%, transparent);
  font-size: var(--button-font-size);
  font-weight: 600;
  letter-spacing: 0.025em;
  line-height: 1;
  vertical-align: middle;
  cursor: pointer;
  user-select: none;
  transition:
    translate 180ms cubic-bezier(0.2, 0, 0, 1),
    scale 180ms cubic-bezier(0.2, 0, 0, 1),
    box-shadow 220ms ease,
    background-color 220ms ease,
    color 220ms ease;
}

.animated-button::before {
  position: absolute;
  z-index: -1;
  inset: 0;
  background: white;
  content: '';
  opacity: 0;
  transition: opacity 180ms ease;
}

.animated-button:hover:not(:disabled) {
  translate: 0 -2px;
  box-shadow:
    0 5px 10px rgb(0 0 0 / 26%),
    0 10px 26px color-mix(in srgb, var(--button-color) 38%, transparent);
}

.animated-button:hover:not(:disabled)::before {
  opacity: 0.1;
}

.animated-button:active:not(:disabled) {
  translate: 0 0;
  scale: 0.97;
  box-shadow: 0 2px 5px rgb(0 0 0 / 25%);
}

.animated-button:focus-visible {
  outline: 3px solid color-mix(in srgb, var(--button-color) 42%, white);
  outline-offset: 3px;
}

.animated-button:disabled {
  color: rgb(255 255 255 / 45%);
  background: color-mix(in srgb, var(--button-color) 28%, #1b2230);
  box-shadow: none;
  cursor: not-allowed;
  opacity: 0.62;
}

.animated-button__content {
  z-index: 2;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  transition:
    opacity 150ms ease,
    transform 180ms ease;
}

.animated-button:hover:not(:disabled) .animated-button__content {
  transform: translateY(-1px);
}

.animated-button__content--hidden {
  opacity: 0;
}

.animated-button__affix {
  display: inline-grid;
  place-items: center;
  font-size: 1.15em;
}

.animated-button__glow {
  position: absolute;
  z-index: -1;
  inset: auto 12% -70% 12%;
  height: 100%;
  border-radius: 50%;
  background: var(--button-color);
  filter: blur(18px);
  opacity: 0;
  transition:
    opacity 220ms ease,
    transform 350ms ease;
}

.animated-button:hover:not(:disabled) .animated-button__glow {
  opacity: 0.7;
  transform: translateY(-25%);
}

.animated-button__shine {
  position: absolute;
  z-index: 1;
  top: -65%;
  left: -50%;
  width: 32%;
  height: 230%;
  background: linear-gradient(90deg, transparent, rgb(255 255 255 / 48%), transparent);
  opacity: 0;
  pointer-events: none;
  transform: rotate(18deg) translateX(-160%);
}

.animated-button:hover:not(:disabled) .animated-button__shine {
  animation: button-shine 850ms cubic-bezier(0.2, 0, 0, 1);
}

.animated-button__ripple {
  position: absolute;
  z-index: 1;
  border-radius: 50%;
  background: rgb(255 255 255 / 38%);
  pointer-events: none;
  transform: scale(0);
  animation: button-ripple 650ms ease-out forwards;
}

.animated-button__loader {
  position: absolute;
  z-index: 3;
  inset: 0;
  display: grid;
  place-items: center;
}

.animated-button__spinner {
  width: 20px;
  height: 20px;
  border: 2px solid currentcolor;
  border-right-color: transparent;
  border-radius: 50%;
  animation: button-spin 700ms linear infinite;
}

.animated-button--flat {
  box-shadow: none;
}

.animated-button--tonal {
  color: var(--button-color);
  background: color-mix(in srgb, var(--button-color) 18%, transparent);
  box-shadow: none;
}

.animated-button--outlined {
  color: var(--button-color);
  border: 1px solid color-mix(in srgb, var(--button-color) 65%, transparent);
  background: transparent;
  box-shadow: none;
}

.animated-button--text,
.animated-button--plain {
  color: var(--button-color);
  background: transparent;
  box-shadow: none;
}

.animated-button--plain {
  opacity: 0.7;
}

.animated-button--plain:hover:not(:disabled) {
  opacity: 1;
}

.animated-button--block {
  display: grid;
  width: 100%;
}

.animated-button--icon {
  width: var(--button-height);
  min-width: var(--button-height);
  padding: 0;
  border-radius: 50%;
}

.animated-button--x-small {
  --button-height: 28px;
  --button-padding: 0 12px;
  --button-font-size: 0.7rem;
}

.animated-button--small {
  --button-height: 34px;
  --button-padding: 0 16px;
  --button-font-size: 0.78rem;
}

.animated-button--large {
  --button-height: 48px;
  --button-padding: 0 26px;
  --button-font-size: 0.95rem;
}

.animated-button--x-large {
  --button-height: 56px;
  --button-padding: 0 32px;
  --button-font-size: 1rem;
}

.animated-button--rounded-none {
  --button-radius: 0;
}

.animated-button--rounded-sm {
  --button-radius: 4px;
}

.animated-button--rounded-md {
  --button-radius: 10px;
}

.animated-button--rounded-lg {
  --button-radius: 16px;
}

.animated-button--rounded-xl {
  --button-radius: 24px;
}

.animated-button--rounded-pill {
  --button-radius: 999px;
}

@keyframes button-ripple {
  to {
    opacity: 0;
    transform: scale(1);
  }
}

@keyframes button-shine {
  0% {
    opacity: 0;
    transform: rotate(18deg) translateX(-160%);
  }
  25% {
    opacity: 0.75;
  }
  100% {
    opacity: 0;
    transform: rotate(18deg) translateX(600%);
  }
}

@keyframes button-spin {
  to {
    transform: rotate(1turn);
  }
}

@media (prefers-reduced-motion: reduce) {
  .animated-button,
  .animated-button::before,
  .animated-button__content,
  .animated-button__glow {
    transition-duration: 0.01ms;
  }

  .animated-button__shine,
  .animated-button__ripple {
    display: none;
  }

  .animated-button__spinner {
    animation-duration: 1.4s;
  }
}
</style>
