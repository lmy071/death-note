# Chrome控制台如何具体分析网页性能

## 一、打开 Chrome 性能分析工具

Chrome DevTools 提供了多个性能分析入口，最核心的是 Performance（性能）面板。打开方式：

1. 快捷键：F12 打开 DevTools → 点击 Performance 标签页
2. 右键菜单：右键页面 → 检查 → Performance
3. 菜单路径：Chrome 菜单 → 更多工具 → 开发者工具 → Performance

---

## 二、录制与分析性能数据

### 2.1 开始录制

点击 Performance 面板左上角的圆形录制按钮（●），或在页面加载时勾选 Screenshots 选项可以逐帧截屏。录制时进行你关心的操作（滚动、点击等），完成后点击 Stop 停止录制。

### 2.2 理解火焰图（Flame Chart）

录制完成后，Main 区域会显示主线程的火焰图，从上到下表示调用栈。X 轴代表时间，Y 轴代表调用深度。

- 黄色（Scripting）：JavaScript 执行耗时
- 紫色（Rendering）：样式计算和布局 (Layout/Reflow) 耗时
- 绿色（Painting）：绘制和合成图层耗时
- 灰色（System）：浏览器内部操作
- 蓝色（Loading）：网络请求和 HTML 解析

---

## 三、关键性能指标解读

### 3.1 FPS（帧率）

FPS 图表位于顶部，绿色条越高越好。低于 60 FPS 表示页面有卡顿。红色条表示掉帧严重，用户可感知到不流畅。

### 3.2 CPU 概况

CPU 概览图表展示了不同类型工作的耗时分布。如果某一种颜色占比过高，就是性能瓶颈所在。

### 3.3 Summary 摘要面板

底部的 Summary 面板按耗时从长到短列出所有活动。可以点开看具体哪个函数耗时最长，直接定位瓶颈。

---

## 四、Lighthouse 一键审计

Lighthouse 是 Chrome 内置的自动化审计工具，无需手动录制。

1. DevTools → Lighthouse 标签页
2. 选择 Categories（Performance / Accessibility / Best Practices / SEO）
3. 点击 Generate report → 自动生成评分和优化建议

Lighthouse 会给出 FCP（首次内容渲染）、LCP（最大内容渲染）、TBT（总阻塞时间）、CLS（累计布局偏移）等 Core Web Vitals 的具体数值和优化建议。

---

## 六、Memory 面板排查内存泄漏

如果页面越来越卡，可能是内存泄漏。用 Memory 面板 → Heap Snapshot 拍两张快照对比，按 Shallow Size 排序找异常增长的对象。

> Memory 分析三步法：① 操作前拍快照 → ② 操作后拍快照 → ③ 对比两份快照找差异
> 

---

## 七、Coverage 面板找冗余代码

Cmd+Shift+P → 输入 Coverage → Show Coverage。录制后可看到每个 JS/CSS 文件中未使用的字节比例，红色部分就是可以优化掉的代码。

---

## 八、常见性能问题速查

下面是一些常见性能问题及对应的排查方向：

| 现象 | 排查方向 |
| --- | --- |
| 页面滚动不流畅 | 查看 Rendering → Paint Flashing，检查不必要的大面积重绘 |
| 点击按钮响应慢 | Performance 录制点击操作，找长任务 (>50ms) |
| 首屏加载慢 | Network → 大文件 → Lighthouse 查 LCP/FCP |
| 动画卡顿 | Rendering → FPS Meter，改用 transform/opacity |
| 页面越来越卡 | Memory → Heap Snapshot 对比，找内存泄漏 |

---

## 九、常用快捷面板

- Rendering 面板（Cmd+Shift+P → Rendering）：显示 FPS、Paint Flashing、Layout Shift Regions
- Performance Monitor（Cmd+Shift+P → Performance Monitor）：实时监控 CPU、JS Heap、DOM Nodes
- Console 面板：用 console.time("label") / console.timeEnd("label") 手动计时关键代码段

---

## 十、总结：完整分析流程

1. 先用 Lighthouse 一键审计，拿到 Core Web Vitals 评分
2. 用 Performance 面板录制关键用户操作，看火焰图和 Summary
3. 用 Network 面板分析资源加载瀑布图
4. 用 Coverage 面板检查未使用的 JS/CSS 代码
5. 用 Memory 面板排查内存泄漏
6. 用 Performance Monitor 实时监控运行时指标

---

<aside>
💡 **关键原则：性能优化不是猜出来的，是量出来的。永远先录数据再动手改。**

</aside>