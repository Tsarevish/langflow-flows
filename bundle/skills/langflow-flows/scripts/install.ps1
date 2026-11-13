# Install or update the skill into the user's DSH skills directory.
#
#   powershell -ExecutionPolicy Bypass -File scripts/install.ps1
#   powershell -ExecutionPolicy Bypass -File scripts/install.ps1 -Target "D:\skills\langflow-flows"
#
# DSH scans <dshHome>/skills for a directory per skill: <name>/SKILL.md.
# Nested **/SKILL.md files are deliberately not discovered, so exactly one
# level is copied. Kept ASCII-only: Windows PowerShell 5.1 reads .ps1 as ANSI
# unless the file has a BOM, and Cyrillic text would break parsing.
param(
    [string]$Target = "$env:USERPROFILE\.dsh\skills\langflow-flows"
)

$ErrorActionPreference = "Stop"
$source = Split-Path -Parent $PSScriptRoot

if (-not (Test-Path (Join-Path $source "SKILL.md"))) {
    throw "SKILL.md not found next to this script: $source"
}

if (Test-Path $Target) {
    Get-ChildItem $Target -Recurse -Directory -Filter "__pycache__" |
        Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item $Target -Recurse -Force
}
New-Item -ItemType Directory -Path $Target -Force | Out-Null
Copy-Item (Join-Path $source "*") $Target -Recurse -Force
Get-ChildItem $Target -Recurse -Directory -Filter "__pycache__" |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

$files = (Get-ChildItem $Target -Recurse -File | Measure-Object).Count
$kb = [math]::Round((Get-ChildItem $Target -Recurse -File | Measure-Object Length -Sum).Sum / 1KB)
Write-Host "installed: $Target ($files files, $kb KB)"
Write-Host "check: call the skill tool with name 'langflow-flows'"
