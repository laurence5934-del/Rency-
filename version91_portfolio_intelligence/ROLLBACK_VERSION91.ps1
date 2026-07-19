$ErrorActionPreference = "Stop"
$Backup = ".\.version91_backup\main.py"
if (Test-Path $Backup) {
    Copy-Item -Force $Backup ".\app\dashboard\main.py"
    Write-Host "Restored app\dashboard\main.py" -ForegroundColor Green
}
Remove-Item ".\app\services\portfolio_intelligence.py" -Force -ErrorAction SilentlyContinue
Remove-Item ".\app\dashboard\components\portfolio_intelligence.py" -Force -ErrorAction SilentlyContinue
Remove-Item ".\tests\test_portfolio_intelligence.py" -Force -ErrorAction SilentlyContinue
Write-Host "Version 9.1 files removed." -ForegroundColor Green
