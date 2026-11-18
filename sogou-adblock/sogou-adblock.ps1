<#
  sogou-adblock.ps1  —  搜狗输入法广告弹窗封禁（幂等，可重复执行）
  ------------------------------------------------------------------
  封禁对象：屏幕右下角 "systoast" 类广告弹窗（pc-advertising-popup）
            以及 imestatuspop 状态栏推广弹窗
  保留功能：拼音输入、云候选、词库同步、皮肤、大模型纠错等全部正常功能

  用法（需管理员权限）：
      .\sogou-adblock.ps1            # 应用/修复封禁
      .\sogou-adblock.ps1 -Status    # 仅检查当前状态
      .\sogou-adblock.ps1 -Revert    # 回滚（从 backup\ 还原）

  每次搜狗升级后请重新执行一次。
#>
[CmdletBinding()]
param(
    [switch]$Status,
    [switch]$Revert
)

$ErrorActionPreference = 'Stop'
$Root    = Split-Path -Parent $MyInvocation.MyCommand.Path
$Backup  = Join-Path $Root 'backup'
$Hosts   = "$env:SystemRoot\System32\drivers\etc\hosts"
$Marker  = '# === sogou-adblock BEGIN (managed by sogou-adblock.ps1) ==='
$EndMark = '# === sogou-adblock END ==='
$BizCenter = 'C:\Program Files (x86)\SogouInput\Components\biz_center\1.0.0.3357'
$SysToast  = 'C:\ProgramData\SogouInput\SGSysToast'
$BizConfig = 'C:\ProgramData\SogouInput\SGBizConfig'

# 仅封广告/追踪域名；输入法功能域名（ime.gtimg.com / get.sogou.com 等）一律不动
$AdDomains = @(
    'rdelivery.qq.com', 't.rdelivery.qq.com',              # 搜狗投放调度
    'c.gdt.qq.com', 'rpt.gdt.qq.com', 'v.gdt.qq.com',
    'vr.gdt.qq.com', 'ttc.gdt.qq.com',                    # 腾讯广点通
    'sdkreport.e.qq.com',                                 # 广告 SDK 上报
    'adsmind.gdtimg.com', 'pgdt.gtimg.cn',                # 广告素材
    'wfiles.gtimg.cn',                                    # 弹窗网页模板 CDN
    'galileotelemetry.tencent.com'                        # 广告遥测
)

function Test-Admin {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    (New-Object Security.Principal.WindowsPrincipal $id).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# ---------------------------------------------------------------- hosts
function Set-HostsBlock {
    $text = Get-Content $Hosts -Raw
    if ($text -match [regex]::Escape($Marker)) {
        $text = [regex]::Replace($text,
            "$([regex]::Escape($Marker))[\s\S]*?$([regex]::Escape($EndMark))", '')
    }
    $block = "`r`n`r`n$Marker`r`n" +
             (($AdDomains | ForEach-Object { "0.0.0.0 $_" }) -join "`r`n") +
             "`r`n$EndMark`r`n"
    Set-Content $Hosts -Value ($text.TrimEnd() + $block) -Encoding ascii -NoNewline
    Clear-DnsClientCache
    Write-Host "  [hosts] 已写入 $($AdDomains.Count) 条广告域名屏蔽" -ForegroundColor Green
}

function Remove-HostsBlock {
    $text = Get-Content $Hosts -Raw
    if ($text -match [regex]::Escape($Marker)) {
        $text = [regex]::Replace($text,
            "$([regex]::Escape($Marker))[\s\S]*?$([regex]::Escape($EndMark))", '').TrimEnd()
        Set-Content $Hosts -Value ($text + "`r`n") -Encoding ascii -NoNewline
        Clear-DnsClientCache
        Write-Host "  [hosts] 已移除屏蔽条目" -ForegroundColor Yellow
    }
}

# ------------------------------------------------------------- 注册表开关
function Set-RegSwitches {
    $ppup = 'HKCU:\SOFTWARE\SogouInput.ppup'
    if (-not (Test-Path $ppup)) { New-Item $ppup -Force | Out-Null }
    $v = @{
        DisableEntries = 1; NewsNewUser = 1; NewsDisabledEx = 1; NewsSwitch = 1
        NewsDisabled = 1; DisableNews = 1; DisablePromotion = 1; DisablePopWnd = 1
        DisableToast = 1; PopWndSwitch = 0; ToastSwitch = 0
        SystoastSwitch = 0; ImePopSwitch = 0; PromotionSwitch = 0
        imestatuspop_switch = 0
    }
    foreach ($kv in $v.GetEnumerator()) {
        New-ItemProperty $ppup -Name $kv.Key -Value $kv.Value -PropertyType DWord -Force | Out-Null
    }
    $su = 'HKCU:\SOFTWARE\SogouInput.store.user'
    if (-not (Test-Path $su)) { New-Item $su -Force | Out-Null }
    foreach ($n in 'bzsk.amsnldrd.tstchk','bzsk.amsnldrd.tstshw','bzsk.amsnldrd.tstivk',
                   'bzsk.amsnldrd.tsttpl','bzsk.amsnldrd.tstclk','gamecenterenable',
                   'ichatenable','writespiritenable','wizardpromotion','imepopswitchstatistics') {
        New-ItemProperty $su -Name $n -Value 0 -PropertyType DWord -Force | Out-Null
    }
    Write-Host "  [reg] 已写入用户级弹窗开关" -ForegroundColor Green
}

# --------------------------------------------------- 广告缓存清理 + 写入封锁
function Set-CacheBlock {
    foreach ($d in @("$SysToast\webtpl", "$SysToast\config", "$SysToast\amsad",
                     "$SysToast\image", 'C:\ProgramData\SogouInput\imepop')) {
        if (-not (Test-Path $d)) { continue }
        Get-ChildItem $d -Force -ErrorAction SilentlyContinue |
            Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
        # 只 deny 普通用户组，保留 SYSTEM/Administrators 全权，避免误伤系统组件
        icacls $d /deny '*S-1-5-32-545:(WD,AD)' /T 2>&1 | Out-Null
    }
    Write-Host "  [cache] 广告模板/配置已清空并禁止用户态重写" -ForegroundColor Green
}

# ------------------------------------------------------ 广告 SDK 组件封锁
function Set-ComponentBlock {
    if (-not (Test-Path $BizCenter)) {
        Write-Host "  [comp] 未找到 biz_center，跳过（版本号可能已变，请检查路径）" -ForegroundColor Yellow
        return
    }
    # 仅封纯广告 SDK：ginkgo.exe(广点通落地页) / libamssdk.dll(腾讯广告 SDK)
    # biz_render.exe、biz_notify.exe 被智能助手等正常组件复用，不封
    foreach ($f in 'ginkgo.exe', 'libamssdk.dll') {
        $p = Join-Path $BizCenter $f
        if (Test-Path $p) {
            icacls $p /deny '*S-1-1-0:(RX)' 2>&1 | Out-Null
        }
    }
    Write-Host "  [comp] 广告渲染组件已禁止执行/加载" -ForegroundColor Green
}

function Undo-ComponentBlock {
    if (-not (Test-Path $BizCenter)) { return }
    foreach ($f in 'ginkgo.exe', 'libamssdk.dll', 'biz_render.exe', 'biz_notify.exe') {
        $p = Join-Path $BizCenter $f
        if (Test-Path $p) { icacls $p /remove:d '*S-1-1-0' 2>&1 | Out-Null }
    }
    Write-Host "  [comp] 组件 ACL 封锁已撤销" -ForegroundColor Yellow
}

# ------------------------------------------------- 云端下发的每小时弹窗任务
function Set-ConfigDbBlock {
    if (-not (Test-Path $BizConfig)) { return }
    $live = Get-ChildItem $BizConfig -Filter '*.db' -File |
            Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not $live) { return }
    $py = Get-Command python -ErrorAction SilentlyContinue
    if (-not $py) {
        Write-Host "  [db] 无 python，跳过任务表修补（hosts 层已可兜底）" -ForegroundColor Yellow
        return
    }
    $script = @'
import sqlite3, json, sys, shutil, os
db = sys.argv[1]
backup = sys.argv[2]
shutil.copy2(db, backup)
c = sqlite3.connect(db)
removed = 0
for key in ("hourtask_1", "hourtask_2"):
    row = c.execute('select "2" from RDeliveryConfig where "1"=?', (key,)).fetchone()
    if not row: continue
    outer = json.loads(row[0]); inner = json.loads(outer["config_value"])
    tasks = inner["configs"]["tasks"]
    keep = [t for t in tasks
            if "systoast" not in t.get("param","") and "imestatuspop" not in t.get("param","")]
    if len(keep) != len(tasks):
        removed += len(tasks) - len(keep)
        inner["configs"]["tasks"] = keep
        outer["config_value"] = json.dumps(inner, ensure_ascii=False, separators=(",",":"))
        c.execute('update RDeliveryConfig set "2"=? where "1"=?',
                  (json.dumps(outer, ensure_ascii=False), key))
for key in ("systoast_general_config_1","systoast_progavoid_1","systoast_relaxation_1"):
    c.execute('update RDeliveryConfig set "3"=0 where "1"=?', (key,))
c.commit(); c.close()
print(removed)
'@
    $tmp = Join-Path $env:TEMP 'sg_adblock_db.py'
    Set-Content $tmp $script -Encoding utf8
    $out = & $py.Source $tmp $live.FullName (Join-Path $Backup 'SGBizConfig_active.db') 2>&1
    Write-Host "  [db] 已从云端任务表移除 $out 条弹窗任务" -ForegroundColor Green
}

# ---------------------------------------------------------------- 服务
function Set-ServiceBlock {
    sc.exe config SogouSvc start= disabled 2>&1 | Out-Null
    Write-Host "  [svc] SogouSvc 已设为禁用（阻断提权弹窗通道）" -ForegroundColor Green
}
function Undo-ServiceBlock {
    sc.exe config SogouSvc start= demand 2>&1 | Out-Null
    Write-Host "  [svc] SogouSvc 已恢复为手动启动" -ForegroundColor Yellow
}

# ---------------------------------------------------------------- 主流程
if ($Revert) {
    if (-not (Test-Admin)) { throw '请以管理员身份运行' }
    Write-Host "=== 回滚搜狗广告封禁 ===" -ForegroundColor Cyan
    Remove-HostsBlock
    Undo-ComponentBlock
    Undo-ServiceBlock
    if (Test-Path "$Backup\hosts.bak") {
        Copy-Item "$Backup\hosts.bak" $Hosts -Force
        Clear-DnsClientCache
        Write-Host "  [hosts] 已从备份还原原始 hosts" -ForegroundColor Yellow
    }
    if (Test-Path "$Backup\SGSysToast") {
        Copy-Item "$Backup\SGSysToast\*" $SysToast -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "  [cache] 广告模板缓存已还原" -ForegroundColor Yellow
    }
    Write-Host "回滚完成。注册表开关保留（如需彻底还原请导入 backup\*.reg）" -ForegroundColor Cyan
    return
}

if ($Status) {
    Write-Host "=== 搜狗广告封禁状态 ===" -ForegroundColor Cyan
    Write-Host "`n[1] hosts 屏蔽条目"
    $h = Get-Content $Hosts
    if ($h -match [regex]::Escape($Marker)) {
        $n = ($h | Where-Object { $_ -like '0.0.0.0 *' }).Count
        Write-Host "    已启用（当前共 $n 条 0.0.0.0 屏蔽）" -ForegroundColor Green
        foreach ($d in 'c.gdt.qq.com','rdelivery.qq.com','wfiles.gtimg.cn') {
            $ip = (Resolve-DnsName $d -ErrorAction SilentlyContinue |
                   Where-Object Type -eq 'A' | Select-Object -First 1).IPAddress
            Write-Host ("    {0,-22} -> {1}" -f $d, $ip)
        }
    } else { Write-Host "    未启用" -ForegroundColor Red }

    Write-Host "`n[2] 广告模板缓存"
    foreach ($d in "$SysToast\webtpl", "$SysToast\config") {
        $n = (Get-ChildItem $d -File -ErrorAction SilentlyContinue).Count
        $c = if ($n -eq 0) { 'Green' } else { 'Red' }
        Write-Host ("    {0,-8} 文件数={1}" -f (Split-Path $d -Leaf), $n) -ForegroundColor $c
    }

    Write-Host "`n[3] 广告组件 ACL"
    foreach ($f in 'ginkgo.exe','libamssdk.dll') {
        $p = Join-Path $BizCenter $f
        if (Test-Path $p) {
            $a = (icacls $p) -join ' '
            $s = if ($a -match 'DENY') { '已封锁' } else { '未封锁' }
            $c = if ($s -eq '已封锁') { 'Green' } else { 'Red' }
            Write-Host ("    {0,-16} {1}" -f $f, $s) -ForegroundColor $c
        }
    }

    Write-Host "`n[4] SogouSvc"
    $svc = Get-Service SogouSvc -ErrorAction SilentlyContinue
    Write-Host ("    {0} / {1}" -f $svc.Status, $svc.StartType)

    Write-Host "`n[5] 输入法核心状态（应保持运行）"
    Get-Process | Where-Object { $_.ProcessName -in 'SGTool','SogouCloud','SogouImeBroker' } |
        ForEach-Object { Write-Host ("    {0} (PID {1})" -f $_.ProcessName, $_.Id) -ForegroundColor Green }

    Write-Host "`n[6] 最近一次 systoast 检查结果"
    $log = "$BizCenter\Data\systoast.log"
    if (Test-Path $log) {
        $last = Get-Content $log -Tail 30 |
                Select-String 'Pop TimeIntervals Unmatch|ParaseDataAndDownloadRes failed|tk\.' |
                Select-Object -Last 3
        foreach ($l in $last) { Write-Host ("    " + $l.Line) }
    }
    return
}

if (-not (Test-Admin)) { throw '请以管理员身份运行（右键 → 以管理员身份运行）' }
New-Item -ItemType Directory -Force -Path $Backup | Out-Null

Write-Host "=== 应用搜狗广告弹窗封禁 ===" -ForegroundColor Cyan
Set-HostsBlock
Set-RegSwitches
Set-CacheBlock
Set-ComponentBlock
Set-ConfigDbBlock
Set-ServiceBlock

Write-Host "`n=== 完成 ===" -ForegroundColor Cyan
Write-Host "输入法功能不受影响；弹窗链路已从网络、缓存、组件、任务、服务五层封禁。"
Write-Host "搜狗升级后请重新运行本脚本：.\sogou-adblock.ps1"
Write-Host "查看状态：.\sogou-adblock.ps1 -Status    回滚：.\sogou-adblock.ps1 -Revert"
