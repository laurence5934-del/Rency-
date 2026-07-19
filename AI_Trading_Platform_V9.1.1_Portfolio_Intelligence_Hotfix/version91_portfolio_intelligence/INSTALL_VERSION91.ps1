$ErrorActionPreference = "Stop"
Write-Host "Installing Version 9.1 Portfolio Intelligence..." -ForegroundColor Cyan

if (-not (Test-Path ".\app\dashboard\main.py")) {
    throw "Run this installer from the repository root."
}

$PackageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Copies = @(
    @{ Source = "app\services\portfolio_intelligence.py"; Destination = "app\services\portfolio_intelligence.py" },
    @{ Source = "app\dashboard\components\portfolio_intelligence.py"; Destination = "app\dashboard\components\portfolio_intelligence.py" },
    @{ Source = "tests\test_portfolio_intelligence.py"; Destination = "tests\test_portfolio_intelligence.py" }
)

foreach ($Item in $Copies) {
    $SourcePath = Join-Path $PackageRoot $Item.Source
    $DestinationPath = Join-Path (Get-Location) $Item.Destination
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $DestinationPath) | Out-Null
    Copy-Item -Force $SourcePath $DestinationPath
}

python (Join-Path $PackageRoot "tools\install_version91.py")
if ($LASTEXITCODE -ne 0) {
    throw "Version 9.1 dashboard integration failed."
}
Write-Host "Installation complete." -ForegroundColor Green
Write-Host "Run: python -m pytest tests\test_portfolio_intelligence.py -q" -ForegroundColor Yellow
