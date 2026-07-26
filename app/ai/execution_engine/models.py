from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping
from uuid import UUID, uuid4

def utc_now(): return datetime.now(timezone.utc).isoformat()
class OrderSide(str,Enum): BUY='BUY'; SELL='SELL'
class OrderType(str,Enum): MARKET='MARKET'; LIMIT='LIMIT'; STOP='STOP'; STOP_LIMIT='STOP_LIMIT'; TRAILING_STOP='TRAILING_STOP'
class TimeInForce(str,Enum): DAY='DAY'; GTC='GTC'; IOC='IOC'; FOK='FOK'
class OrderStatus(str,Enum): CREATED='CREATED'; VALIDATED='VALIDATED'; ROUTED='ROUTED'; SUBMITTED='SUBMITTED'; ACKNOWLEDGED='ACKNOWLEDGED'; PARTIALLY_FILLED='PARTIALLY_FILLED'; FILLED='FILLED'; CANCELLED='CANCELLED'; REJECTED='REJECTED'; FAILED='FAILED'
class ExecutionStatus(str,Enum): SUCCESS='SUCCESS'; PARTIAL='PARTIAL'; REJECTED='REJECTED'; FAILED='FAILED'; DEFERRED='DEFERRED'
@dataclass(frozen=True,slots=True)
class ExecutionRequest:
    symbol:str; side:OrderSide; quantity:int; order_type:OrderType=OrderType.MARKET; time_in_force:TimeInForce=TimeInForce.DAY
    limit_price:float|None=None; stop_price:float|None=None; trailing_percent:float|None=None
    decision_id:str|None=None; correlation_id:str|None=None; idempotency_key:str|None=None; metadata:Mapping[str,Any]=field(default_factory=dict)
    def __post_init__(self):
        if not self.symbol.strip(): raise ValueError('symbol cannot be empty')
        if self.quantity<=0: raise ValueError('quantity must be positive')
@dataclass(slots=True)
class Order:
    order_id:UUID; request:ExecutionRequest; status:OrderStatus=OrderStatus.CREATED; broker_order_id:str|None=None
    filled_quantity:int=0; average_fill_price:float=0.0; created_at_utc:str=field(default_factory=utc_now); updated_at_utc:str=field(default_factory=utc_now); failure_reason:str|None=None
    @classmethod
    def create(cls,request): return cls(uuid4(),request)
    @property
    def remaining_quantity(self): return max(0,self.request.quantity-self.filled_quantity)
    def to_dict(self):
        d=asdict(self); d['order_id']=str(self.order_id); d['status']=self.status.value; d['request']['side']=self.request.side.value; d['request']['order_type']=self.request.order_type.value; d['request']['time_in_force']=self.request.time_in_force.value; return d
@dataclass(frozen=True,slots=True)
class BrokerAcknowledgement: accepted:bool; broker_order_id:str|None; message:str=''
@dataclass(frozen=True,slots=True)
class Fill:
    fill_id:UUID; order_id:UUID; quantity:int; price:float; timestamp_utc:str=field(default_factory=utc_now)
    @classmethod
    def create(cls,order_id,quantity,price): return cls(uuid4(),order_id,quantity,price)
@dataclass(frozen=True,slots=True)
class ExecutionResult:
    execution_id:UUID; status:ExecutionStatus; order:Order; fills:tuple[Fill,...]; message:str; created_at_utc:str=field(default_factory=utc_now)
    @classmethod
    def create(cls,status,order,fills,message): return cls(uuid4(),status,order,fills,message)
    def to_dict(self): return {'execution_id':str(self.execution_id),'status':self.status.value,'order':self.order.to_dict(),'fills':[{'fill_id':str(f.fill_id),'order_id':str(f.order_id),'quantity':f.quantity,'price':f.price,'timestamp_utc':f.timestamp_utc} for f in self.fills],'message':self.message,'created_at_utc':self.created_at_utc}
