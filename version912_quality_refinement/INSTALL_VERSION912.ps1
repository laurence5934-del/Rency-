$ErrorActionPreference = "Stop"

Write-Host "Installing Version 9.1.2..." -ForegroundColor Cyan

if (-not (Test-Path ".\app\dashboard\main.py")) {
    throw "Run this installer from the repository root."
}

$PackageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

python (Join-Path $PackageRoot "tools\install_version912.py")
if ($LASTEXITCODE -ne 0) {
    throw "Version 9.1.2 repository patch failed."
}

$Copies = @(
    @{
        Source = "app\services\portfolio_intelligence.py"
        Destination = "app\services\portfolio_intelligence.py"
    },
    @{
        Source = "app\dashboard\components\portfolio_intelligence.py"
        Destination = "app\dashboard\components\portfolio_intelligence.py"
    },
    @{
        Source = "tests\test_account_summary.py"
        Destination = "tests\test_account_summary.py"
    },
    @{
        Source = "tests\test_portfolio_intelligence.py"
        Destination = "tests\test_portfolio_intelligence.py"
    }
)

foreach ($Item in $Copies) {
    $SourcePath = Join-Path $PackageRoot $Item.Source
    $DestinationPath = Join-Path (Get-Location) $Item.Destination
    $DestinationDirectory = Split-Path -Parent $DestinationPath

    New-Item -ItemType Directory -Force -Path $DestinationDirectory | Out-Null
    Copy-Item -Force $SourcePath $DestinationPath
}

Write-Host ""
Write-Host "Version 9.1.2 installed." -ForegroundColor Green
Write-Host "Run these tests:" -ForegroundColor Yellow
Write-Host "python -m pytest tests\test_account_summary.py tests\test_portfolio_intelligence.py -q"
Write-Host "python -m pytest tests\test_order_manager.py -q"
Write-Host "python -m pytest -q"
