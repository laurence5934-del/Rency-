from pathlib import Path
import shutil

PROJECT_ROOT = Path.cwd()
MAIN_FILE = PROJECT_ROOT / "app" / "dashboard" / "main.py"
BACKUP_DIR = PROJECT_ROOT / ".version91_backup"
BACKUP_FILE = BACKUP_DIR / "main.py"

if not MAIN_FILE.exists():
    raise SystemExit("Run the installer from the repository root.")

BACKUP_DIR.mkdir(exist_ok=True)
if not BACKUP_FILE.exists():
    shutil.copy2(MAIN_FILE, BACKUP_FILE)

text = MAIN_FILE.read_text(encoding="utf-8")
text = text.replace(
    "from app.dashboard.components.portfolio_summary import show_portfolio_summary",
    "from app.dashboard.components.portfolio_intelligence import show_portfolio_intelligence",
)

duplicate_import = (
    "from app.dashboard.controllers.dashboard_controller import (
"
    "    initialize_dashboard_state,
"
    ")

"
    "from app.dashboard.controllers.dashboard_controller import (
"
    "    initialize_dashboard_state,
"
    ")
"
)
text = text.replace(
    duplicate_import,
    "from app.dashboard.controllers.dashboard_controller import (
"
    "    initialize_dashboard_state,
"
    ")
",
)

replacements = {
    'page_icon="ðŸ“ˆ"': 'page_icon="📈"',
    'return "ðŸŸ¢"': 'return "🟢"',
    'return "ðŸŸ¡"': 'return "🟡"',
    'return "ðŸ”´"': 'return "🔴"',
    'return "âšª"': 'return "⚪"',
    'st.subheader("ðŸ¤– AI Signal Center")': 'st.subheader("🤖 AI Signal Center")',
}
for old, new in replacements.items():
    text = text.replace(old, new)

start_marker = 'st.subheader("IBKR Paper Account Summary")'
end_marker = 'st.subheader("🤖 AI Signal Center")'
if start_marker in text and end_marker in text:
    start = text.index(start_marker)
    end = text.index(end_marker)
    replacement = (
        "show_portfolio_intelligence(
"
        "    account_data,
"
        "    positions_data,
"
        ")

"
        "st.divider()

"
    )
    text = text[:start] + replacement + text[end:]

text = text.replace(
    "show_portfolio_summary(account_data)",
    "show_portfolio_intelligence(
    account_data,
    positions_data,
)",
)

needle = (
    "
st.divider()
"
    "show_portfolio_intelligence(
"
    "    account_data,
"
    "    positions_data,
"
    ")

"
    "st.divider()
"
    "show_live_positions(positions_data)"
)
text = text.replace(
    needle,
    "
st.divider()
show_live_positions(positions_data)",
)

MAIN_FILE.write_text(text, encoding="utf-8")
print("Version 9.1 dashboard integration completed.")
print(f"Backup: {BACKUP_FILE}")
