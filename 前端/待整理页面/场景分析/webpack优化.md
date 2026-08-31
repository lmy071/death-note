# webpack优化

## 📊 性能分析工具

### 基础分析工具

- **Speed Measure Plugin**: 测量每个loader/plugin耗时
- **Webpack Bundle Analyzer**: 可视化分析包体积和依赖
- **构建统计文件**: `webpack --profile --json=stats.json`

### 安装命令

bash

```
npm install --save-dev speed-measure-webpack-plugin webpack-bundle-analyzer
```

### 配置示例

javascript

```jsx
// 使用Speed Measure Plugin
const SpeedMeasurePlugin = require("speed-measure-webpack-plugin");
const smp = new SpeedMeasurePlugin();
module.exports = smp.wrap(config);

// 使用Bundle Analyzer
const BundleAnalyzerPlugin = require('webpack-bundle-analyzer').BundleAnalyzerPlugin;
plugins: [new BundleAnalyzerPlugin()]
```

## ⚡ 核心优化策略

### 1. 减少解析范围

javascript

```jsx
module.exports = {
  module: {
    rules: [{
      test: /\.js$/,
      exclude: /node_modules/,          // 排除无需处理的目录
      include: path.resolve(__dirname, 'src') // 精确指定处理目录
    }]
  },
  resolve: {
    modules: [path.resolve(__dirname, 'src'), 'node_modules'],
    extensions: ['.js', '.jsx'],        // 明确文件后缀
    alias: { '@': path.resolve(__dirname, 'src') }
  }
};
```

### 2. 缓存机制

**Webpack 5 内置缓存:**

javascript

```
module.exports = {
  cache: {
    type: 'filesystem',
    cacheDirectory: path.resolve(__dirname, 'node_modules/.cache/webpack'),
    buildDependencies: { config: [__filename] }
  }
};
```

**Webpack 4 使用 HardSource:**

javascript

```
const HardSourceWebpackPlugin = require('hard-source-webpack-plugin');
plugins: [new HardSourceWebpackPlugin()]
```

### 3. 多进程构建

javascript

```
// thread-loader配置
module.exports = {
  module: {
    rules: [{
      test: /\.js$/,
      use: [
        { loader: 'thread-loader', options: { workers: 2 } },
        'babel-loader'
      ]
    }]
  },
  optimization: {
    minimizer: [
      new TerserPlugin({ parallel: true }) // 多进程压缩
    ]
  }
};
```

### 4. 代码分割优化

javascript

```jsx
module.exports = {
  optimization: {
    splitChunks: {
      chunks: 'all',
      minSize: 20000,
      cacheGroups: {
        vendors: {
          test: /[\\/]node_modules[\\/]/,
          name: 'vendors',
          priority: -10
        },
        common: {
          minChunks: 2,
          name: 'common',
          priority: -20
        }
      }
    },
    runtimeChunk: { name: 'runtime' } // 提取runtime
  }
};
```

## 🎯 环境特定优化

### 开发环境优化

javascript

```
module.exports = {
  mode: 'development',
  devtool: 'eval-cheap-module-source-map',
  cache: { type: 'memory' },
  optimization: {
    removeAvailableModules: false,
    removeEmptyChunks: false,
    splitChunks: false,
    minimize: false
  }
};
```

### 生产环境优化

javascript

```
module.exports = {
  mode: 'production',
  devtool: false, // 生产环境不需要sourcemap或使用'source-map'
  optimization: {
    minimize: true,
    minimizer: [new TerserPlugin()],
    concatenateModules: true // 模块合并
  }
};
```

## 📈 性能监控方案

### 构建时间监控脚本

javascript

```
// build-time-monitor.js
class BuildTimeMonitor {
  start() { this.startTime = Date.now(); }
  end() {
    const duration = Date.now() - this.startTime;
    console.log(`构建耗时:${duration}ms`);
    if (duration > 60000) this.alertLongBuild(duration);
  }
}
```

### Webpack插件监控

javascript

```
class BuildTimeAnalyzer {
  apply(compiler) {
    compiler.hooks.beforeRun.tap('BuildTimeAnalyzer', () => {
      this.startTime = Date.now();
    });
    compiler.hooks.done.tap('BuildTimeAnalyzer', (stats) => {
      const duration = Date.now() - this.startTime;
      console.log(`总构建时间:${duration}ms`);
    });
  }
}
```

## ✅ 优化检查清单

### 基础优化项

- 使用 `exclude/include` 减少解析范围
- 配置 `resolve.alias` 减少层级查找
- 开启缓存机制（filesystem/memory）
- 使用多进程压缩（TerserPlugin parallel）

### 进阶优化项

- 代码分割（splitChunks）配置优化
- 使用 thread-loader 处理耗时的loader
- 开发环境关闭不必要的优化
- 生产环境启用模块合并

### 大型项目优化项

- 使用 DLL 预编译公共库
- 实施模块联邦（Module Federation）
- 定期进行包体积分析
- 建立构建性能监控体系

## 🚀 快速优化方案

### 紧急优化（立即生效）

1. **开启缓存**: 添加 `cache: { type: 'filesystem' }`
2. **排除node_modules**: `exclude: /node_modules/`
3. **多进程压缩**: `new TerserPlugin({ parallel: true })`

### 中期优化（1-2天）

1. **分析包体积**: 使用 Bundle Analyzer
2. **优化代码分割**: 调整 splitChunks 配置
3. **引入多进程构建**: 添加 thread-loader

### 长期优化（1-2周）

1. **DLL预编译**: 分离第三方库
2. **构建监控**: 建立性能基线
3. **依赖优化**: 清理未使用依赖

## 🔧 常见问题解决

### 构建时间过长

javascript

```
// 解决方案：逐步排查
1. 使用 Speed Measure Plugin 分析耗时
2. 检查是否有大型未压缩资源
3. 减少 loader 处理范围
4. 升级 webpack 和关键 loader 版本
```

### 内存溢出

json

```
// package.json
{
  "scripts": {
    "build": "node --max-old-space-size=4096 node_modules/webpack/bin/webpack.js"
  }
}
```

### 热更新缓慢

javascript

```
// webpack.dev.js
module.exports = {
  devServer: {
    hot: true,
    watchFiles: { paths: ['src/**/*'], ignored: /node_modules/ },
    compress: true
  }
};
```

## 📋 性能基准测试

### 测试脚本

json

```
{
  "scripts": {
    "benchmark": "node scripts/benchmark.js",
    "analyze": "webpack --profile --json=stats.json && webpack-bundle-analyzer stats.json"
  }
}
```

### 关键指标

| 指标 | 优秀 | 需优化 |
| --- | --- | --- |
| 冷构建时间 | < 30s | > 60s |
| 热构建时间 | < 10s | > 20s |
| 包体积 (gzip) | < 2MB | > 5MB |
| 首屏资源数 | < 10个 | > 20个 |

## 🎮 实战命令速查

bash

```
# 分析构建时间
npm run build -- --profile --json=stats.json

# 可视化分析包
npx webpack-bundle-analyzer stats.json

# 查看构建配置
npx webpack-cli inspect

# 清理缓存
rm -rf node_modules/.cache
```

## 📚 最佳实践总结

1. **监控先行**: 先测量，再优化
2. **渐进优化**: 每次只优化1-2项，验证效果
3. **环境区分**: 开发环境重速度，生产环境重体积
4. **定期审查**: 每月进行一次包体积分析
5. **团队同步**: 确保所有成员使用相同的构建配置

---

**优化效果预期:**

- ✅ 缓存机制: 二次构建提速 50-70%
- ✅ 多进程构建: 整体构建提速 30-50%
- ✅ 代码分割: 首屏加载提速 20-40%
- ✅ 开发环境优化: 热更新提速 40-60%

通过系统性的分析和优化，可以将构建时间从几分钟降至几十秒，显著提升开发体验和部署效率。