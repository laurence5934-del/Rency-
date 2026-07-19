$ErrorActionPreference = "Stop"

$BackupRoot = ".\.version912_backup"

if (-not (Test-Path $BackupRoot)) {
    throw "No Version 9.1.2 backup directory was found."
}

$Files = @(
    "app\broker\order_manager.py",
    "app\services\portfolio_intelligence.py",
    "app\dashboard\components\portfolio_intelligence.py",
    "tests\test_account_summary.py"
)

foreach ($RelativePath in $Files) {
    $BackupFile = Join-Path $BackupRoot $RelativePath

    if (Test-Path $BackupFile) {
        $Destination = Join-Path (Get-Location) $RelativePath
        $DestinationDirectory = Split-Path -Parent $Destination
        New-Item -ItemType Directory -Force -Path $DestinationDirectory | Out-Null
        Copy-Item -Force $BackupFile $Destination
        Write-Host "Restored $RelativePath" -ForegroundColor Green
    }
}

Write-Host "Version 9.1.2 rollback completed." -ForegroundColor Green
