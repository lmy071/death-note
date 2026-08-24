# Vue3路由实现原理

## 一、前端路由的本质

单页应用（SPA）中，路由的核心任务只有两个：

- **监听 URL 变化，解析出当前路径**
- **根据路径匹配对应的组件，渲染到页面中**

与后端路由不同，前端路由不发起网络请求，所有页面切换都在浏览器端完成，因此称为前端路由。

## 二、两种路由模式

### 1. Hash 模式（createWebHashHistory）

利用 URL 中的 # 号（即 hash）来模拟路由。hash 改变时浏览器不会刷新页面，通过 hashchange 事件监听变化。

```jsx
// Hash Router 核心原理
window.addEventListener('hashchange', () => {
  const hash = window.location.hash.slice(1) || '/'
  renderRoute(hash)
})

window.location.hash = '/home' // 不刷新页面

// URL 示例
// http://example.com/#/home
// http://example.com/#/about
```

优点：兼容性好，不需要后端配合。缺点：URL 带 # 不够美观，且 hash 部分不会被搜索引擎索引。

### 2. History 模式（createWebHistory）

基于 HTML5 的 History API（pushState、replaceState、popstate 事件），实现无 # 的干净 URL。

```jsx
// History Router 核心原理
window.addEventListener('popstate', () => {
  renderRoute(window.location.pathname)
})

function push(path) {
  window.history.pushState({}, '', path)
  renderRoute(path)
}

function replace(path) {
  window.history.replaceState({}, '', path)
  renderRoute(path)
}

// URL 示例
// http://example.com/home
// http://example.com/about
```

**注意：pushState/replaceState 不会触发 popstate 事件，所以手动调用后需要同步渲染。**

优点：URL 美观、SEO 友好。缺点：需要后端配置 fallback（所有路径指向 index.html），否则刷新会 404。

## 三、Vue Router 4 核心源码分析

### 1. createRouter 创建路由实例

```jsx
function createRouter(options) {
  const router = {
    currentRoute: shallowRef(START_LOCATION),
    history: options.history,
    matcher: createRouterMatcher(options.routes),
    install(app) {
      app.component('RouterLink', RouterLink)
      app.component('RouterView', RouterView)
      app.config.globalProperties.$router = this
      app.config.globalProperties.$route = this.currentRoute
      app.provide(routerKey, this)
      app.provide(routeLocationKey, reactive(this.currentRoute))
      this.history.listen((to) => {
        this.currentRoute.value = this.matcher.resolve(to)
      })
    },
    async push(to) {
      const target = this.matcher.resolve(to)
      const failure = await this.runGuards(target)
      if (failure) return failure
      await this.history.push(target.path)
      this.currentRoute.value = target
    },
  }
  return router
}
```

### 2. 响应式路由状态 — shallowRef + reactive

Vue Router 使用 Vue 3 的响应式系统来驱动路由变更。核心思路：

- **currentRoute 用 shallowRef 包裹，只做浅层响应 — 路由切换时整个替换**
- 通过 provide/inject 将路由状态注入到所有子组件中
- 组件内使用 useRoute() 获取当前路由信息，实质就是访问这个响应式对象

```jsx
const routeLocationKey = Symbol('route-location')
const routerKey = Symbol('router')

function useRoute() {
  return inject(routeLocationKey)
}
function useRouter() {
  return inject(routerKey)
}

// 当路由变化时，所有调用了 useRoute() 的组件
// 会自动重新渲染 — 这就是 Vue3 响应式的威力
```

### 3. 路由匹配器 — createRouterMatcher

路由匹配的核心是将路径字符串（如 /user/:id）转为正则表达式，并将路径参数提取出来。Vue Router 4 使用 path-to-regexp 库完成这一工作。

```jsx
function createRouterMatcher(routes) {
  const matchers = routes.map((route) => {
    const keys = []
    const regex = pathToRegexp(route.path, keys)
    return { ...route, regex, keys }
  })
  function resolve(rawPath) {
    for (const m of matchers) {
      const match = rawPath.match(m.regex)
      if (match) {
        const params = {}
        m.keys.forEach((key, i) => {
          params[key.name] = match[i + 1]
        })
        return { matched: [m], params, path: rawPath }
      }
    }
    return null
  }
  return { resolve }
}

// 路由 /user/:id + 路径 /user/123
// => { params: { id: '123' }, path: '/user/123' }
```

### 4. RouterView 组件原理

<RouterView> 是路由出口，根据 currentRoute 中的 matched 数组，用动态组件渲染匹配到的组件。

```jsx
const RouterView = defineComponent({
  name: 'RouterView',
  setup() {
    const route = useRoute()
    return () => {
      const matched = route.matched
      if (!matched || !matched.length) return h('div', 'No route matched')
      const component = matched[matched.length - 1].component
      return h(component)
    }
  },
})
```

### 5. RouterLink 组件原理

```jsx
const RouterLink = defineComponent({
  name: 'RouterLink',
  props: { to: [String, Object], replace: Boolean },
  setup(props, { slots }) {
    const router = useRouter()
    function navigate(e) {
      if (e) e.preventDefault()
      props.replace ? router.replace(props.to) : router.push(props.to)
    }
    return () =>
      h(
        'a',
        {
          href: router.resolve(props.to).href,
          onClick: navigate,
        },
        slots.default?.(),
      )
  },
})
```

### 6. 导航守卫的实现原理

Vue Router 的导航守卫是责任链模式。每次导航经过一系列守卫函数调用，任何一个返回 false 或重定向都会中断导航。

```jsx
// 执行顺序：
// 1. 失活组件的 beforeRouteLeave
// 2. 全局 beforeEach
// 3. 重用组件的 beforeRouteUpdate
// 4. 路由配置的 beforeEnter
// 5. 激活组件的 beforeRouteEnter
// 6. 全局 beforeResolve
// 7. 导航确认后触发 afterEach

async function runGuards(to, from) {
  const guards = [
    leaveGuards(from),
    globalBeforeEach,
    updateGuards(from),
    beforeEnterGuards(to),
    enterGuards(to),
    globalBeforeResolve,
  ]
  for (const g of guards) {
    const r = await g(to, from)
    if (r === false) return false
    if (typeof r === 'string') return runGuards(r, from)
  }
  globalAfterEach(to, from)
  return true
}
```

## 四、手写一个 Mini Router

下面是一个完整的微型 Vue Router 实现，包含 Hash 模式路由的核心逻辑：

```jsx
// MiniRouter.js — 迷你 Vue3 路由实现
import { shallowRef, reactive, defineComponent, h, provide, inject } from 'vue'

const RouterKey = Symbol('mini-router')
const RouteKey = Symbol('mini-route')
export function useRouter() { return inject(RouterKey) }
export function useRoute() { return inject(RouteKey) }

function pathToRegexp(path) {
  const keys = []
  const r = path.replace(/:([^/]+)/g, (_, key) => {
    keys.push(key); return '([^/]+)'
  })
  return { regex: new RegExp('^' + r + '$'), keys }
}

export function createMiniRouter(options) {
  const matchers = (options.routes || []).map(r => ({ ...r, ...pathToRegexp(r.path) }))
  const currentRoute = shallowRef({ path: '/', params: {}, matched: [] })

  function match(path) {
    for (const m of matchers) {
      const r = path.match(m.regex)
      if (r) {
        const params = {}
        m.keys.forEach((k, i) => { params[k] = r[i + 1] })
        return { path, params, matched: [m] }
      }
    }
    return { path, params: {}, matched: [] }
  }

  function onHashChange() {
    currentRoute.value = match(window.location.hash.slice(1) || '/')
  }
  window.addEventListener('hashchange', onHashChange)

  const router = {
    currentRoute,
    push(to) { window.location.hash = typeof to === 'string' ? to : to.path },
    install(app) {
      onHashChange()
      // 注册 RouterView 组件
      app.component('RouterView', { ... })
      app.component('RouterLink', { ... })
      app.provide(RouterKey, router)
      app.provide(RouteKey, reactive(currentRoute))
      app.config.globalProperties.$router = router
      app.config.globalProperties.$route = currentRoute
    }
  }
  return router
}
```

RouterView 和 RouterLink 的完整实现：

```jsx
app.component('RouterView', {
  setup() {
    const route = inject(RouteKey)
    return () => {
      const m = route.matched
      return m.length ? h(m[m.length - 1].component) : h('div', '404')
    }
  },
})

app.component('RouterLink', {
  props: { to: String },
  setup(props, { slots }) {
    const router = inject(RouterKey)
    return () =>
      h(
        'a',
        {
          href: '#' + props.to,
          onClick: (e) => {
            e.preventDefault()
            router.push(props.to)
          },
        },
        slots.default?.(),
      )
  },
})
```

## 五、Vue Router 4 新特性

- Composition API 原生支持 — useRouter()、useRoute() 等 composable 函数
- 动态路由 — addRoute()、removeRoute() 运行时增删路由
- 导航守卫改进 — 支持 async/await，更清晰的类型推导
- 历史记录状态（History State）— push/replace 时可携带任意数据
- Typescript 重写 — 完整的类型推导，更好的开发体验

## 六、总结

Vue Router 的核心原理可以用一句话概括：**监听 URL 变化 → 匹配路由 → 更新响应式状态 → 驱动组件渲染**

通过 Vue 3 的 shallowRef 和 reactive 系统，路由状态变更能够准确地触发组件更新；通过 path-to-regexp 库实现精确的路径匹配；通过责任链模式实现灵活的导航守卫。
