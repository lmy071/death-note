import { mkdir, readdir, readFile, writeFile } from 'node:fs/promises'
import { relative, resolve } from 'node:path'

const distDir = resolve(new URL('../dist/', import.meta.url).pathname.replace(/^\/(.:)/, '$1'))
const serverDir = resolve(distDir, 'server')
const assets = {}

async function collect(directory) {
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const path = resolve(directory, entry.name)
    if (path === serverDir) continue
    if (entry.isDirectory()) await collect(path)
    else assets[`/${relative(distDir, path).replaceAll('\\', '/')}`] = (await readFile(path)).toString('base64')
  }
}

await collect(distDir)
await mkdir(serverDir, { recursive: true })
await writeFile(
  resolve(serverDir, 'index.js'),
  `const assets = ${JSON.stringify(assets)}
const contentTypes = ${JSON.stringify({
    '.css': 'text/css; charset=utf-8',
    '.html': 'text/html; charset=utf-8',
    '.ico': 'image/x-icon',
    '.js': 'text/javascript; charset=utf-8',
    '.json': 'application/json; charset=utf-8',
    '.png': 'image/png',
    '.svg': 'image/svg+xml',
  })}

function decode(value) {
  const binary = atob(value)
  return Uint8Array.from(binary, (character) => character.charCodeAt(0))
}

export default {
  async fetch(request) {
    const pathname = new URL(request.url).pathname
    const assetPath = assets[pathname] ? pathname : '/index.html'
    const extension = assetPath.slice(assetPath.lastIndexOf('.'))
    return new Response(decode(assets[assetPath]), {
      headers: { 'content-type': contentTypes[extension] ?? 'application/octet-stream' },
    })
  },
}\n`,
)
