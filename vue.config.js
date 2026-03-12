const { defineConfig } = require('@vue/cli-service')
const path = require('path')

module.exports = defineConfig({
  transpileDependencies: true,
  chainWebpack: (config) => {
    const leetCodeDir = path.resolve(__dirname, 'src/leetCode')

    // 这些文件只用于“展示源码”，不参与 JS 编译执行
    config.module.rule('js').exclude.add(leetCodeDir)

    // Webpack 5: asset/source 会把文件内容作为 string 导入
    config.module
      .rule('leetCode-source')
      .test(/\.js$/)
      .include.add(leetCodeDir)
      .end()
      .type('asset/source')
  }
})
