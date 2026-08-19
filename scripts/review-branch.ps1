param(
    [Parameter(Mandatory = $true)]
    [string]$SourceBranch,

    [Parameter(Mandatory = $true)]
    [string]$TargetBranch,

    [int]$Unified = 3,

    [switch]$FetchFirst
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot

Push-Location $repoRoot

try {

function Write-Section {
    param([string]$Title)
    Write-Output ""
    Write-Output "### $Title"
}

function Test-LocalBranchExists {
    param([string]$BranchName)

    git show-ref --verify --quiet "refs/heads/$BranchName"
    return $LASTEXITCODE -eq 0
}

function Fail {
    param([string]$Message)

    throw $Message
}

if ($FetchFirst) {
    git fetch origin | Out-Null
}

if (-not (Test-LocalBranchExists -BranchName $SourceBranch)) {
    Fail "Source branch '$SourceBranch' was not found locally."
}

if (-not (Test-LocalBranchExists -BranchName $TargetBranch)) {
    Fail "Target branch '$TargetBranch' was not found locally."
}

$mergeBase = git merge-base $TargetBranch $SourceBranch
if (-not $mergeBase) {
    Fail "Could not resolve a merge base between '$TargetBranch' and '$SourceBranch'."
}

Write-Section "Review Context"
Write-Output "SourceBranch: $SourceBranch"
Write-Output "TargetBranch: $TargetBranch"
Write-Output "MergeBase: $mergeBase"
Write-Output "FetchFirst: $FetchFirst"

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
}
finally {
    Pop-Location
}
