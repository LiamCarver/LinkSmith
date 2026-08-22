param(
    [Parameter(Mandatory = $true)]
    [Alias("SourceBranch")]
    [string]$SourceRef,

    [Parameter(Mandatory = $true)]
    [Alias("TargetBranch")]
    [string]$TargetRef,

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

function Fail {
    param([string]$Message)

    throw $Message
}

function Test-GitRefExists {
    param([string]$RefName)

    git rev-parse --verify --quiet $RefName | Out-Null
    return $LASTEXITCODE -eq 0
}

function Resolve-GitRefCommit {
    param([string]$RefName)

    $resolved = git rev-parse --verify "$RefName^{commit}"
    if ($LASTEXITCODE -ne 0 -or -not $resolved) {
        Fail "Git ref '$RefName' could not be resolved to a commit."
    }
    return $resolved.Trim()
}

function Get-GitRefKind {
    param([string]$RefName)

    git show-ref --verify --quiet "refs/heads/$RefName"
    if ($LASTEXITCODE -eq 0) {
        return "branch"
    }

    git show-ref --verify --quiet "refs/tags/$RefName"
    if ($LASTEXITCODE -eq 0) {
        return "tag"
    }

    return "commit-or-other-ref"
}

if ($FetchFirst) {
    git fetch origin | Out-Null
}

if (-not (Test-GitRefExists -RefName $SourceRef)) {
    Fail "Source ref '$SourceRef' was not found locally."
}

if (-not (Test-GitRefExists -RefName $TargetRef)) {
    Fail "Target ref '$TargetRef' was not found locally."
}

$resolvedSource = Resolve-GitRefCommit -RefName $SourceRef
$resolvedTarget = Resolve-GitRefCommit -RefName $TargetRef
$sourceKind = Get-GitRefKind -RefName $SourceRef
$targetKind = Get-GitRefKind -RefName $TargetRef

$mergeBase = git merge-base $resolvedTarget $resolvedSource
if (-not $mergeBase) {
    Fail "Could not resolve a merge base between '$TargetRef' and '$SourceRef'."
}

Write-Section "Review Context"
Write-Output "SourceRef: $SourceRef"
Write-Output "SourceKind: $sourceKind"
Write-Output "SourceCommit: $resolvedSource"
Write-Output "TargetRef: $TargetRef"
Write-Output "TargetKind: $targetKind"
Write-Output "TargetCommit: $resolvedTarget"
Write-Output "MergeBase: $mergeBase"
Write-Output "FetchFirst: $FetchFirst"

Write-Section "Status"
git status --short

Write-Section "Commits"
git log --oneline --no-decorate "$resolvedTarget..$resolvedSource"

Write-Section "Changed Files"
git diff --name-only "$resolvedTarget...$resolvedSource"

Write-Section "Diff Stat"
git diff --stat "$resolvedTarget...$resolvedSource"

Write-Section "Patch"
git diff "--unified=$Unified" "$resolvedTarget...$resolvedSource"
}
finally {
    Pop-Location
}
