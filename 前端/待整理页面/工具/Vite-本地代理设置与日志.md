# Vite 本地代理设置与日志

# Vite 本地代理设置与日志

在本地开发中，前端通常需要通过代理（proxy）解决跨域问题或将请求转发到后端服务。Vite 基于 http-proxy 实现了开发服务器代理，本文详细讲解配置方法与日志调试技巧。

## 1. 基础代理配置

**在 vite.config.ts 中通过 server.proxy 选项配置代理：**

```tsx
import { defineConfig } from 'vite'

export default defineConfig({
  server: {
    proxy: {
      // 字符串简写
      '/api': 'http://localhost:3000',

      // 带选项的完整写法
      '/api/v2': {
        target: 'http://localhost:3000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
```

## 2. 完整配置选项详解

```tsx
proxy: {
  '/api': {
    // ========== 必填项 ==========
    target: 'http://localhost:3000',  // 代理目标地址

    // ========== 常用选项 ==========
    changeOrigin: true,     // 将请求头中的 Host 改为 target 的主机名
    rewrite: (path) => path.replace(/^\/api/, ''),  // 重写请求路径
    secure: true,           // 是否验证 SSL 证书（HTTPS 目标）
    ws: true,               // 是否代理 WebSocket
    headers: {              // 自定义请求头
      'X-Custom-Header': 'value',
    },

    // ========== 高级选项 ==========
    prependPath: true,      // 将代理路径前缀添加到 target 前（默认 true）
    ignorePath: false,      // 忽略请求路径，直接用 target（默认 false）
    followRedirects: false, // 是否跟随重定向（默认 false）
    cookieDomainRewrite: {  // 重写 cookie 域名
      '*': '',              // 清除所有 cookie 域名
    },
    cookiePathRewrite: {    // 重写 cookie 路径
      '/api': '/',          // 将 /api 前缀替换为 /
    },

    // ========== 事件钩子 ==========
    configure: (proxy, options) => {
      // proxy 是 http-proxy 实例
      // 在此可以注册事件监听
    },

    // ========== 条件代理 ==========
    bypass: (req, res, options) => {
      // 返回 false 跳过代理
      // 返回路径字符串重写请求
      if (req.headers.accept?.includes('html')) {
        return '/index.html'
      }
    },
  },
}
```

## 3. 代理日志配置

Vite 代理底层使用 http-proxy，默认不输出任何代理日志。需要通过 configure 钩子手动注册事件来记录日志。

### 3.1 基础请求日志

```tsx
proxy: {
  '/api': {
    target: 'http://localhost:3000',
    changeOrigin: true,
    configure: (proxy) => {
      proxy.on('proxyReq', (proxyReq, req, res) => {
        console.log(
          `[Proxy Request] ${req.method} ${req.url} → ${proxyReq.path}`
        )
      })
    },
  },
}
```

### 3.2 详细日志 — 请求监听

```tsx
proxy: {
  '/api': {
    target: 'http://localhost:3000',
    changeOrigin: true,
    configure: (proxy) => {
      // 请求发出时
      proxy.on('proxyReq', (proxyReq, req, res) => {
        const startTime = Date.now()
        ;(req as any)._startTime = startTime

        console.log('\n📤 [Proxy Request]')
        console.log(`   Method: ${req.method}`)
        console.log(`   Original URL: ${req.url}`)
        console.log(`   Proxy Path: ${proxyReq.path}`)
        console.log(`   Target: ${proxyReq.getHeader('host')}`)
        console.log('   Headers:', JSON.stringify(
          Object.fromEntries(
            Object.entries(proxyReq.getHeaders())
              .filter(([k]) => !['cookie', 'authorization'].includes(k))
          ),
          null, 2
        ))
      })
    },
  },
}
```

### 3.3 详细日志 — 响应与错误监听

```tsx
      // 在同一个 configure 中继续添加：

      // 收到响应时
      proxy.on('proxyRes', (proxyRes, req, res) => {
        const duration = Date.now() - (req as any)._startTime

        console.log('\n📥 [Proxy Response]')
        console.log(`   Status: ${proxyRes.statusCode} ${proxyRes.statusMessage}`)
        console.log(`   Duration: ${duration}ms`)
        console.log(`   URL: ${req.url}`)
        console.log('   Response Headers:', JSON.stringify(
          Object.fromEntries(
            Object.entries(proxyRes.headers)
              .filter(([k]) => ['content-type','set-cookie','cache-control'].includes(k))
          ),
          null, 2
        ))
      })

      // 代理错误
      proxy.on('error', (err, req, res) => {
        console.error('\n❌ [Proxy Error]')
        console.error(`   URL: ${req?.url}`)
        console.error(`   Error: ${err.message}`)
        console.error(`   Code: ${err.code}`)
        if (!res.headersSent) {
          res.writeHead(502, { 'Content-Type': 'application/json' })
        }
        res.end(JSON.stringify({ error: 'Proxy Error', message: err.message }))
      })

      // 连接关闭
      proxy.on('close', () => {
        console.log('🔌 [Proxy Close] Connection closed')
      })
```

### 3.4 彩色日志工具函数

将日志逻辑封装为可复用函数，支持彩色输出和按环境开关：

```tsx
// utils/proxyLogger.ts

const COLORS = {
  reset: '\x1b[0m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  red: '\x1b[31m',
  cyan: '\x1b[36m',
  gray: '\x1b[90m',
  magenta: '\x1b[35m',
} as const

const ENABLED = process.env.VITE_PROXY_LOG !== 'false'

function timestamp(): string {
  return new Date().toLocaleTimeString('zh-CN', { hour12: false })
}

export function logProxyRequest(
  method: string, originalUrl: string,
  proxyPath: string, target: string,
) {
  if (!ENABLED) return
  console.log(
    `${COLORS.cyan}[${timestamp()}]${COLORS.reset} ` +
    `${COLORS.green}${method}${COLORS.reset} ` +
    `${originalUrl} ${COLORS.gray}→${COLORS.reset} ` +
    `${COLORS.magenta}${target}${proxyPath}${COLORS.reset}`,
  )
}

export function logProxyResponse(
  statusCode: number, duration: number, url: string,
) {
  if (!ENABLED) return
  const c = statusCode >= 400 ? COLORS.red
    : statusCode >= 300 ? COLORS.yellow : COLORS.green
  console.log(
    `${COLORS.cyan}[${timestamp()}]${COLORS.reset} ` +
    `${c}${statusCode}${COLORS.reset} ` +
    `${COLORS.gray}${duration}ms${COLORS.reset} ${url}`,
  )
}

export function logProxyError(url: string, message: string, code?: string) {
  if (!ENABLED) return
  console.error(
    `${COLORS.cyan}[${timestamp()}]${COLORS.reset} ` +
    `${COLORS.red}✖${COLORS.reset} ${url} ` +
    `${COLORS.red}${message}${COLORS.reset} ` +
    `${code ? COLORS.gray+'('+code+')'+COLORS.reset : ''}`,
  )
}
```

### 3.5 使用日志工具的代理配置

```tsx
import { defineConfig } from 'vite'
import { logProxyRequest, logProxyResponse, logProxyError } from './utils/proxyLogger'

export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:3000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
        configure: (proxy) => {
          proxy.on('proxyReq', (proxyReq, req) => {
            ;(req as any)._startTime = Date.now()
            logProxyRequest(
              req.method!, req.url!,
              proxyReq.path,
              proxyReq.getHeader('host') as string,
            )
          })
          proxy.on('proxyRes', (proxyRes, req) => {
            logProxyResponse(
              proxyRes.statusCode!,
              Date.now() - (req as any)._startTime,
              req.url!,
            )
          })
          proxy.on('error', (err, req) => {
            logProxyError(req?.url!, err.message, err.code)
          })
        },
      },
    },
  },
})
```

## 4. 多代理规则配置

实际项目中通常需要代理多个服务，以下是常见场景配置：

```tsx
export default defineConfig({
  server: {
    proxy: {
      // 主业务 API
      '/api': {
        target: 'http://localhost:3000',
        changeOrigin: true,
      },

      // 用户服务
      '/user-api': {
        target: 'http://localhost:3001',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/user-api/, '/api'),
      },

      // WebSocket 服务
      '/ws': {
        target: 'ws://localhost:3002',
        ws: true,
        changeOrigin: true,
      },

      // 静态资源 CDN 代理
      '/cdn': {
        target: 'https://cdn.example.com',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/cdn/, ''),
        secure: true,
        headers: { Referer: 'https://cdn.example.com/' },
      },

      // 上传服务（大文件需要调整超时）
      '/upload': {
        target: 'http://localhost:3003',
        changeOrigin: true,
        configure: (proxy) => {
          proxy.on('proxyReq', (proxyReq) => {
            proxyReq.setTimeout(5 * 60 * 1000) // 5 分钟
          })
        },
      },
    },
  },
})
```

## 5. 环境区分代理配置

```tsx
// vite.config.ts
import { defineConfig, loadEnv } from 'vite'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')

  return {
    server: {
      proxy: {
        '/api': {
          target: env.VITE_API_TARGET || 'http://localhost:3000',
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, ''),
        },
      },
    },
  }
})
```

```bash
# .env.development
VITE_API_TARGET=http://localhost:3000

# .env.staging
VITE_API_TARGET=https://staging-api.example.com

# .env.production（生产环境通常不用代理）
# VITE_API_TARGET=https://api.example.com
```

## 6. 代理日志输出示例

```
📤 [Proxy Request]
   Method: POST
   Original URL: /api/user/login
   Proxy Path: /user/login
   Target: localhost:3000
   Headers: {
     "content-type": "application/json",
     "accept": "application/json"
   }

📥 [Proxy Response]
   Status: 200 OK
   Duration: 45ms
   URL: /api/user/login
   Response Headers: {
     "content-type": "application/json; charset=utf-8",
     "cache-control": "no-cache"
   }

❌ [Proxy Error]
   URL: /api/data/sync
   Error: connect ECONNREFUSED 127.0.0.1:3000
   Code: ECONNREFUSED
```

## 7. 常见问题排查

### 7.1 代理后 404

- 检查 rewrite 规则是否正确移除了路径前缀`（最常见的坑：/api/users → 后端期望 /users，但 rewrite 未生效）`
- 检查 target 地址是否包含路径前缀（如 target: 'http://localhost:3000/v1'）

### 7.2 Cookie 丢失

- 设置 cookieDomainRewrite: { '*': '' } 清除 cookie 域名限制
- 设置 cookiePathRewrite: { '/api': '/' } 修正 cookie 路径

### 7.3 HTTPS 证书报错

- 设置 secure: false 跳过 SSL 验证（仅开发环境）
- 如果是自签名证书，还需设置 NODE_TLS_REJECT_UNAUTHORIZED=0

### 7.4 WebSocket 代理失败

- 确认 ws: true 已设置
- target 使用 ws:// 协议而非 http://
- 如果使用 Nginx，确认 upstream 配置了 proxy_set_header Upgrade

### 7.5 请求超时 / 大文件上传中断

- 在 configure 钩子中设置 proxyReq.setTimeout(超时毫秒数)
- Vite 开发服务器本身也有超时配置：server.proxy.timeout（默认 120s）

---

<aside>
💡 Vite 代理底层基于 http-proxy（github.com/http-party/node-http-proxy），所有 http-proxy 的选项和事件均可使用。代理配置仅在开发服务器生效，生产环境需通过 Nginx 等反向代理实现。

</aside>