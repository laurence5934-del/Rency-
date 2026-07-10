# Implementation Steps

1. Extract ZIP to `C:\Users\jamar\AITradingPlatformV4`.
2. Open folder in VS Code.
3. Create venv:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
4. Copy `config/config.example.env` to `config/config.env`.
5. Add your new OpenAI API key.
6. Start TWS paper account and verify API settings.
7. Run `python tests\test_openai.py`.
8. Run `python tests\test_ibkr_connection.py`.
9. Start webhook: `python -m uvicorn app.api.webhook_server:app --reload --port 8000`.
10. Start dashboard: `python -m streamlit run app/dashboard/main.py`.
11. Run `python tests\test_webhook.py`.
12. Only after connection success, run `python tests\test_paper_order_1_share.py` for a 1-share paper order.
