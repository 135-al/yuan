#Requires -Version 5.1
<#
.SYNOPSIS
    task-system 一键推送 GitHub —— 自动挑选可用通道

.DESCRIPTION
    在多条候选通道中挑选真正可用的一条推送到 GitHub。
    判定标准是 git ls-remote 实测成功（非端口探测），
    因为 SNI 阻断场景下 TCP 端口仍可能连通，端口探测会产生假阳性。

.PARAMETER Mode
    auto  —— 自动挑选（默认）
    https —— 强制 HTTPS 443
    ssh   —— 强制 SSH over 443

.PARAMETER User
    GitHub 用户名。省略时以交互方式询问。

.PARAMETER Repo
    仓库名，默认 flask-task-system-testbed

.EXAMPLE
    .\push-to-github.ps1
    .\push-to-github.ps1 -Mode ssh -User alice
#>

[CmdletBinding()]
param(
    [ValidateSet('auto', 'https', 'ssh')]
    [string]$Mode = 'auto',
    [string]$User,
    [string]$Repo = 'flask-task-system-testbed'
)

$ErrorActionPreference = 'Continue'
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

# 让子进程输出的中文在本控制台正确呈现
try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch { }

# ---------------------------------------------------------------- 输出辅助
function Write-Section($text) {
    Write-Host ""
    Write-Host ("=" * 62) -ForegroundColor DarkCyan
    Write-Host "  $text" -ForegroundColor Cyan
    Write-Host ("=" * 62) -ForegroundColor DarkCyan
}
function Write-Ok($text)   { Write-Host "  [OK]   $text" -ForegroundColor Green }
function Write-Bad($text)  { Write-Host "  [FAIL] $text" -ForegroundColor Red }
function Write-Info($text) { Write-Host "  [..]   $text" -ForegroundColor Gray }

# ---------------------------------------------------------------- 带超时的通道实测
<#
    用 git ls-remote 走完整协议栈验证。端口探测不够可靠：
    SNI 阻断时 TCP 三次握手照样成功，只有走到 TLS/应用层才会失败。
#>
function Test-GitChannel {
    param(
        [Parameter(Mandatory)][string]$Label,
        [Parameter(Mandatory)][string]$Url,
        [int]$TimeoutMs = 25000
    )

    Write-Info "正在测试 $Label ..."

    $stdout = [System.IO.Path]::GetTempFileName()
    $stderr = [System.IO.Path]::GetTempFileName()

    try {
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName               = 'git'
        $psi.Arguments              = "ls-remote `"$Url`""
        $psi.UseShellExecute        = $false
        $psi.RedirectStandardOutput = $true
        $psi.RedirectStandardError  = $true
        $psi.CreateNoWindow         = $true
        $psi.WorkingDirectory       = $RepoRoot

        $proc = [System.Diagnostics.Process]::Start($psi)

        if (-not $proc.WaitForExit($TimeoutMs)) {
            Write-Bad "$Label —— 超时 (${TimeoutMs}ms)，判定不可用"
            try { $proc.Kill() } catch { }
            return $false
        }

        $outText = Get-Content $stdout -Raw -ErrorAction SilentlyContinue
        $errText = Get-Content $stderr -Raw -ErrorAction SilentlyContinue

        # 成功与否只看退出码：空仓库没有任何 ref，ls-remote 输出为空属正常，
        # 若在此额外要求"输出非空"，会把明明可用的通道误判为不可用。
        if ($proc.ExitCode -eq 0) {
            Write-Ok "$Label —— 通道可用"
            return $true
        }

        # 网络已抵达 GitHub，失败出在仓库不存在 / 鉴权未配置——这仍算"通道可用"
        if ($errText -match 'denied|Authentication failed|could not read|Repository not found|does not appear to be a git repository') {
            Write-Ok "$Label —— 网络可达"
            if ($errText -match 'not found|could not read') {
                Write-Info "注意：远端仓库返回「不存在」，请确认 GitHub 网页端已创建该仓库"
            }
            return $true
        }

        Write-Bad "$Label —— 不可达"
        if ($errText) {
            $tail = ($errText.Trim() -split "`r?`n" | Select-Object -Last 2) -join ' | '
            Write-Info $tail
        }
        return $false

    } catch {
        Write-Bad "$Label —— 异常: $($_.Exception.Message)"
        return $false
    } finally {
        Remove-Item $stdout, $stderr -Force -ErrorAction SilentlyContinue
    }
}

# ================================================================ 主流程
Clear-Host
Write-Section "task-system 推送助手"

# --- 定位 git ---
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Bad "未检测到 git，请先安装 Git for Windows"
    exit 1
}

Push-Location $RepoRoot
try {
    if (-not (Test-Path '.git')) {
        Write-Bad "当前目录不是 git 仓库: $RepoRoot"
        exit 1
    }

    # --- 用户名 ---
    if (-not $User) {
        Write-Host ""
        $User = (Read-Host "  请输入你的 GitHub 用户名").Trim()
    }
    if (-not $User) {
        Write-Bad "用户名为空，无法继续"
        exit 1
    }
    Write-Info "目标仓库: https://github.com/$User/$Repo"

    # --- 构造候选 ---
    $httpsUrl = "https://github.com/$User/$Repo.git"
    $sshUrl   = "git@github.com:${User}/${Repo}.git"

    $selected = $null
    if ($Mode -eq 'auto') {
        Write-Section "通道探测（每条最多 25 秒，请稍候）"
        if (Test-GitChannel -Label 'HTTPS (github.com:443)' -Url $httpsUrl) {
            $selected = @{ Label = 'HTTPS'; Url = $httpsUrl }
        } elseif (Test-GitChannel -Label 'SSH over 443 (ssh.github.com)' -Url $sshUrl) {
            $selected = @{ Label = 'SSH-443'; Url = $sshUrl }
        }
    } elseif ($Mode -eq 'https') {
        Write-Section "强制 HTTPS 通道"
        if (Test-GitChannel -Label 'HTTPS' -Url $httpsUrl) {
            $selected = @{ Label = 'HTTPS'; Url = $httpsUrl }
        }
    } else {
        Write-Section "强制 SSH over 443 通道"
        if (Test-GitChannel -Label 'SSH-443' -Url $sshUrl) {
            $selected = @{ Label = 'SSH-443'; Url = $sshUrl }
        }
    }

    if (-not $selected) {
        Write-Section "结论"
        Write-Bad "所有候选通道均不可用"
        Write-Host ""
        Write-Host "  建议按顺序排查：" -ForegroundColor Yellow
        Write-Host "   1. 代理软件请开启「系统代理/全局模式」，PAC 模式对命令行无效" -ForegroundColor Gray
        Write-Host "   2. 若 HTTPS 走代理，可执行： git config --global http.proxy http://127.0.0.1:<端口>" -ForegroundColor Gray
        Write-Host "   3. 确认已在 GitHub 网页端创建名为 $Repo 的空仓库" -ForegroundColor Gray
        Write-Host "   4. 仍不通则考虑托管到 Gitee / CNB（国内平台，面试官也点得开）" -ForegroundColor Gray
        Write-Host ""
        exit 2
    }

    # --- 执行推送 ---
    Write-Section "推送（通道：$($selected.Label)）"
    Write-Info "remote url = $($selected.Url)"

    # 清理旧 remote，忽略"不存在"这类报错
    $null = & git remote remove origin 2>&1
    & git remote add origin $selected.Url
    if ($LASTEXITCODE -ne 0) { Write-Bad "remote 设置失败"; exit 1 }

    & git branch -M main
    Write-Host ""
    Write-Host "  正在推送..." -ForegroundColor Cyan
    Write-Host ""

    & git push -u origin main
    $pushCode = $LASTEXITCODE

    Write-Host ""
    if ($pushCode -eq 0) {
        Write-Section "推送成功"
        Write-Host "  仓库地址:  https://github.com/$User/$Repo" -ForegroundColor Green
        Write-Host "  流水线:    https://github.com/$User/$Repo/actions" -ForegroundColor Green
        Write-Host ""
        Write-Host "  下一步：打开 Actions 页，重点看 ui-tests 那个 job" -ForegroundColor Yellow
        Write-Host "          （playwright install --with-deps 需 apt 装依赖，最可能出问题）" -ForegroundColor Gray
        exit 0
    }

    Write-Section "推送失败 (exit $pushCode)"
    Write-Host "  最常见原因：" -ForegroundColor Yellow
    Write-Host "   - 仓库不存在 / 名字不符   -> 到 GitHub 网页确认是否已创建" -ForegroundColor Gray
    Write-Host "   - HTTPS 未用 Token 认证   -> 密码框要填 PAT，不是登录密码" -ForegroundColor Gray
    Write-Host "   - SSH 公钥未添加          -> Settings > SSH and GPG keys，公钥见 ~/.ssh/id_ed25519.pub" -ForegroundColor Gray
    exit $pushCode

} finally {
    Pop-Location
}

Write-Host ""
Read-Host "  按回车键关闭"
