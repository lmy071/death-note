# 搜狗输入法右下角广告弹窗封禁 — 操作说明

> 本机（Windows 11 22631）已完成封禁。输入法功能（拼音输入、云候选、词库、皮肤、大模型纠错）全部保留。

## 一、广告是怎么弹出来的（诊断结论）

搜狗的右下角弹窗**不是**输入法本体弹的，而是一条独立的"商业推广"链路：

```
SGBizLauncher.exe  ──每小时读云端配置──▶  biz_helper.exe --type=systoast --subtype=check
                                              │
                                              ├─ 从 wfiles.gtimg.cn 下载网页模板 ZIP
                                              │  （内部路径 build/client/pc-advertising-popup/）
                                              ├─ 写入 C:\ProgramData\SogouInput\SGSysToast\webtpl\
                                              └─ 拉起 libamssdk.dll（腾讯广点通广告 SDK）
                                                     └─ ginkgo.exe 加载落地页 / 上报点击
```

关键点：云端配置 `systoast_general_config_1` 里带 `"ignore_sys_switch": true`、
`"ignore_sglb_switch": true`、`"ignore_user_noactive": true`，
**意味着单纯在设置里关掉"推荐"、或在注册表里打开关，都会被云端覆盖。**
所以只靠注册表是不够的，必须同时掐断网络和组件。

## 二、已实施的四层封禁

| 层 | 措施 | 作用 |
|---|---|---|
| **网络层** | hosts 写入 12 条 `0.0.0.0` 屏蔽（`c.gdt.qq.com`、`rpt.gdt.qq.com`、`v.gdt.qq.com`、`ttc.gdt.qq.com`、`sdkreport.e.qq.com`、`adsmind.gdtimg.com`、`pgdt.gtimg.cn`、`wfiles.gtimg.cn`、`rdelivery.qq.com`、`t.rdelivery.qq.com`、`galileotelemetry.tencent.com`） | 广告素材/模板/上报全部断网，弹窗无内容可渲染 |
| **缓存层** | 清空 `SGSysToast\webtpl`、`config`、`amsad`、`image`、`imepop`，并 deny `BUILTIN\Users` 写入 | 已有的广告模板立即失效，且无法再写入新模板 |
| **组件层** | ACL deny `Everyone` 执行/读取 `ginkgo.exe`（广点通落地页）、`libamssdk.dll`（腾讯广告 SDK） | 广告 SDK 无法加载，即使拿到模板也渲染不出来 |
| **任务层** | 从 `SGBizConfig` 云端任务表 `hourtask_1`/`hourtask_2` 中删除 3 条 `systoast`/`imestatuspop` 任务，并把 `systoast_*` 三个配置行的开关位置 0 | 每小时的弹窗调度不再触发 |
| **服务层** | `SogouSvc` 设为禁用（原为手动启动，当前本就 Stopped） | 阻断 `tk.cpop.elevate.show`（提权弹窗）通道 |

### 特意**没有**动的东西

- `ime.gtimg.com` — 该域同时承载输入法云资源（大模型纠错规则 `large_model_rules_1`、纠错引擎 `fix_engine_1`），封了会影响输入质量，已排除。
- `get.sogou.com` / `sec.sginput.qq.com` — 输入法账号、词库同步、皮肤等功能域。
- `biz_render.exe` / `biz_notify.exe` — 被搜狗智能助手、IChat 等正常组件复用，日志中从未用于弹窗，封了会误伤功能。
- 任何输入法本体文件（`SogouTSF.ime`、`ImeFunc.dll`、`UIPlugin.dll` 等）— 完全未改动。

## 三、验证结果

- hosts 12 条广告域全部解析为 `0.0.0.0`，`ime.gtimg.com` 仍正常解析到 `175.43.203.60`。
- 手动触发一次 `biz_helper.exe --type=systoast --subtype=check`：`webtpl` / `config` 写入后仍为 **0 个文件**，无 `biz_helper`/`ginkgo`/`biz_render` 进程残留，日志出现 `tk.s6`（模板下载/解析失败），弹窗链路在第一步即被掐断。
- 输入法进程 `SGTool`、`SogouCloud`、`SogouImeBroker` 全部正常运行，TSF 注册项 `{E7EA138E-...}` → `C:\Windows\system32\SogouTSF.ime` 完好。
- 云端配置 DB `pragma integrity_check` = `ok`，`hourtask_2` 剩余 7 条任务，均不含 `systoast`/`imestatuspop`。

## 四、日常维护

```powershell
# 查看当前封禁状态
powershell -ExecutionPolicy Bypass -File .\sogou-adblock.ps1 -Status

# 搜狗升级后重新应用（幂等，可反复跑）
powershell -ExecutionPolicy Bypass -File .\sogou-adblock.ps1

# 如需彻底还原
powershell -ExecutionPolicy Bypass -File .\sogou-adblock.ps1 -Revert
```

**重要**：搜狗升级/重装会覆盖 `Components\biz_center\<新版本号>` 目录（版本号变化后 ACL 封锁失效），
并且可能重写 `SGBizConfig` 里的任务表。**每次搜狗升级后重新运行一次脚本即可。**

## 五、备份与回滚

`backup\` 目录下已保存改动前的原始状态：

| 文件 | 内容 |
|---|---|
| `hosts.bak` | 原始 hosts（1037 字节，含原有 8 条 adware 屏蔽） |
| `SGSysToast\` | 原始广告模板缓存（21 个文件，1.48 MB） |
| `SGBizConfig_active.db` | 改动前的云端配置 DB |
| `SogouInput.reg`、`SogouInput.ppup.reg`、`SogouInput.store.user.reg`、`SogouInput.user.reg` | 原始注册表快照 |
| `acl-libamssdk.txt`、`acl-ginkgo.txt` | 改动前的原始 ACL |

## 六、若仍偶发弹窗

1. 先跑 `-Status`，看 `[2] 广告模板缓存` 是否又出现文件（说明 ACL 被重置）。
2. 重新跑一次主脚本。
3. 若弹窗换了新域名，用 `Get-Content <systoast.log> -Tail 50` 看新出现的 URL，把新域名补进脚本里的 `$AdDomains` 数组。
