import { createRouter, createWebHashHistory } from 'vue-router'

// 自动扫描 src/views 下所有 .vue 文件，根据文件结构生成路由
const viewContext = require.context('../views', true, /\.vue$/)

/**
 * 文件路径 -> 路由 path（项目约定）
 * ./HomeView.vue          -> /
 * ./code/leetCodeView.vue -> /code/leet-code
 */
function toRoutePath(filePath) {
  // 去掉 "./" 前缀和 ".vue" 后缀
  const relative = filePath
    .replace(/^\.\//, '')
    .replace(/\.vue$/, '')

  // 去掉末尾的 "View" 后缀（项目命名约定）
  const withoutView = relative.replace(/View$/, '')

  // 按目录分隔符分段，每段转 kebab-case
  const segments = withoutView.split('/').map((seg) =>
    seg
      .replace(/([A-Z])/g, '-$1')
      .toLowerCase()
      .replace(/^-/, '')
  )

  const path = '/' + segments.filter(Boolean).join('/')

  // Home 特殊处理
  if (path === '/' || path === '/home') {
    return '/'
  }

  return path
}

function toRouteName(filePath) {
  const relative = filePath
    .replace(/^\.\//, '')
    .replace(/\.vue$/, '')
    .replace(/View$/, '')
  return relative.replace(/\//g, '-').toLowerCase() || 'home'
}

// 生成路由配置
const autoRoutes = viewContext.keys().map((key) => {
  const mod = viewContext(key)
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

