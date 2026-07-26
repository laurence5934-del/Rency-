# Version 10.1.1.4 - Enterprise AI Consensus Engine

Install at `app/ai/consensus_engine/`.

Compile:
`python -m compileall app/ai/consensus_engine`

Smoke test:
`$env:PYTHONPATH = $PWD`
`python tests/test_ai_consensus_engine_smoke.py`
`echo $LASTEXITCODE`

Capabilities include contributor registration, concurrent vote collection,
confidence and reputation weighted voting, agreement and dissent scoring,
and APPROVE, REVIEW, REJECT, or ABSTAIN decisions.
