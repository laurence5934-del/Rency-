from app.broker.ibkr_official import place_paper_buy

print("Submitting 1-share paper BUY order for NVDA.")
print("Only run this while logged into IBKR PAPER account.")
confirm = input("Type PAPER to continue: ").strip().upper()
if confirm != "PAPER":
    print("Cancelled.")
else:
    print(place_paper_buy("NVDA", 1))
