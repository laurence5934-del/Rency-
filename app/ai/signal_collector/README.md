# Version 10.1.1.2 — Enterprise Signal Collector

## Purpose

The Enterprise Signal Collector is the intake gateway for the AI Decision Engine.
It collects, normalizes, scores, deduplicates, prioritizes, and optionally publishes
signals from many independent providers.

## Modules

- `models.py` — raw and normalized signal contracts
- `provider.py` — provider protocol
- `registry.py` — thread-safe provider registry
- `normalizer.py` — canonical normalization and SHA-256 fingerprinting
- `quality.py` — freshness, completeness, and confidence scoring
- `deduplicator.py` — bounded thread-safe duplicate suppression
- `metrics.py` — collection metrics
- `collector.py` — concurrent enterprise collector orchestration

## Compile

```powershell
python -m compileall app/ai/signal_collector
```

## Package location

```text
app/ai/signal_collector/
```
