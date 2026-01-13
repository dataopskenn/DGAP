<#
Push the current repository to GitHub using the GitHub CLI (`gh`).

Usage:
  # create repo under authenticated user (public) and push
  .\scripts\push_to_github.ps1

  # create repo under specific owner (org or user)
  .\scripts\push_to_github.ps1 -Owner "my-org-or-user"

Notes:
- Requires `gh` (GitHub CLI) and `git` installed and `gh auth login` completed.
- This script will initialize a git repo if none exists, create an initial commit if needed,
  create a public GitHub repo named `DGAP` (or under specified owner), add remote `origin`, and push.
#>

param(
    [string]$Owner = "",
    [ValidateSet('public','private')][string]$Visibility = 'public',
    [string]$RepoName = 'DGAP'
)

Set-Location -Path (Split-Path -Path $MyInvocation.MyCommand.Definition -Parent) > $null
Set-Location -Path (Resolve-Path ".." ) > $null

Write-Host "Repository root: $(Get-Location)"

# Ensure git initialized
if (-not (Test-Path -Path .git)) {
    Write-Host "Initializing git repository..."
    git init
}

# Add files and commit if no commits
$hasCommit = $false
try {
    git rev-parse --verify HEAD > $null 2>&1
    $hasCommit = $true
} catch {
    $hasCommit = $false
}

git add -A
if (-not $hasCommit) {
    git commit -m "chore: add DGAP Sprint 1 prototype" --allow-empty
} else {
    # create a commit if there are staged changes
    $status = git diff --cached --name-only
    if ($status) { git commit -m "chore: update DGAP prototype" }
}

# If a remote named 'origin' already exists, prompt user for action
$originExists = $false
git remote get-url origin > $null 2>&1
if ($LASTEXITCODE -eq 0) { $originExists = $true }

if ($originExists) {
    $existingUrl = (git remote get-url origin) -join ""
    Write-Host "Remote 'origin' already exists: $existingUrl"
    $choice = Read-Host "Choose action: [O]verwrite remote, [U]se existing and push, [A]bort (O/U/A)"
    switch ($choice.ToUpper()) {
        'O' {
            Write-Host "Removing existing 'origin' remote..."
            git remote remove origin
        }
        'U' {
            Write-Host "Using existing remote. Pushing to origin/main..."
            git branch -M main
            git push -u origin main
            if ($LASTEXITCODE -ne 0) { Write-Error "Push failed."; exit $LASTEXITCODE }
            Write-Host "Pushed to existing remote. Exiting."
            exit 0
        }
        Default {
            Write-Host "Aborting per user request."; exit 1
        }
    }
}

# Construct gh create command and create+push the repo
if ([string]::IsNullOrWhiteSpace($Owner)) {
    $createCmd = "gh repo create $RepoName --$Visibility --source=. --remote=origin --push"
} else {
    $createCmd = "gh repo create $Owner/$RepoName --$Visibility --source=. --remote=origin --push"
}

Write-Host "Running: $createCmd"
Invoke-Expression $createCmd

if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to create or push repository. Check gh auth and network access."
    exit $LASTEXITCODE
}

try {
    $login = gh api user --jq .login
} catch {
    $login = "<owner>"
}

Write-Host "Repository created and pushed. Visit: https://github.com/$(if ($Owner) { $Owner + "/" + $RepoName } else { $login + "/" + $RepoName })"
