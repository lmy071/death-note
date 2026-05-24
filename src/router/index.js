import { createRouter, createWebHashHistory } from 'vue-router'

// 自动扫描 src/views 下所有 .vue 文件，根据文件结构生成路由
const viewModules = import.meta.glob('../views/**/*.vue', { eager: true })

/**
 * 文件路径 -> 路由 path（项目约定）
 * ../views/HomeView.vue          -> /
 * ../views/code/leetCodeView.vue -> /code/leet-code
 */
function toRoutePath(filePath) {
  // 去掉 "../views" 前缀和 ".vue" 后缀
  const relative = filePath
    .replace('../views', '')
    .replace('.vue', '')

  // 去掉末尾的 "View" 后缀（项目命名约定）
  const withoutView = relative.replace(/View$/, '')

  // 按目录分隔符分段，每段转 kebab-case
  const segments = withoutView.split('/').map((seg) =>
    seg
      .replace(/([A-Z])/g, '-$1')
      .toLowerCase()
      .replace(/^-/, '')
  )

  const routePath = '/' + segments.filter(Boolean).join('/')

  // Home 特殊处理
  if (routePath === '/' || routePath === '/home') {
    return '/'
  }

  return routePath
}

function toRouteName(filePath) {
  const relative = filePath
    .replace('../views', '')
    .replace('.vue', '')
    .replace(/View$/, '')
  return relative.replace(/\//g, '-').toLowerCase() || 'home'
}

// 生成路由配置
const autoRoutes = Object.entries(viewModules).map(([key, mod]) => {
  return {
    path: toRoutePath(key),
    name: toRouteName(key),
    component: mod.default || mod
  }
})

// 确保 / 排在第一位
autoRoutes.sort((a, b) => {
  if (a.path === '/') return -1
  if (b.path === '/') return 1
  return a.path.localeCompare(b.path)
})

const router = createRouter({
  history: createWebHashHistory(),
  routes: autoRoutes
})

export default router