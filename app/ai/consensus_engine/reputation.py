from threading import RLock
class ContributorReputationManager:
    def __init__(self, minimum_multiplier=.5, maximum_multiplier=1.5):
        self.minimum=minimum_multiplier; self.maximum=maximum_multiplier
        self._outcomes={}; self._lock=RLock()
    def record(self, contributor_id, successful):
        with self._lock:
            success,failure=self._outcomes.get(contributor_id,[0,0])
            self._outcomes[contributor_id]=[success+int(successful),failure+int(not successful)]
    def multiplier(self, contributor_id):
        with self._lock: success,failure=self._outcomes.get(contributor_id,[0,0])
        total=success+failure
        if not total: return 1.0
        return min(self.maximum,max(self.minimum,.5+success/total))
