from app.broker.ibkr_official import cancel_order

order_id = int(input("Enter order ID to cancel: "))

confirm = input(f"Type CANCEL to cancel order {order_id}: ")

if confirm == "CANCEL":
    print(cancel_order(order_id))
else:
    print("Cancelled by user.")