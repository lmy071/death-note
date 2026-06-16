<template>
  <div class="page-full bg-page text-body">
    <!-- Header -->
    <header class="ci-header">
      <div class="ci-header__left">
        <router-link to="/" class="ci-back">← 返回</router-link>
        <h1 class="ci-title">缓存管理器</h1>
        <span class="badge">KeepAlive</span>
      </div>
      <div class="ci-header__right">
        <!-- Auto-cache toggle -->
        <label class="ci-toggle" :title="isAutoCacheEnabled ? '自动缓存已开启' : '自动缓存已关闭'">
          <span class="ci-toggle__label">自动缓存</span>
          <input
            type="checkbox"
            class="ci-toggle__input"
            :checked="isAutoCacheEnabled"
            @change="toggleAutoCache()"
          />
          <span class="ci-toggle__track" :class="{ 'ci-toggle__track--on': isAutoCacheEnabled }">
            <span class="ci-toggle__thumb" />
          </span>
        </label>
        <button class="btn btn-hover" type="button" :disabled="cacheCount === 0" @click="handleClearAll">
          清空全部
        </button>
      </div>
    </header>

    <!-- Stats bar -->
    <div class="ci-stats">
      <div class="ci-stat-card">
        <div class="ci-stat-card__value">{{ cacheCount }}</div>
        <div class="ci-stat-card__label">缓存实例</div>
      </div>
      <div class="ci-stat-card">
        <div class="ci-stat-card__value">{{ activeCount }}</div>
        <div class="ci-stat-card__label">活跃实例</div>
      </div>
      <div class="ci-stat-card">
        <div class="ci-stat-card__value">{{ removedCount }}</div>
        <div class="ci-stat-card__label">已禁缓存</div>
      </div>
    </div>

    <!-- Cache list -->
    <div class="ci-list">
      <!-- Active cache instances -->
      <div v-if="cacheInstances.length > 0" class="ci-section">
        <div class="ci-section__title">
          <span class="ci-section__dot ci-section__dot--active" />
          缓存实例
          <span class="ci-section__count">{{ cacheCount }}</span>
        </div>
      </div>

      <TransitionGroup name="ci-item" tag="div" class="ci-items">
        <div
          v-for="instance in cacheInstances"
          :key="instance.name"
          class="ci-item"
          :class="{ 'ci-item--active': instance.isActive }"
        >
          <div class="ci-item__indicator" :class="{ 'ci-item__indicator--active': instance.isActive }" />

          <div class="ci-item__body">
            <div class="ci-item__name-row">
              <span class="ci-item__name">{{ getLabel(instance.name) }}</span>
              <span class="ci-item__comp-name">{{ instance.name }}</span>
              <span v-if="instance.isActive" class="ci-item__active-tag">活跃</span>
            </div>
            <div class="ci-item__meta">
              <span v-if="instance.routePath" class="ci-item__path">{{ instance.routePath }}</span>
              <span class="ci-item__time">{{ formatTime(instance.cachedAt) }}</span>
            </div>
          </div>

          <div class="ci-item__actions">
            <button
              v-if="instance.routePath"
              class="btn btn-hover ci-action-btn"
              type="button"
              title="跳转到该页面"
              @click="navigateTo(instance.routePath)"
            >
              跳转
            </button>
            <button
              class="btn btn-hover ci-action-btn ci-action-btn--danger"
              type="button"
              :disabled="instance.isActive"
              :title="instance.isActive ? '无法删除当前活跃实例' : '删除缓存并禁用自动缓存'"
              @click="handleRemove(instance.name)"
            >
              删除
            </button>
          </div>
        </div>
      </TransitionGroup>

      <!-- Removed (disabled) cache instances -->
      <div v-if="removedInstances.length > 0" class="ci-section ci-section--removed">
        <div class="ci-section__title">
          <span class="ci-section__dot ci-section__dot--removed" />
          已禁用自动缓存
          <span class="ci-section__count">{{ removedCount }}</span>
        </div>
        <div class="ci-section__hint">这些页面不会被自动缓存，可恢复</div>
      </div>

      <TransitionGroup name="ci-item" tag="div" class="ci-items">
        <div
          v-for="instance in removedInstances"
          :key="'rm-' + instance.name"
          class="ci-item ci-item--removed"
        >
          <div class="ci-item__indicator ci-item__indicator--removed" />

          <div class="ci-item__body">
            <div class="ci-item__name-row">
              <span class="ci-item__name">{{ getLabel(instance.name) }}</span>
              <span class="ci-item__comp-name">{{ instance.name }}</span>
            </div>
            <div class="ci-item__meta">
              <span v-if="instance.routePath" class="ci-item__path">{{ instance.routePath }}</span>
            </div>
          </div>

          <div class="ci-item__actions">
            <button
              class="btn btn-hover ci-action-btn ci-action-btn--restore"
              type="button"
              title="恢复自动缓存"
              @click="handleRestore(instance.name)"
            >
              恢复
            </button>
          </div>
        </div>
      </TransitionGroup>

      <!-- Empty state -->
      <div v-if="cacheInstances.length === 0 && removedInstances.length === 0" class="ci-empty">
        <div class="ci-empty__icon">🕳️</div>
        <div class="ci-empty__text">暂无缓存记录</div>
        <div class="ci-empty__hint">访问其他页面后，组件将被自动缓存</div>
      </div>
    </div>

    <!-- Delete confirm dialog -->
    <Teleport to="body">
      <Transition name="ci-dialog">
        <div v-if="confirmDialog.show" class="ci-dialog-overlay" @click.self="confirmDialog.show = false">
          <div class="ci-dialog">
            <div class="ci-dialog__title">确认删除</div>
            <div class="ci-dialog__body">
              确定要删除 <strong>{{ getLabel(confirmDialog.target) }}</strong> 的缓存吗？
              <br />删除后该页面将不再被自动缓存，直到你手动恢复。
            </div>
            <div class="ci-dialog__actions">
              <button class="btn btn-hover" type="button" @click="confirmDialog.show = false">取消</button>
              <button
                class="btn btn-hover ci-action-btn--danger"
                type="button"
                @click="confirmDelete"
              >
                确认删除
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script lang="ts">
export default {
  name: 'CacheInspectorView'
}
</script>

<script setup lang="ts">
import { computed, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useKeepAliveStore, nameLabelMap } from '../../composables/useKeepAliveStore'

const router = useRouter()
const {
  cacheInstances,
  cacheCount,
  removedInstances,
  removedCount,
  isAutoCacheEnabled,
  removeCache,
  restoreCache,
  clearAllCache,
  toggleAutoCache,
} = useKeepAliveStore()

const activeCount = computed(() => cacheInstances.value.filter((i) => i.isActive).length)

function getLabel(componentName: string): string {
  return nameLabelMap.value.get(componentName) ?? componentName
}

// ---- Confirm dialog ----
const confirmDialog = reactive({
  show: false,
  target: '',
})

function handleRemove(name: string) {
  confirmDialog.target = name
  confirmDialog.show = true
}

function confirmDelete() {
  removeCache(confirmDialog.target)
  confirmDialog.show = false
}

function handleRestore(name: string) {
  restoreCache(name)
}

function handleClearAll() {
  clearAllCache()
}

function navigateTo(path: string) {
  router.push(path)
}

function formatTime(ts: number): string {
  if (!ts) return '--'
  const d = new Date(ts)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}
</script>

<style scoped>
/* ========================================
   Layout
   ======================================== */
.ci-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(0, 0, 0, 0.15);
  flex-shrink: 0;
}

.ci-header__left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.ci-header__right {
  display: flex;
  align-items: center;
  gap: 14px;
}

.ci-back {
  font-size: 13px;
  color: rgba(130, 177, 255, 0.9);
  text-decoration: none;
  transition: color 0.15s;
}
.ci-back:hover { color: rgba(160, 200, 255, 1); }

.ci-title {
  font-size: 16px;
  font-weight: 750;
  letter-spacing: 0.5px;
}

/* ========================================
   Toggle Switch
   ======================================== */
.ci-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  user-select: none;
}

.ci-toggle__label {
  font-size: 12px;
  color: rgba(230, 232, 239, 0.65);
}

.ci-toggle__input {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
}

.ci-toggle__track {
  position: relative;
  width: 36px;
  height: 20px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.12);
  transition: all 0.2s ease;
}

.ci-toggle__track--on {
  background: rgba(0, 212, 255, 0.25);
  border-color: rgba(0, 212, 255, 0.4);
}

.ci-toggle__thumb {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: rgba(230, 232, 239, 0.6);
  transition: all 0.2s ease;
}

.ci-toggle__track--on .ci-toggle__thumb {
  left: 18px;
  background: #00d4ff;
  box-shadow: 0 0 6px rgba(0, 212, 255, 0.5);
}

/* ========================================
   Stats Bar
   ======================================== */
.ci-stats {
  display: flex;
  gap: 12px;
  padding: 16px 20px;
  flex-shrink: 0;
}

.ci-stat-card {
  flex: 1;
  padding: 14px 16px;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(10, 16, 32, 0.6);
  text-align: left;
}

.ci-stat-card__value {
  font-size: 22px;
  font-weight: 800;
  color: rgba(130, 177, 255, 0.95);
  line-height: 1.2;
}

.ci-stat-card__label {
  font-size: 11px;
  color: rgba(230, 232, 239, 0.5);
  margin-top: 4px;
  letter-spacing: 0.5px;
}

/* ========================================
   Section Headers
   ======================================== */
.ci-section {
  padding: 12px 2px 4px;
}

.ci-section--removed {
  margin-top: 12px;
}

.ci-section__title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  font-weight: 700;
  color: rgba(230, 232, 239, 0.7);
  letter-spacing: 0.5px;
  text-transform: uppercase;
}

.ci-section__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.ci-section__dot--active {
  background: #00d4ff;
  box-shadow: 0 0 6px rgba(0, 212, 255, 0.4);
}

.ci-section__dot--removed {
  background: rgba(255, 100, 100, 0.6);
}

.ci-section__count {
  font-size: 10px;
  color: rgba(230, 232, 239, 0.4);
  background: rgba(255, 255, 255, 0.06);
  padding: 1px 6px;
  border-radius: 999px;
}

.ci-section__hint {
  font-size: 11px;
  color: rgba(230, 232, 239, 0.35);
  margin-top: 4px;
}

/* ========================================
   Cache List
   ======================================== */
.ci-list {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 4px 20px 24px;
}

.ci-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 200px;
  color: rgba(230, 232, 239, 0.55);
}
.ci-empty__icon { font-size: 40px; margin-bottom: 12px; }
.ci-empty__text { font-size: 15px; font-weight: 600; }
.ci-empty__hint { font-size: 12px; margin-top: 6px; color: rgba(230, 232, 239, 0.35); }

.ci-items {
  display: grid;
  gap: 6px;
}

.ci-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(10, 16, 32, 0.6);
  transition: all 0.2s ease;
}
.ci-item:hover {
  background: rgba(18, 28, 60, 0.8);
  border-color: rgba(255, 255, 255, 0.12);
}
.ci-item--active {
  border-color: rgba(130, 177, 255, 0.28);
  background: rgba(130, 177, 255, 0.08);
}
.ci-item--removed {
  border-color: rgba(255, 100, 100, 0.12);
  background: rgba(255, 100, 100, 0.04);
  opacity: 0.7;
}
.ci-item--removed:hover {
  opacity: 1;
  background: rgba(255, 100, 100, 0.08);
}

.ci-item__indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.15);
  flex-shrink: 0;
}
.ci-item__indicator--active {
  background: #00d4ff;
  box-shadow: 0 0 8px rgba(0, 212, 255, 0.5);
  animation: pulse 2s ease-in-out infinite;
}
.ci-item__indicator--removed {
  background: rgba(255, 100, 100, 0.5);
}

@keyframes pulse {
  0%, 100% { box-shadow: 0 0 4px rgba(0, 212, 255, 0.3); }
  50% { box-shadow: 0 0 12px rgba(0, 212, 255, 0.6); }
}

.ci-item__body {
  flex: 1;
  min-width: 0;
  text-align: left;
}

.ci-item__name-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.ci-item__name {
  font-size: 13px;
  font-weight: 650;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.ci-item__comp-name {
  font-size: 10px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  color: rgba(230, 232, 239, 0.35);
  padding: 1px 5px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.04);
}

.ci-item__active-tag {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.5px;
  padding: 1px 6px;
  border-radius: 4px;
  background: rgba(0, 212, 255, 0.15);
  color: #00d4ff;
  border: 1px solid rgba(0, 212, 255, 0.3);
}

.ci-item__meta {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 3px;
  font-size: 11px;
  color: rgba(230, 232, 239, 0.45);
}

.ci-item__path {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 11px;
}

.ci-item__actions {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
}

.ci-action-btn {
  font-size: 12px;
  padding: 4px 10px;
  height: 28px;
}

.ci-action-btn--danger {
  color: rgba(255, 100, 100, 0.9);
  border-color: rgba(255, 100, 100, 0.25);
}
.ci-action-btn--danger:hover:not(:disabled) {
  background: rgba(255, 100, 100, 0.12);
  border-color: rgba(255, 100, 100, 0.4);
}
.ci-action-btn--danger:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.ci-action-btn--restore {
  color: rgba(80, 220, 140, 0.9);
  border-color: rgba(80, 220, 140, 0.25);
}
.ci-action-btn--restore:hover {
  background: rgba(80, 220, 140, 0.12);
  border-color: rgba(80, 220, 140, 0.4);
}

/* ========================================
   Transition — list item
   ======================================== */
.ci-item-enter-active {
  transition: all 0.25s ease-out;
}
.ci-item-leave-active {
  transition: all 0.2s ease-in;
}
.ci-item-enter-from {
  opacity: 0;
  transform: translateY(-8px);
}
.ci-item-leave-to {
  opacity: 0;
  transform: translateX(20px);
}
.ci-item-move {
  transition: transform 0.25s ease;
}

/* ========================================
   Dialog
   ======================================== */
.ci-dialog-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: grid;
  place-items: center;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(4px);
}

.ci-dialog {
  width: 360px;
  max-width: 90vw;
  padding: 24px;
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(10, 16, 32, 0.98);
  box-shadow: 0 8px 40px rgba(0, 0, 0, 0.5);
  text-align: left;
}

.ci-dialog__title {
  font-size: 16px;
  font-weight: 750;
  margin-bottom: 12px;
}

.ci-dialog__body {
  font-size: 13px;
  color: rgba(230, 232, 239, 0.75);
  line-height: 1.6;
  margin-bottom: 20px;
}

.ci-dialog__body strong {
  color: rgba(130, 177, 255, 0.95);
}

.ci-dialog__actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.ci-dialog-enter-active { transition: all 0.2s ease-out; }
.ci-dialog-leave-active { transition: all 0.15s ease-in; }
.ci-dialog-enter-from,
.ci-dialog-leave-to {
  opacity: 0;
}

/* ========================================
   Scrollbar
   ======================================== */
.ci-list {
  scrollbar-width: thin;
  scrollbar-color: rgba(130, 177, 255, 0.5) rgba(255, 255, 255, 0.06);
}
.ci-list::-webkit-scrollbar { width: 9px; }
.ci-list::-webkit-scrollbar-track { background: rgba(0, 0, 0, 0.2); border-radius: 999px; }
.ci-list::-webkit-scrollbar-thumb {
  border-radius: 999px;
  border: 2px solid transparent;
  background-clip: content-box;
  background-color: rgba(130, 177, 255, 0.38);
}
.ci-list::-webkit-scrollbar-thumb:hover { background-color: rgba(130, 177, 255, 0.58); }
</style>
