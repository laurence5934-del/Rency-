from app.scanner.scanner_config import ScannerConfig
from app.scanner.scanner_models import ScanSummary


class MarketScanner:

    def __init__(self, config: ScannerConfig | None = None):

        self.config = config or ScannerConfig()

    def scan(self, symbols: list[str]) -> ScanSummary:
        """
        Scan symbols and return ranked candidates.
        """
        raise NotImplementedError