import { fileURLToPath, URL } from 'node:url'
import { readdir } from 'node:fs/promises'
import { relative, resolve, sep } from 'node:path'

import { defineConfig, type Plugin } from 'vite'
import vue from '@vitejs/plugin-vue'
import UnoCSS from '@unocss/vite'
import { presetUno, presetAttributify } from 'unocss'
import { sites } from '@openai/sites-vite-plugin'

const markdownModuleId = 'virtual:markdown-files'
const resolvedMarkdownModuleId = `\0${markdownModuleId}`

async function findMarkdownFiles(directory: string): Promise<string[]> {
  const entries = await readdir(directory, { withFileTypes: true }).catch(() => [])
  const files = await Promise.all(
    entries.map(async (entry) => {
      const path = resolve(directory, entry.name)
      if (entry.isDirectory()) return findMarkdownFiles(path)
      return entry.isFile() && entry.name.toLowerCase().endsWith('.md') ? [path] : []
    }),
  )

  return files.flat()
}

function markdownFilesPlugin(): Plugin {
  const markdownRoot = resolve(fileURLToPath(new URL('.', import.meta.url)), 'public/md')
  const isMarkdownFile = (path: string) =>
    path.startsWith(`${markdownRoot}${sep}`) && path.toLowerCase().endsWith('.md')

  return {
    name: 'markdown-files',
    resolveId(id) {
      return id === markdownModuleId ? resolvedMarkdownModuleId : undefined
    },
    async load(id) {
      if (id !== resolvedMarkdownModuleId) return undefined

      const files = await findMarkdownFiles(markdownRoot)
      const sources = files
        .map((file) => relative(markdownRoot, file))
        .sort((left, right) => left.localeCompare(right, 'zh-CN'))
        .map(
          (file) =>
            `/md/${file
              .split(sep)
              .map((segment) => encodeURIComponent(segment))
              .join('/')}`,
        )

      return `export default ${JSON.stringify(sources)}`
    },
    configureServer(server) {
      const refreshTree = (path: string) => {
        if (!isMarkdownFile(path)) return
        const module = server.moduleGraph.getModuleById(resolvedMarkdownModuleId)
        if (module) server.moduleGraph.invalidateModule(module)
        server.ws.send({ type: 'full-reload' })
      }

      server.watcher.add(markdownRoot)
      server.watcher.on('add', refreshTree)
      server.watcher.on('unlink', refreshTree)
    },
  }
}

export default defineConfig({
  plugins: [
    sites(),
    markdownFilesPlugin(),
    vue(),
    UnoCSS({
      presets: [presetUno(), presetAttributify()],
      shortcuts: {
        // 布局
        'page-full': 'h-screen w-screen flex flex-col items-center overflow-hidden',
        'page-full-row': 'h-screen w-screen flex overflow-hidden',
        // 文本
        'text-body': 'text-[#e6e8ef]',
        'text-dim': 'text-[rgba(230,232,239,0.75)]',
        'text-dim-2': 'text-[rgba(230,232,239,0.65)]',
        'text-dim-3': 'text-[rgba(230,232,239,0.7)]',
        // 边框
        'border-card': 'border-1 border-solid border-[rgba(255,255,255,0.08)]',
        'border-input': 'border-1 border-solid border-[rgba(255,255,255,0.12)]',
        'border-active': 'border-1 border-solid border-[rgba(130,177,255,0.28)]',
        // 背景
        'bg-page': 'bg-[#0b1020]',
        'bg-card': 'bg-[rgba(10,16,32,0.95)]',
        'bg-card-hover': 'bg-[rgba(18,28,60,0.98)]',
        'bg-card-active': 'bg-[rgba(130,177,255,0.14)]',
        'bg-sidebar': 'bg-gradient-to-b from-[rgba(255,255,255,0.04)] to-[rgba(255,255,255,0.02)]',
        'bg-input': 'bg-[rgba(0,0,0,0.25)]',
        'bg-code': 'bg-[rgba(0,0,0,0.35)]',
        'bg-placeholder': 'bg-[rgba(0,0,0,0.18)]',
        // 按钮
        btn: 'h-34px px-3 rounded-10px border-1 border-solid border-[rgba(255,255,255,0.14)] bg-[rgba(255,255,255,0.06)] text-body cursor-pointer outline-none',
        'btn-hover': 'hover:bg-[rgba(255,255,255,0.09)]',
        'btn-disabled': 'disabled:opacity-45 disabled:cursor-not-allowed',
        // 过渡
        'transition-card': 'transition-all duration-180 ease-out',
        // 搜索框
        'input-search':
          'w-full h-36px px-3 rounded-10px border-input bg-input text-body outline-none placeholder:text-[rgba(230,232,239,0.55)] focus:border-[rgba(130,177,255,0.55)] focus:ring-3 focus:ring-[rgba(130,177,255,0.14)]',
        // 徽章
        badge:
          'flex-shrink-0 text-11px font-650 tracking-[0.2px] px-2 py-[3px] rounded-999px border-1 border-solid border-[rgba(130,177,255,0.35)] text-[rgba(200,218,255,0.95)] bg-[rgba(130,177,255,0.12)]',
        // 列表项
        'list-item':
          'w-full text-left p-[10px] rounded-12px border-1 border-transparent bg-transparent text-body cursor-pointer grid gap-6px hover:bg-[rgba(255,255,255,0.05)] hover:border-card',
        'list-item-active': 'bg-card-active border-active',
      },
      theme: {
        fontFamily: {
          mono: [
            'ui-monospace',
            'SFMono-Regular',
            'Menlo',
            'Monaco',
            'Consolas',
            'Liberation Mono',
            'Courier New',
            'monospace',
          ],
        },
      },
    }),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  assetsInclude: ['**/*.md'],
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules/three')) {
            return 'three'
          }
        },
      },
    },
  },
})
