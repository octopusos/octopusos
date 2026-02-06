Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$root = Resolve-Path (Join-Path $PSScriptRoot '..\..')
$appDir = Join-Path $root 'apps\desktop-client'
$versionFile = Join-Path $root 'VERSION'
$channel = if ($env:OCTOPUSOS_CHANNEL) { $env:OCTOPUSOS_CHANNEL } else { 'stable' }

if (Test-Path $versionFile) {
  $version = (Get-Content $versionFile -Raw).Trim()
} else {
  $version = '0.0.0'
}

Write-Host "octopusos_version=$version"
Write-Host "channel=$channel"

& (Join-Path $appDir 'runtime\build-runtime.ps1')

Set-Location $appDir
if (Get-Command pnpm -ErrorAction SilentlyContinue) {
  pnpm exec tauri build | Out-Host
} elseif (Get-Command npx -ErrorAction SilentlyContinue) {
  npx tauri build | Out-Host
} else {
  throw 'Neither pnpm nor npx found for tauri build'
}

$outDir = Join-Path $root "publish\artifacts\$version\windows"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$msi = Get-ChildItem -Path (Join-Path $appDir 'src-tauri\target\release\bundle\msi') -Filter *.msi -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $msi) {
  throw 'Desktop MSI not found under src-tauri target bundle output'
}

$targetName = "octopusos-desktop-$version-windows-x86_64-$channel.msi"
Copy-Item -Path $msi.FullName -Destination (Join-Path $outDir $targetName) -Force

Write-Host "desktop_artifact=$(Join-Path $outDir $targetName)"
