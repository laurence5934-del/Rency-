class ValidationScoreEngine:
    def __init__(self, policy): self.policy=policy
    def calculate(self, checks):
        lookup={c.check_type:c for c in checks}; total=used=0.0
        for kind,weight in self.policy.check_weights.items():
            if kind in lookup: total+=lookup[kind].score*weight; used+=weight
        return max(0,min(1,total/used)) if used else 0.0
