from app.broker.ibkr_official import get_positions

print("Reading IBKR paper positions...")

result = get_positions()

print(result)

input("Press Enter to close...")