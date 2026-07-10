from app.broker.market_data import get_market_data

print("Reading live market data for NVDA...")
print(get_market_data("NVDA"))

input("Press Enter to close...")