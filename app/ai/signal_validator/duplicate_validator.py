from collections import OrderedDict
from threading import RLock
from .validation_models import *
class DuplicateValidator:
    def __init__(self, capacity=100000):
        self.capacity=capacity; self._seen=OrderedDict(); self._lock=RLock()
    def validate(self, signal, context):
        with self._lock:
            duplicate=signal.fingerprint in self._seen
            self._seen[signal.fingerprint]=None; self._seen.move_to_end(signal.fingerprint)
            while len(self._seen)>self.capacity: self._seen.popitem(last=False)
        if duplicate:
            return ValidationCheckResult(ValidationCheckType.DUPLICATE,ValidationStatus.FAIL,0,
                ValidationSeverity.WARNING,"DUPLICATE_SIGNAL","Signal was already validated.")
        return ValidationCheckResult(ValidationCheckType.DUPLICATE,ValidationStatus.PASS,1,
            ValidationSeverity.INFO,"SIGNAL_UNIQUE","Signal is unique.")
    def size(self):
        with self._lock: return len(self._seen)
