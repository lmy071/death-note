# 谷歌人机验证（reCAPTCHA）判断原理

> 整理时间：2026-11-04
> 关键词：reCAPTCHA v2 / v3 / Enterprise、风险评分、浏览器指纹、行为信号、IP 信誉、token 生命周期

---

## 一、一句话结论

谷歌的"真人验证"（reCAPTCHA）**不是在浏览器里做一次判断，而是一个服务端的风险评分系统**：

- 前端脚本（`api.js`）只负责**采集信号**并换取一个一次性 token；
- 真正的判定发生在 **Google 服务端**，输出一个 `0.0 ~ 1.0` 的分数（以及原因枚举）；
- **是否放行由接入方（网站）自己决定**，Google 只给分，不做强制拦截（v3 / Enterprise 模式）。

所以"它怎么判断"要拆成两层看：**它采集了什么** + **它用什么模型打分**。前者有大量公开线索（官方 API 字段、逆向分析），后者是黑盒。

---

## 二、四种形态，判定方式不同

| 形态 | 交互 | 判定结果 | 说明 |
| --- | --- | --- | --- |
| reCAPTCHA v2（复选框） | 点"我不是机器人" | pass / 弹图像挑战 | 点击时做一次风险分析；风险高则加载 `bframe` 图像挑战 |
| reCAPTCHA v2 Invisible | 无感（由代码触发） | pass / 弹图像挑战 | 同 v2，只是不显示复选框 |
| reCAPTCHA v3 | 完全无感 | 返回分数，永不打断 | 站点自己按阈值决定放行/加验证/拦截 |
| reCAPTCHA Enterprise | 无感 + 可配置挑战 | 分数 + `reasons` + 可选挑战 | 官方文档最全，字段暴露最多，是理解内部逻辑的最佳样本 |
| Google 搜索的"异常流量"页 | 全页拦截 | 必须过验证 | 属于 Google 自身风控（`/sorry/`），以 IP 维度为主，与 reCAPTCHA 是两套东西 |

---

## 三、完整链路：一次验证发生了什么

```
① 页面加载 api.js
      │  采集环境信号（UA、canvas、WebGL、时区、插件…）
      │  写 cookie / localStorage（_GRECAPTCHA、rc::a/b/c…）
      ▼
② 用户触发 execute()（或点击复选框）
      │  打包行为信号 + 环境指纹 → 请求 Google 的 reload/anchor 接口
      ▼
③ Google 服务端打分（机器学习模型 + IP 信誉 + 账号历史 + 站点历史）
      │  返回一次性 token（有效期约 2 分钟）
      ▼
④ 前端把 token 交给自己的后端
      ▼
⑤ 后端调 siteverify / CreateAssessment 校验
      │  返回 success、score、action、challenge_ts、hostname、error-codes
      │  （Enterprise 还返回 reasons、challenge 状态、verified_bots）
      ▼
⑥ 站点按阈值决策：放行 / 加二次验证 / 静默限流 / 拦截
```

几个关键点：

- **token 一次性、约 2 分钟过期**，重复提交会返回 `timeout-or-duplicate`。
- 后端必须校验 `action` 与 `hostname`，否则会出现"低风险页面拿 token 重放到高风险接口"的漏洞。
- **分数是给后端看的，不是给前端看的**——前端拿不到自己的分数（这也是很多自动化工具"看不见自己为什么被拦"的原因）。

---

## 四、它到底看哪些信号

可以分成五层。层与层之间是**加权融合**，不是任何单一信号一票否决。

### 1. 网络层（权重很高，最难伪装）

- **IP 信誉**：住宅 IP / 机房 IP / 公共代理 / Tor 出口；ASN 归属；IP 与声称的地理位置是否一致。
- **流量特征**：同一 IP 或 IP 段的请求频率、并发、访问节奏（是否像人一样有停顿）。
- **TLS / HTTP 指纹**：Enterprise 的 `Event` 里**官方就有 `ja3` 和 `ja4` 字段**（SSL 客户端指纹），说明 TLS 握手特征确实是评分输入之一。同一 UA 却出现与真实浏览器不符的 TLS 指纹，是很强的自动化信号。
- **共享网络被牵连**：公司/学校/公共 WiFi 出口被滥用时，整段 IP 都会被打低分——这正是 Google 帮助页里"您的计算机或网络可能正在发送自动查询"的典型成因。

### 2. 浏览器环境层（指纹）

- User-Agent、Client Hints、语言、时区、屏幕分辨率、设备像素比。
- **一致性校验**：UA 说是 Windows + Chrome，但时区是 UTC、语言是 `en-US`、字体列表是 Linux 容器里的那几套 —— 组合起来就不像真人。
- Canvas / WebGL / AudioContext 指纹（GPU 渲染差异、`SwiftShader` 这类软件渲染器是 headless 的典型特征）。
- 插件列表、`navigator.webdriver`、`window.chrome` 是否存在、`outerWidth/outerHeight` 是否为 0。
- 自动化框架痕迹：CDP 调用残留（`Error.stack` 特征）、事件是否 `isTrusted`、鼠标事件序列是否缺少 `mousemove → mousedown → mouseup → click` 的自然过渡。
- iframe 环境完整性：reCAPTCHA 运行在 Google 域下的 iframe 里，会检测自身是否被"非常规"嵌入或劫持。

### 3. 行为层（v3 的核心卖点）

- 鼠标移动轨迹（速度、加速度、抖动、是否直线插值）、点击位置与目标控件的相对关系。
- 滚动行为（时机、方向、惯性）、触摸/手势事件。
- 键盘节奏：输入间隔、是否有 keydown/keyup 配对、是否粘贴而非输入。
- 页面停留时长、焦点切换（`visibilitychange`、`blur`）、表单填写到提交的时间差。
- 会话内多次 `execute()` 的行为一致性（v3 允许在整页生命周期内多次打分）。

> 注意：**"看鼠标轨迹"只是其中一层**。大量真实用户（纯键盘操作、触屏、辅助技术）本来就没有鼠标轨迹，所以行为层不会单独决定结果。

### 4. 身份与历史层（最容易被忽略，但权重极大）

这是 reCAPTCHA 与"纯指纹方案"最大的区别：**它认识你**。

- **Google 账号 cookie**：登录 Google 的会话（`SID` / `HSID` / `SSID` / `APISID` / `SAPISID`）是最强的"真人"证据；只点一下复选框就通过，通常就是这一层在起作用。
- **`_GRECAPTCHA` cookie**（reCAPTCHA 自己的会话 cookie）与 **localStorage 的 `rc::a` / `rc::b` / `rc::c` / `rc::d-<id>`**：保存历史风险评估结果，跨页面复用。
- **站点级历史**：同一个 sitekey 上，这个 IP / 这个浏览器 / 这个账号过去的行为是"正常通过"还是"被挑战过"，会持续影响后续分数。官方文档明确说"reCAPTCHA 通过观察你站点上的真实流量来学习"，因此**新站、测试环境、刚接入时分数会明显偏离**。
- **跨站数据**：v3 被建议全站埋点，等于在同一 sitekey 覆盖的所有页面持续累积画像。
- Enterprise 还支持传入 `account_id` / `hashed_account_id` / 邮箱 / 手机号，做**关联账号团伙识别**（`RelatedAccountGroup`），把"同一批账号"的风险互相传染。

### 5. 站点上下文层

- `action` 名称是否与后端期望一致（防止 token 重放）。
- `hostname` 是否在允许域名列表内（域名不匹配直接 `invalid-input-response` 类错误）。
- 该 sitekey 的历史流量分布、当前是否正在被攻击（攻击期间阈值会整体收紧）。

---

## 五、服务端能看到的"判断结果"长什么样

### v3 / siteverify 的返回

```json
{
  "success": true,
  "score": 0.7,
  "action": "login",
  "challenge_ts": "2026-11-04T07:20:00Z",
  "hostname": "example.com",
  "error-codes": []
}
```

### Enterprise `Assessment` 的返回（信息量最大）

```json
{
  "tokenProperties": { "valid": true, "hostname": "example.com", "action": "login" },
  "riskAnalysis": {
    "score": 0.3,
    "reasons": ["AUTOMATION", "UNEXPECTED_ENVIRONMENT"],
    "challenge": "FAILED",
    "verifiedBots": []
  }
}
```

`riskAnalysis.reasons` 的官方枚举（直接来自 Google 的 proto 定义，是理解"它在判断什么"最硬的证据）：

| 枚举 | 含义 |
| --- | --- |
| `AUTOMATION` | 交互特征与自动化代理的行为吻合 |
| `UNEXPECTED_ENVIRONMENT` | 事件来自"不合法"的运行环境（非常规浏览器/容器/被篡改环境） |
| `TOO_MUCH_TRAFFIC` | 该事件来源的流量明显高于正常水平 |
| `UNEXPECTED_USAGE_PATTERNS` | 站点上的使用模式与预期显著不同（如正常用户不会走的路径） |
| `LOW_CONFIDENCE_SCORE` | 该站点累计流量太少，模型还不敢下结论 |

另外还有：

- `challenge`：`NOCAPTCHA`（没弹挑战）/ `PASSED` / `FAILED`（挑战答错或"答得可疑"）。
- `verifiedBots`：Google 能**实名识别**的机器人，类型分 `AI_AGENT` / `CONTENT_SCRAPER` / `SEARCH_INDEXER`，并给出名字（如 `google-agent`、`chat-gpt`、`duck-duck-go`、`manus` 等）。也就是说，对已知 AI 爬虫，它不是"猜"，而是**直接标注**。
- `extendedVerdictReasons`：更细的判定原因，仅 Enterprise 高阶套餐可见，且集合会变。

---

## 六、判定为"非人类"之后会发生什么

| 场景 | 表现 |
| --- | --- |
| v2 | 复选框点击后不直接通过，加载 `bframe` 图像挑战（Street View 九宫格等）；连续答错会继续加码 |
| v3 | 什么都不发生——只是分数变低，**由站点决定后果**（很多站点表现为"提交后莫名失败""要求邮箱验证""静默限流"） |
| Enterprise + WAF | 可配置 `REDIRECT` 到挑战页、`BLOCK` 返回错误码、`SUBSTITUTE` 换页面、`SET_HEADER` 交后端处理 |
| Google 搜索 | 整页跳转到 `/sorry/index`，显示"检测到异常流量"，需要过验证才能继续 |

---

## 七、为什么"我明明是真人"却被打低分

按出现频率排序（也是排查顺序）：

1. **机房/代理/VPN IP**，或所在网络出口被大量滥用（最致命，行为再像人也没用）。
2. **无 Google cookie / 隐身模式 / 全新浏览器 profile**：没有任何历史可参考，默认偏保守。
3. **自动化痕迹**：`navigator.webdriver`、headless UA、`SwiftShader`、CDP 残留、事件 `isTrusted === false`。
4. **环境自相矛盾**：UA 与平台、时区、语言、字体、屏幕分辨率对不上。
5. **节奏不像人**：秒级完成表单、无任何中间事件、固定间隔重试。
6. **站点侧问题**：新站流量太少（`LOW_CONFIDENCE_SCORE`）、域名未加白、`action` 不匹配、token 超时或重复使用、超出免费配额（v3 超配额时会**静默返回固定 0.9**，反而掩盖了问题）。
7. **正在被攻击**：站点整体阈值收紧，正常用户被误伤。

---

## 八、几个常见误解

| 误解 | 事实 |
| --- | --- |
| "它在本地判断你是不是机器人" | 本地只采集和打包信号，**判定在 Google 服务端** |
| "主要看鼠标轨迹" | 鼠标只是行为层的一项；**IP 信誉 + 账号/cookie 历史**权重往往更高 |
| "分数是概率" | `score` 是模型输出的风险置信度，未做概率校准，**不同站点、不同时间不可直接比较**；官方建议从 0.5 起步再按自己流量调 |
| "0.9 就一定是真人" | 免费配额耗尽时 v3 会返回静态 0.9；测试环境、新站也会出现系统性偏移 |
| "拿到 token 就等于通过" | token 只是"我做过评估"的凭证，**分数低照样被站点拒绝**；且 token 一次性、约 2 分钟失效 |
| "免费版分数是连续值" | 社区观察：免费档 v3 常见只有 0.1 / 0.3 / 0.7 / 0.9 几档离散值，绑定 Cloud 计费后才是完整区间（**非官方文档，仅供参考**） |
| "它只防爬虫" | 它也用于登录、注册、支付、评论等场景的**分级处置**（低分不一定封禁，而是加验证） |

---

## 九、给接入方的实践建议

1. **阈值分层，不要一刀切**：登录/支付用严格阈值，订阅/评论可放宽；对低分优先"加一道验证"（OTP、邮箱确认、2FA）而不是直接封禁，减少误伤。
2. **按 `action` 分别统计分数分布**，在控制台看真实流量再定阈值，别拍脑袋。
3. **后端三件事必做**：校验 `success`、校验 `action`、校验 `hostname`。
4. **记录分数**（脱敏、按天聚合），否则出问题无法定位是"模型变严"还是"自己的 bug"。
5. **测试环境用官方测试 key**（v2 测试 key 永远返回 `nocaptcha`），或为测试单独建 key；生产/测试 key 必须分开。
6. **不要把 reCAPTCHA 当作唯一防线**：它对"高仿真自动化"并不保证能识别，官方文档自己也承认不保证检测出所有机器人。
7. **注意隐私合规**：reCAPTCHA 会读取终端数据（cookie、指纹、行为），欧盟场景下需评估是否需要前置同意——法国 CNIL 曾因未取得同意部署 reCAPTCHA 而对 Cityscoot 开出罚单（2023，约 12.5 万欧元，与地理位置过度采集合并处罚）。

---

## 十、一句话记忆版

> 谷歌判断"你是不是人"，靠的是**"这个 IP + 这个浏览器 + 这个账号 + 这个行为节奏 + 在这个站点上的历史"**，一起喂给一个服务端模型，输出一个分数；它自己从不拦截，只是把分数交给网站，由网站决定你要不要多点几下红绿灯。

---

## 参考来源

- [reCAPTCHA v3 官方文档（评分、action、siteverify 返回字段）](https://developers.google.cn/recaptcha/docs/v3?hl=en)
- [reCAPTCHA 常见问题（Cookie、配额、测试 key、异常流量页）](https://developers.google.cn/recaptcha/docs/faq?hl=zh-cn)
- [Google Cloud reCAPTCHA Enterprise proto 定义（`ja3`/`ja4`、`reasons` 枚举、`verifiedBots`）](https://raw.githubusercontent.com/googleapis/googleapis/master/google/cloud/recaptchaenterprise/v1/recaptchaenterprise.proto)
- [RiskAnalysis.ClassificationReason 枚举文档](https://docs.cloud.google.com/java/docs/reference/google-cloud-recaptchaenterprise/2.3.1/com.google.recaptchaenterprise.v1.RiskAnalysis.ClassificationReason)
- [Google 搜索"异常流量"帮助页](https://support.google.com/websearch/answer/86640?hl=zh-Hans)
- [reCAPTCHA 版本演进与评分影响因素（TheWebScrapingClub scraping-wiki）](https://raw.githubusercontent.com/TheWebScrapingClub/scraping-wiki/refs/heads/main/entities/recaptcha.md)
- [reCAPTCHA v3 机制综述（CapMonster，含分数档位与阈值实践）](https://capmonster.cloud/zh/blog/recaptcha-v3-googles-invisible-bot-protection-explained/)
- [reCAPTCHA Cookie 与 localStorage 条目说明](https://blog.captchaai.com/recaptcha-cookie-requirements-explained)
- [浏览器自动化与 CAPTCHA 检测信号清单（agent-knowledge）](https://raw.githubusercontent.com/agent-sh/agent-knowledge/main/generic-auth-patterns-captcha-systems.md)
