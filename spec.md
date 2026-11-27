# 前端开发岗位考试题库生成规范（子代理必读）

## 一、总体目标
为《前端开发岗位考试大纲》生成 **1100 道** 客观题，覆盖全部 10 个考点，最终打包为可导入「考试宝」app 的 Excel 题库文件。

题型与数量（严格）：
- 单项选择题：660 道（每题 2 分）
- 多项选择题：220 道（每题 3 分，多选/错选不得分，漏选得 1 分）
- 判断题：220 道（每题 1 分）

10 个考点 **每个考点恰好 110 道** = 单选 66 + 多选 22 + 判断 22。

## 二、考点清单（来自《前端开发岗位考试大纲》）
大纲原文见 `D:\ProjectCode\death-note\syllabus_extract.txt`（UTF-8，每考点一段）。

| 章号 | 考点 | 知识点范围（必须全部覆盖） |
|---|---|---|
| ch01 | 考点1：HTML与语义化标记 | HTML文档结构、常用标签与标签语义；HTML5语义化标签 header/nav/main/section/article/footer 及无障碍意义；meta、title 元信息；script 的 defer/async、type="module" 延迟执行；HTML5存储、移动端适配；浏览器默认样式、文档解析流程、HTML安全规范 |
| ch02 | 考点2：CSS基础与布局 | 选择器类型、优先级计算与层叠；盒模型与 box-sizing；position 定位与文档流影响；浮动与 BFC；Flexbox 一维布局；Grid 二维布局；水平垂直居中；层叠上下文与 z-index；CSS变量、常用单位、响应式设计；过渡、动画、变换、伪元素 |
| ch03 | 考点3：JavaScript语言核心 | 基本类型与引用类型判断、类型转换；var/let/const、作用域、变量提升、暂时性死区；闭包原理；原型与原型链、继承机制；this 绑定规则、严格模式；数组/字符串/对象常用方法；深浅拷贝、垃圾回收、内存管理 |
| ch04 | 考点4：ES6+与异步编程 | 解构赋值、扩展运算符、箭头函数、Symbol、Set、Map；Promise 三种状态与转换；Promise.all/allSettled/race、async/await；事件循环、宏任务与微任务执行顺序、异步代码输出分析 |
| ch05 | 考点5：DOM、BOM与事件 | DOM 节点查询（getElementById、querySelector 等）与增删改；节点属性和样式操作；BOM 常用对象（window/location/navigator/history）、浏览器存储；事件流三阶段（捕获、目标、冒泡）、addEventListener、事件对象；事件委托机制与性能；表单事件与常见 DOM 场景 |
| ch06 | 考点6：浏览器原理与网络基础 | 输入 URL 到页面渲染完整流程；重排与重绘及其性能影响；同源策略与跨域方案（CORS、代理、JSONP）；浏览器多进程架构、渲染进程多线程模型、Web Worker；渲染引擎（Blink/WebKit/Gecko）与 JS 引擎（V8）区别；浏览器存储机制、HTTP 缓存原理；TCP/UDP、TCP 三次握手、DNS 解析、HTTPS 的 TLS/SSL |
| ch07 | 考点7：HTTP与数据交互 | HTTP/HTTPS 协议基础、HTTP/2 多路复用；请求方法语义与状态码分类；强缓存与协商缓存及请求/响应头；Cookie、Token、JWT 鉴权；Fetch API、axios；RESTful 接口约定、异常处理 |
| ch08 | 考点8：Vue框架 | Vue2 与 Vue3 响应式原理核心差异；Composition API（ref、shallowRef、reactive、computed、watch）；生命周期、异步更新队列；组件基础与组件通信、自定义指令、动态组件、内置组件；状态管理；Vue Router 路由传参与导航守卫；虚拟 DOM 与 Diff 算法 |
| ch10 | 考点10：前端工程化、构建与性能优化 | ESModule 模块化规范、前端路由原理；Webpack（Loader、Plugin、HMR、代码分割、缓存优化、模式配置）；Vite 基本原理与开发构建流程；TypeScript 基础；首屏加载优化、懒加载、CDN、防抖节流；FCP、LCP 等性能指标 |
| ch11 | 考点11：前端安全与跨端技术 | XSS、CSRF 原理与防御；内容安全策略 CSP、存储安全；SSR/SSG 渲染模式；微前端核心概念与主子应用通信；PWA、小程序等跨端方案；按项目场景选择合适的前端架构 |

## 三、输出文件（每考点 4 个 JSON 文件）
输出目录：`D:\ProjectCode\death-note\questions\`（已存在）

- `chXX_single_a.json`：单选前 33 题
- `chXX_single_b.json`：单选后 33 题
- `chXX_multi.json`：多选 22 题
- `chXX_judge.json`：判断 22 题

（XX 为章节号：01,02,03,04,05,06,07,08,10,11）

每个文件是**一个 JSON 数组**，每道题一个对象，字段：

```json
{
  "chapter": "考点1：HTML与语义化标记",
  "type": "single",
  "question": "题干文字……",
  "options": ["选项A内容", "选项B内容", "选项C内容", "选项D内容"],
  "answer": "A",
  "analysis": "解析文字（说明正确选项为何正确、干扰项错在哪）",
  "difficulty": 3,
  "tag": "语义化标签"
}
```

字段规则：
- `type` 取值：`"single"`（单选）、`"multiple"`（多选）、`"judge"`（判断）。
- 单选：`options` 恰好 4 项；`answer` 为单个大写字母 A/B/C/D，且必须与正确选项一致。
- 多选：`options` 恰好 4 项；`answer` 为 **2～3 个大写字母**（如 "AB"、"BCD"），不含空格、逗号，字母按 A→D 升序排列；**禁止 4 个全选**（考试宝要求多选答案必须少于选项数）。
- 判断：`options` 固定为 `["正确", "错误"]`；`answer` 只能为 `"A"`（正确）或 `"B"`（错误）。
- `difficulty`：1=简单、2=较简单、3=中等、4=较难、5=困难。整章题目难度分布要拉开（简单~较难都有，中等偏多）。
- `tag`：该题知识点的关键词（2~6 字），如 "语义化标签"、"闭包"、"Promise"。
- `analysis`：必须写实质解析（2~4 句中文），说明依据，不能敷衍或留空。

## 四、出题质量要求
1. **答案必须准确无误**：以主流前端技术事实为准（HTML5/CSS3/ES6+/Vue3/Webpack5/Vite 等现代标准），这是本任务的生命线。凡涉及具体数值、API 行为、执行顺序的题目，务必核实后出题。
2. 内容严格贴合大纲各考点；题干与选项使用专业、清晰的表述。
3. 单选/多选的干扰项要"像真的"（似是而非），避免明显荒谬导致送分；避免选项中出现"以上都对/以上都错/不确定"。
4. 题干不含答案暗示；同一章内题目不得重复或变相重复（换个数字/标签不算）。
5. 判断题对错比例大致均衡（约一半 A 一半 B），不要全部一个答案。
6. 单选答案 A/B/C/D 分布大致均匀。
7. 题干、选项、解析一律用中文；代码、标签名、属性名、API 名保留英文原样。
8. JSON 必须合法：双引号字符串，中文引号「“”」不影响，但代码块中的英文双引号需转义为 `\"`；文件用 UTF-8 编码保存，**不要 BOM**。
9. 出题风格贴近前端岗位笔试/面试题（概念辨析、代码结果、原理理解、场景应用）。

## 五、自校验（写完文件后必须执行）
用以下命令校验自己的 4 个文件（Python 路径固定）：

```
C:\Users\Administrator\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe
```

脚本要点（用自己的章节号替换 XX）：
```python
import json
for f in ['single_a','single_b','multi','judge']:
    data = json.load(open(rf'D:\ProjectCode\death-note\questions\chXX_{f}.json', encoding='utf-8'))
    assert isinstance(data, list) and len(data) == (33 if f.startswith('single') else 22)
    for q in data:
        assert q['type'] == ('single' if f.startswith('single') else (f.split('_')[0])), f
        assert len(q['options']) == (4 if q['type'] != 'judge' else 2)
        letters = [chr(65+i) for i in range(len(q['options']))]
        if q['type'] == 'single':
            assert q['answer'] in letters
        elif q['type'] == 'multiple':
            assert set(q['answer']) <= set(letters) and 2 <= len(q['answer']) <= 3
        else:
            assert q['answer'] in ('A','B')
        assert q['question'] and q['analysis'] and 1 <= q['difficulty'] <= 5
print('OK, total', sum(...))
```

运行通过后，请在最终回复中报告：各文件题数、单选答案分布（A/B/C/D 各多少）、判断题 A/B 比例、难度分布。

## 六、禁止事项
- 不要改动 `syllabus_extract.txt`、`spec.md` 及他人输出目录下的文件。
- 不要生成除上述 4 个文件以外的其他文件（脚本直接在命令行用 python -c 或临时文件运行，用完删除）。
- 不要编造大纲中没有的考点整体（可在考点内细分子知识点）。