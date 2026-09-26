param(
    [string]$DarktidePath = "",
    [string]$Branch = "depths-preview-mod"
)

$ErrorActionPreference = "Stop"
$Owner = "a1615439938-collab"
$Repo = "Darktide-BD"
$Prefix = "game-mod/DepthsPreview"

$Files = @(
    "DepthsPreview.mod",
    "README.md",
    "info.json",
    "scripts/mods/DepthsPreview/DepthsPreview.lua",
    "scripts/mods/DepthsPreview/DepthsPreview_data.lua",
    "scripts/mods/DepthsPreview/DepthsPreview_localization.lua",
    "scripts/mods/DepthsPreview/balance_preview.lua",
    "scripts/mods/DepthsPreview/blessing_preview.lua",
    "scripts/mods/DepthsPreview/compatibility.lua",
    "scripts/mods/DepthsPreview/official_preview_spec.lua",
    "scripts/mods/DepthsPreview/preview_equipment.lua",
    "scripts/mods/DepthsPreview/preview_state.lua",
    "scripts/mods/DepthsPreview/preview_talent_ui.lua",
    "scripts/mods/DepthsPreview/preview_trees.lua",
    "scripts/mods/DepthsPreview/runtime_preview.lua",
    "scripts/mods/DepthsPreview/talent_balance_preview.lua"
)

function Test-DarktidePath([string]$Path) {
    if ([string]::IsNullOrWhiteSpace($Path)) { return $false }
    return (Test-Path (Join-Path $Path "binaries")) -and
           ((Test-Path (Join-Path $Path "bundle")) -or
            (Test-Path (Join-Path $Path "mods")))
}

function Get-SteamLibraries {
    $libraries = New-Object System.Collections.Generic.List[string]

    $steamPath = ""
    try {
        $steamPath = (Get-ItemProperty -Path "HKCU:\Software\Valve\Steam" -Name SteamPath -ErrorAction Stop).SteamPath
    } catch {}

    if ($steamPath) {
        $libraries.Add(($steamPath -replace "/", "\"))
        $vdf = Join-Path $steamPath "steamapps\libraryfolders.vdf"
        if (Test-Path $vdf) {
            foreach ($line in Get-Content $vdf -ErrorAction SilentlyContinue) {
                if ($line -match '"path"\s+"([^"]+)"') {
                    $candidate = $matches[1] -replace '\\\\', '\'
                    if (-not $libraries.Contains($candidate)) {
                        $libraries.Add($candidate)
                    }
                }
            }
        }
    }

    return $libraries
}

if (-not (Test-DarktidePath $DarktidePath)) {
    foreach ($library in Get-SteamLibraries) {
        $candidate = Join-Path $library "steamapps\common\Warhammer 40,000 DARKTIDE"
        if (Test-DarktidePath $candidate) {
            $DarktidePath = $candidate
            break
        }
    }
}

if (-not (Test-DarktidePath $DarktidePath)) {
    Write-Host ""
    Write-Host "未自动找到 Darktide。请输入游戏根目录，例如：" -ForegroundColor Yellow
    Write-Host "D:\SteamLibrary\steamapps\common\Warhammer 40,000 DARKTIDE"
    $DarktidePath = Read-Host "Darktide 路径"
}

if (-not (Test-DarktidePath $DarktidePath)) {
    throw "路径不像 Darktide 游戏根目录：$DarktidePath"
}

$ModsPath = Join-Path $DarktidePath "mods"
$Destination = Join-Path $ModsPath "DepthsPreview"
New-Item -ItemType Directory -Force -Path $Destination | Out-Null

Write-Host ""
Write-Host "安装 DepthsPreview -> $Destination" -ForegroundColor Cyan

foreach ($Relative in $Files) {
    $Target = Join-Path $Destination ($Relative -replace "/", "\")
    $Parent = Split-Path -Parent $Target
    New-Item -ItemType Directory -Force -Path $Parent | Out-Null

    $EncodedParts = ($Relative -split "/") | ForEach-Object { [Uri]::EscapeDataString($_) }
    $EncodedRelative = $EncodedParts -join "/"
    $Url = "https://raw.githubusercontent.com/$Owner/$Repo/$Branch/$Prefix/$EncodedRelative"

    Write-Host "  下载 $Relative"
    Invoke-WebRequest -Uri $Url -OutFile $Target -UseBasicParsing
}

$LoadOrder = Join-Path $ModsPath "mod_load_order.txt"
if (-not (Test-Path $LoadOrder)) {
    New-Item -ItemType File -Path $LoadOrder -Force | Out-Null
}

$Lines = @(Get-Content $LoadOrder -ErrorAction SilentlyContinue)
if (-not ($Lines | Where-Object { $_.Trim() -eq "DepthsPreview" })) {
    Add-Content -Path $LoadOrder -Value "DepthsPreview"
    Write-Host "已加入 mod_load_order.txt" -ForegroundColor Green
} else {
    Write-Host "mod_load_order.txt 已包含 DepthsPreview" -ForegroundColor Green
}

$Required = @(
    (Join-Path $Destination "DepthsPreview.mod"),
    (Join-Path $Destination "scripts\mods\DepthsPreview\DepthsPreview.lua"),
    (Join-Path $Destination "scripts\mods\DepthsPreview\preview_trees.lua")
)

$Missing = @($Required | Where-Object { -not (Test-Path $_) })
if ($Missing.Count -gt 0) {
    Write-Host "安装后检查失败：" -ForegroundColor Red
    $Missing | ForEach-Object { Write-Host "  缺少 $_" -ForegroundColor Red }
    exit 1
}

Write-Host ""
Write-Host "DepthsPreview 文件安装完成。" -ForegroundColor Green
Write-Host "前置仍需要：Darktide Mod Loader + Darktide Mod Framework。"
Write-Host "实际战斗试玩使用 SoloPlay 或 Realms 本地主机。"
Write-Host ""
Write-Host "进游戏后运行：" -ForegroundColor Cyan
Write-Host "  /depths on"
Write-Host "  /depths selftest"
Write-Host "  /depths open"
