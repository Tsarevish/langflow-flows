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

New-Item -ItemType Directory -Path $Target -Force | Out-Null
# Update packaged files without deleting user profiles or credentials.
$sourceRoot = [IO.Path]::GetFullPath($source).TrimEnd('\')
$targetRoot = [IO.Path]::GetFullPath($Target).TrimEnd('\')
if ($targetRoot -eq $sourceRoot -or $targetRoot.StartsWith($sourceRoot + '\', [StringComparison]::OrdinalIgnoreCase)) {
    throw "Target must be outside the source skill directory"
}
$items = @(Get-ChildItem -LiteralPath $sourceRoot -Recurse -File)
foreach ($item in $items) {
    $relative = $item.FullName.Substring($sourceRoot.Length + 1)
    if ($relative -match '(^|\\)(__pycache__|\.git)(\\|$)' -or $item.Extension -eq '.pyc') { continue }
    if ($relative.StartsWith('profiles\') -and -not $relative.StartsWith('profiles\_template\')) { continue }
    if ($relative -notmatch '^(SKILL\.md|README\.md|VERIFICATION\.md|NOTICE\.md|LICENSE)$|^(references|examples|scripts|tests|profiles)\\') { continue }
    $destination = Join-Path $targetRoot $relative
    New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force | Out-Null
    Copy-Item -LiteralPath $item.FullName -Destination $destination -Force
}

$files = (Get-ChildItem $Target -Recurse -File | Measure-Object).Count
$kb = [math]::Round((Get-ChildItem $Target -Recurse -File | Measure-Object Length -Sum).Sum / 1KB)
Write-Host "installed: $Target ($files files, $kb KB)"
Write-Host "check: call the skill tool with name 'langflow-flows'"
