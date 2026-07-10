from app.db.approvals import (
    get_pending_manual_reviews,
    get_review_history,
    init_approval_db,
)

print("Initializing manual approval database...")
init_approval_db()

print("\nPending manual reviews:")
for item in get_pending_manual_reviews():
    print(
        item["id"],
        item["symbol"],
        item["ai_score"],
        item["final_action"],
        item["quantity"],
    )

print("\nReview history:")
print(get_review_history())