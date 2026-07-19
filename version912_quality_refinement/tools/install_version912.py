from __future__ import annotations

from pathlib import Path
import shutil


ROOT = Path.cwd()
BACKUP = ROOT / ".version912_backup"

required = [
    ROOT / "app" / "broker" / "order_manager.py",
    ROOT / "app" / "services" / "portfolio_intelligence.py",
    ROOT / "app" / "dashboard" / "components" / "portfolio_intelligence.py",
]

missing = [str(path) for path in required if not path.exists()]
if missing:
    raise SystemExit(
        "Version 9.1.2 prerequisites are missing:\n- "
        + "\n- ".join(missing)
    )

BACKUP.mkdir(exist_ok=True)

for source in required + [ROOT / "tests" / "test_account_summary.py"]:
    if source.exists():
        target = BACKUP / source.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            shutil.copy2(source, target)

order_manager = required[0]
text = order_manager.read_text(encoding="utf-8")

old_import = (
    "from app.models.risk_models import PortfolioSnapshot"
)
new_import = (
    "from app.models.portfolio_risk_models "
    "import PortfolioSnapshot"
)

if old_import in text:
    text = text.replace(old_import, new_import)
elif new_import not in text:
    raise SystemExit(
        "Could not identify the PortfolioSnapshot import in "
        "app/broker/order_manager.py."
    )

order_manager.write_text(text, encoding="utf-8")

print("Updated order_manager PortfolioSnapshot import.")
print(f"Backup directory: {BACKUP}")
