from __future__ import annotations


class BenchmarkEngine:
    def compare(self, portfolio_values: tuple[float, ...], benchmark_values: tuple[float, ...]) -> dict[str, float]:
        portfolio_return = self._total_return(portfolio_values)
        benchmark_return = self._total_return(benchmark_values)
        return {
            "portfolio_return": portfolio_return,
            "benchmark_return": benchmark_return,
            "excess_return": portfolio_return - benchmark_return,
        }

    @staticmethod
    def _total_return(values: tuple[float, ...]) -> float:
        if len(values) < 2 or values[0] == 0:
            return 0.0
        return (values[-1] - values[0]) / values[0]
