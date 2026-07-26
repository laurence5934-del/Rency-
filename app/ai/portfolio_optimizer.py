from __future__ import annotations
from dataclasses import dataclass
from math import isfinite
from numbers import Real
from typing import Mapping, Any

@dataclass(frozen=True, slots=True)
class AssetAllocation:
    symbol: str
    expected_return: float
    risk_score: float
    correlation_penalty: float
    confidence: float
    current_weight: float = 0.0

@dataclass(frozen=True, slots=True)
class OptimizationResult:
    target_weights: dict[str,float]
    portfolio_score: float
    rebalance_required: bool
    reasons: tuple[str,...]

    def to_dict(self)->dict[str,Any]:
        return {
            "target_weights": self.target_weights,
            "portfolio_score": self.portfolio_score,
            "rebalance_required": self.rebalance_required,
            "reasons": list(self.reasons),
        }

class PortfolioOptimizer:
    """
    Version 9.8.0.6
    Simple explainable optimizer.
    """

    def __init__(self,
                 max_asset_weight: float = 0.25,
                 min_asset_weight: float = 0.0):
        for n,v in (("max_asset_weight",max_asset_weight),
                    ("min_asset_weight",min_asset_weight)):
            if not isinstance(v,Real) or isinstance(v,bool):
                raise TypeError(f"{n} must be numeric")
            v=float(v)
            if not isfinite(v):
                raise ValueError(f"{n} must be finite")
        if not 0<=min_asset_weight<=max_asset_weight<=1:
            raise ValueError("invalid weight limits")
        self.max_asset_weight=float(max_asset_weight)
        self.min_asset_weight=float(min_asset_weight)
        self._last=None

    def optimize(self, assets: Mapping[str,AssetAllocation]) -> OptimizationResult:
        if not assets:
            raise ValueError("assets cannot be empty")
        scores={}
        total=0.0
        reasons=[]
        for name,a in assets.items():
            score=max(0.0,
                a.expected_return*0.35+
                a.confidence*0.35+
                (1-a.risk_score)*0.20+
                (1-a.correlation_penalty)*0.10)
            scores[name]=score
            total+=score
        weights={}
        for name,score in scores.items():
            w=score/total if total else 0
            w=min(self.max_asset_weight,max(self.min_asset_weight,w))
            weights[name]=w
        norm=sum(weights.values())
        if norm>0:
            weights={k:v/norm for k,v in weights.items()}
        portfolio_score=sum(scores.values())/len(scores)
        reasons.append("Weights favor higher confidence and return while penalizing risk and correlation.")
        result=OptimizationResult(
            target_weights=weights,
            portfolio_score=round(portfolio_score,6),
            rebalance_required=True,
            reasons=tuple(reasons),
        )
        self._last=result
        return result

    def reset(self):
        self._last=None

    def to_dict(self):
        return {
            "max_asset_weight":self.max_asset_weight,
            "min_asset_weight":self.min_asset_weight,
            "last_result":None if self._last is None else self._last.to_dict()
        }
