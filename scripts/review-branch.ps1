param(
    [Parameter(Mandatory = $true)]
    [string]$SourceBranch,

    [Parameter(Mandatory = $true)]
    [string]$TargetBranch,

    [int]$Unified = 3,

    [switch]$NoFetch
)

$ErrorActionPreference = "Stop"

function Write-Section {
    param([string]$Title)
    Write-Output ""
    Write-Output "### $Title"
}

if (-not $NoFetch) {
    git fetch origin | Out-Null
}

$mergeBase = git merge-base $TargetBranch $SourceBranch

Write-Section "Review Context"
Write-Output "SourceBranch: $SourceBranch"
Write-Output "TargetBranch: $TargetBranch"
Write-Output "MergeBase: $mergeBase"

Write-Section "Status"
git status --short

Write-Section "Commits"
git log --oneline --no-decorate "$TargetBranch..$SourceBranch"

Write-Section "Changed Files"
git diff --name-only "$TargetBranch...$SourceBranch"

Write-Section "Diff Stat"
git diff --stat "$TargetBranch...$SourceBranch"

Write-Section "Patch"
git diff "--unified=$Unified" "$TargetBranch...$SourceBranch"
