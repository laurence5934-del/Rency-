from __future__ import annotations

from pathlib import Path
import shutil


PROJECT_ROOT = Path.cwd()
MAIN_FILE = PROJECT_ROOT / "app" / "dashboard" / "main.py"
BACKUP_DIR = PROJECT_ROOT / ".version91_backup"
BACKUP_FILE = BACKUP_DIR / "main.py"


def fail(message: str) -> None:
    print(f"ERROR: {message}")
    raise SystemExit(1)


if not MAIN_FILE.exists():
    fail(
        "Run the installer from the repository root. "
        "app/dashboard/main.py was not found."
    )

BACKUP_DIR.mkdir(exist_ok=True)
if not BACKUP_FILE.exists():
    shutil.copy2(MAIN_FILE, BACKUP_FILE)

text = MAIN_FILE.read_text(encoding="utf-8")

text = text.replace(
    "from app.dashboard.components.portfolio_summary "
    "import show_portfolio_summary",
    "from app.dashboard.components.portfolio_intelligence "
    "import show_portfolio_intelligence",
)

duplicate_import = """from app.dashboard.controllers.dashboard_controller import (
    initialize_dashboard_state,
)

from app.dashboard.controllers.dashboard_controller import (
    initialize_dashboard_state,
)
"""
single_import = """from app.dashboard.controllers.dashboard_controller import (
    initialize_dashboard_state,
)
"""
text = text.replace(duplicate_import, single_import)

text = text.replace('page_icon="ðŸ“ˆ"', 'page_icon="📈"')
text = text.replace('return "ðŸŸ¢"', 'return "🟢"')
text = text.replace('return "ðŸŸ¡"', 'return "🟡"')
text = text.replace('return "ðŸ”´"', 'return "🔴"')
text = text.replace('return "âšª"', 'return "⚪"')
text = text.replace(
    'st.subheader("ðŸ¤– AI Signal Center")',
    'st.subheader("🤖 AI Signal Center")',
)

start_marker = 'st.subheader("IBKR Paper Account Summary")'
ai_markers = (
    'st.subheader("🤖 AI Signal Center")',
    'st.subheader("ðŸ¤– AI Signal Center")',
)

end_marker = next(
    (marker for marker in ai_markers if marker in text),
    None,
)

if start_marker in text and end_marker is not None:
    start = text.index(start_marker)
    end = text.index(end_marker)
    replacement = """show_portfolio_intelligence(
    account_data,
    positions_data,
)

st.divider()

"""
    text = text[:start] + replacement + text[end:]
else:
    print(
        "NOTICE: The original top account-summary block was not found. "
        "The existing bottom portfolio component will be upgraded instead."
    )

text = text.replace(
    "show_portfolio_summary(account_data)",
    """show_portfolio_intelligence(
    account_data,
    positions_data,
)""",
)

duplicate_panel = """
st.divider()
show_portfolio_intelligence(
    account_data,
    positions_data,
)

st.divider()
show_live_positions(positions_data)
"""
single_panel = """
st.divider()
show_live_positions(positions_data)
"""
text = text.replace(duplicate_panel, single_panel)

MAIN_FILE.write_text(text, encoding="utf-8")
print("Version 9.1 dashboard integration completed.")
print(f"Backup: {BACKUP_FILE}")
