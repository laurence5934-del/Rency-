# AI Trading Platform V4 Professional Edition

TradingView + ChatGPT/OpenAI + Official Interactive Brokers API + FastAPI + Streamlit.

## Safety Defaults

- Paper trading only by default
- Manual approval required by default
- Live trading blocked unless you explicitly change settings
- Designed for testing and education, not guaranteed profits

## Folder Structure

```text
ai_trading_platform_v4_pro/
├── app/
│   ├── ai/                 # OpenAI signal scoring
│   ├── api/                # FastAPI webhook server
│   ├── broker/             # Official IBKR API integration
│   ├── dashboard/          # Streamlit dashboard
│   ├── db/                 # SQLite database
│   ├── models/             # Pydantic models
│   ├── risk/               # Risk manager
│   └── utils/              # Logging/helpers
├── config/                 # config.env lives here
├── data/                   # SQLite database
├── logs/                   # Runtime logs
├── scripts/                # Windows start/test scripts
├── tradingview/            # Pine Script scanner
└── tests/                  # Test utilities
```

## Step 1 — Install Packages

```powershell
pip install -r requirements.txt
```

## Step 2 — Create Config File

Copy:

```powershell
copy config\config.example.env config\config.env
```

Edit `config/config.env` and add your new OpenAI API key.

```env
OPENAI_API_KEY=your_new_openai_key_here
OPENAI_MODEL=gpt-4.1-mini
IBKR_HOST=127.0.0.1
IBKR_PORT=7497
IBKR_CLIENT_ID=11
PAPER_TRADING_ONLY=true
MANUAL_APPROVAL_REQUIRED=true
AUTO_SUBMIT_PAPER_ORDERS=false
MIN_AI_SCORE=80
MAX_SHARES_PER_TRADE=25
MAX_RISK_PER_TRADE_PCT=1.0
MAX_DAILY_LOSS_PCT=3.0
```

## Step 3 — Start TWS Paper Trading

In TWS:

```text
File → Global Configuration → API → Settings
```

Confirm:

- Enable ActiveX and Socket Clients: checked
- Socket Port: 7497
- Read-Only API: unchecked
- Allow localhost only: checked
- Trusted IP: 127.0.0.1

## Step 4 — Test OpenAI

```powershell
python tests\test_openai.py
```

## Step 5 — Test IBKR Connection

```powershell
python tests\test_ibkr_connection.py
```

## Step 6 — Start Webhook Server

```powershell
python -m uvicorn app.api.webhook_server:app --reload --port 8000
```

Open:

```text
http://127.0.0.1:8000
```

## Step 7 — Start Dashboard

In another PowerShell:

```powershell
python -m streamlit run app/dashboard/main.py
```

Open:

```text
http://localhost:8501
```

## Step 8 — Test Full Webhook

```powershell
python tests\test_webhook.py
```

Refresh dashboard.

## Step 9 — TradingView

Use `tradingview/ai_scanner_v4.pine` in TradingView Pine Editor.

For local testing, expose the webhook using ngrok or Cloudflare Tunnel:

```powershell
ngrok http 8000
```

TradingView webhook URL:

```text
https://your-ngrok-url/webhook/tradingview
```

## Important

Start with manual review and paper trading only. Do not enable live trading until the system has been tested thoroughly.
