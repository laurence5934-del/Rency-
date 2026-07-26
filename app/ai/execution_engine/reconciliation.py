from .models import OrderStatus
class ExecutionReconciler:
    def reconcile(self,order):
        issues=[]
        if order.filled_quantity>order.request.quantity:issues.append('OVERFILLED_ORDER')
        if order.status==OrderStatus.FILLED and order.filled_quantity!=order.request.quantity:issues.append('FILLED_STATUS_QUANTITY_MISMATCH')
        return (not issues,tuple(issues))
