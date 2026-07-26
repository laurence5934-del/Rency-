from collections import defaultdict
from .models import *
VALUES={Direction.STRONGLY_BEARISH:-1.0,Direction.BEARISH:-.5,Direction.NEUTRAL:0.0,
        Direction.BULLISH:.5,Direction.STRONGLY_BULLISH:1.0}
class WeightedVotingEngine:
    def __init__(self, neutral_deadband=.10): self.deadband=neutral_deadband
    def calculate(self, votes):
        if not votes:
            return ConsensusOutcome(Direction.NEUTRAL,0,0,0,0,
                {d.value:0 for d in Direction},0,0)
        scores=defaultdict(float); total=0.0; signed=0.0; abstentions=0
        for vote in votes:
            effective=vote.weight*vote.confidence
            scores[vote.direction]+=effective; total+=effective
            signed+=VALUES[vote.direction]*effective
            abstentions += vote.direction==Direction.NEUTRAL
        normalized=signed/total if total else 0
        if abs(normalized)<=self.deadband: winner=Direction.NEUTRAL
        elif normalized>=.75: winner=Direction.STRONGLY_BULLISH
        elif normalized>0: winner=Direction.BULLISH
        elif normalized<=-.75: winner=Direction.STRONGLY_BEARISH
        else: winner=Direction.BEARISH
        bull=scores[Direction.BULLISH]+scores[Direction.STRONGLY_BULLISH]
        bear=scores[Direction.BEARISH]+scores[Direction.STRONGLY_BEARISH]
        if winner in {Direction.BULLISH,Direction.STRONGLY_BULLISH}: win,dissent=bull,bear
        elif winner in {Direction.BEARISH,Direction.STRONGLY_BEARISH}: win,dissent=bear,bull
        else: win,dissent=scores[Direction.NEUTRAL],min(bull,bear)
        agreement=win/total if total else 0; dissent_ratio=dissent/total if total else 0
        score=max(0,min(1,.65*agreement+.35*abs(normalized)))
        return ConsensusOutcome(winner,score,agreement,dissent_ratio,total,
            {d.value:scores.get(d,0) for d in Direction},len(votes),abstentions)
