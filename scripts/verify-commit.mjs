import console from 'node:console'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import process from 'node:process'
import pico from 'picocolors'

const messagePath = path.resolve(process.argv[2] || '.git/COMMIT_EDITMSG')
const message = readFileSync(messagePath, 'utf8').trim()
const commitPattern =
  /^(revert: )?(feat|fix|docs|dx|style|refactor|perf|test|workflow|build|ci|chore|types|wip|release)(\([a-z0-9._-]+\))?!?: .{1,72}$/

if (!commitPattern.test(message.split('\n')[0])) {
  console.error(`\n${pico.white(pico.bgRed(' ERROR '))} ${pico.red('提交信息格式不规范。')}\n`)
  console.error('请使用：<类型>(可选范围): <简短描述>')
  console.error(`例如：${pico.green('feat(editor): add markdown preview')}\n`)
  console.error(
    '允许的类型：feat、fix、docs、dx、style、refactor、perf、test、workflow、build、ci、chore、types、wip、release\n',
  )
  process.exit(1)
}
