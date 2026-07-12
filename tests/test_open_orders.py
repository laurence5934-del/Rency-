from app.broker.open_orders import get_open_orders

print("Reading IBKR paper open orders...")

result = get_open_orders()

print(result)

input("Press Enter to close...")