import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import UnoCSS from '@unocss/vite'
import { presetUno, presetAttributify } from 'unocss'
import path from 'path'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [
    vue(),
    UnoCSS({
      presets: [
        presetUno(),
        presetAttributify()
      ],
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
        'btn': 'h-34px px-3 rounded-10px border-1 border-solid border-[rgba(255,255,255,0.14)] bg-[rgba(255,255,255,0.06)] text-body cursor-pointer outline-none',
        'btn-hover': 'hover:bg-[rgba(255,255,255,0.09)]',
        'btn-disabled': 'disabled:opacity-45 disabled:cursor-not-allowed',
        // 过渡
        'transition-card': 'transition-all duration-180 ease-out',
        // 搜索框
        'input-search': 'w-full h-36px px-3 rounded-10px border-input bg-input text-body outline-none placeholder:text-[rgba(230,232,239,0.55)] focus:border-[rgba(130,177,255,0.55)] focus:ring-3 focus:ring-[rgba(130,177,255,0.14)]',
        // 徽章
        'badge': 'flex-shrink-0 text-11px font-650 tracking-[0.2px] px-2 py-[3px] rounded-999px border-1 border-solid border-[rgba(130,177,255,0.35)] text-[rgba(200,218,255,0.95)] bg-[rgba(130,177,255,0.12)]',
        // 列表项
        'list-item': 'w-full text-left p-[10px] rounded-12px border-1 border-transparent bg-transparent text-body cursor-pointer grid gap-6px hover:bg-[rgba(255,255,255,0.05)] hover:border-card',
        'list-item-active': 'bg-card-active border-active',
      },
      theme: {
        fontFamily: {
          mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'Liberation Mono', 'Courier New', 'monospace'],
        },
      },
      preflights: [
        {
          getCSS: () => `
            * { margin: 0; padding: 0; box-sizing: border-box; }
            #app, #layout {
              font-family: Avenir, Helvetica, Arial, sans-serif;
              -webkit-font-smoothing: antialiased;
              -moz-osx-font-smoothing: grayscale;
              text-align: center;
              color: #2c3e50;
              height: 100vh;
              width: 100vw;
              position: relative;
            }
          `,
        },
      ],
    })
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  assetsInclude: ['**/*.md'],
  build: {
    outDir: 'death-note',
    assetsDir: 'assets',
    rollupOptions: {
      output: {
        manualChunks: {
          three: ['three'],
        },
      },
    },
  }
})
