<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    visible: boolean
    text?: string
    backdrop?: string
    zIndex?: number
  }>(),
  {
    text: '加载中…',
    backdrop: 'rgba(5, 8, 18, 0.86)',
    zIndex: 1000,
  },
)

const maskStyle = computed(() => ({
  '--loading-backdrop': props.backdrop,
  zIndex: props.zIndex,
}))
</script>

<template>
  <Teleport to="body">
    <Transition name="loading-mask">
      <div
        v-if="visible"
        class="loading-mask"
        :style="maskStyle"
        role="status"
        aria-live="polite"
        aria-busy="true"
        :aria-label="text"
      >
        <div class="loading-mask__content">
          <div class="wrapper" aria-hidden="true">
            <div class="circle" />
            <div class="circle" />
            <div class="circle" />
            <div class="shadow" />
            <div class="shadow" />
            <div class="shadow" />
          </div>

          <p v-if="text" class="loading-mask__text">
            {{ text }}
          </p>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.loading-mask {
  position: fixed;
  inset: 0;
  display: grid;
  place-items: center;
  padding: 1.5rem;
  background: var(--loading-backdrop);
  backdrop-filter: blur(8px);
}

.loading-mask__content {
  display: grid;
  justify-items: center;
  gap: 1.5rem;
}

.wrapper {
  position: relative;
  z-index: 1;
  width: 200px;
  height: 60px;
}

.circle {
  position: absolute;
  left: 15%;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background-color: #fff;
  transform-origin: 50%;
  animation: circle7124 0.5s alternate infinite ease;
}

.circle:nth-child(2) {
  left: 45%;
  animation-delay: 0.2s;
}

.circle:nth-child(3) {
  right: 15%;
  left: auto;
  animation-delay: 0.3s;
}

.shadow {
  position: absolute;
  z-index: -1;
  top: 62px;
  left: 15%;
  width: 20px;
  height: 4px;
  border-radius: 50%;
  background-color: rgba(0, 0, 0, 0.9);
  filter: blur(1px);
  transform-origin: 50%;
  animation: shadow046 0.5s alternate infinite ease;
}

.shadow:nth-child(4) {
  left: 15%;
}

.shadow:nth-child(5) {
  left: 45%;
  animation-delay: 0.2s;
}

.shadow:nth-child(6) {
  right: 15%;
  left: auto;
  animation-delay: 0.3s;
}

.loading-mask__text {
  margin: 0;
  color: rgba(230, 232, 239, 0.82);
  font-size: 0.875rem;
  letter-spacing: 0.12em;
}

.loading-mask-enter-active,
.loading-mask-leave-active {
  transition: opacity 180ms ease-out;
}

.loading-mask-enter-from,
.loading-mask-leave-to {
  opacity: 0;
}

@keyframes circle7124 {
  0% {
    top: 60px;
    height: 5px;
    border-radius: 50px 50px 25px 25px;
    transform: scaleX(1.7);
  }

  40% {
    height: 20px;
    border-radius: 50%;
    transform: scaleX(1);
  }

  100% {
    top: 0;
  }
}

@keyframes shadow046 {
  0% {
    transform: scaleX(1.5);
  }

  40% {
    opacity: 0.7;
    transform: scaleX(1);
  }

  100% {
    opacity: 0.4;
    transform: scaleX(0.2);
  }
}

@media (prefers-reduced-motion: reduce) {
  .circle,
  .shadow {
    animation: none;
  }

  .circle {
    top: 20px;
  }

  .loading-mask-enter-active,
  .loading-mask-leave-active {
    transition: none;
  }
}
</style>
