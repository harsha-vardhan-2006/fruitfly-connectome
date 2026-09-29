# E10B FINAL STATUS — immutable experiment record

Written: 2026-09-16. This file records the E10B protocol and its live
state. The manuscript is updated **only** from
`results/final/e10b_final.json` after 100/100 — never from this prose.

```text
Experiment:            E10B — 100-null degree-preserving confirmation protocol
Protocol:              100 null networks, directed configuration model, EXACT
                       in+out degree sequences (verified per null inside the run)
Observed network:      FAFB v783 (Princeton), 138,584 nodes / 3,732,460 edges
Random seeds:          100 + i, i = 0..99
Panel k:               k = 4 (fixed source panel, seed 0), 1,696 matched-pair nodes
Matched pairs:         E08 pre-registered 848 GABA→ACh pairs (±10% total degree)
Algorithm version:     code_version f1d00d078f7f3ad7 (post swap-disjointness +
                       rejection-redraw fixes; pilot artifacts quarantined)
Implementation:        src/experiments/run_e10b.py (UNMODIFIED throughout)
Completed:             live — see results/tables/e10b_nulls.csv (n rows = n nulls)
Hardware:              local Windows 11, AMD64, Python 3.13.2 (3 parallel workers)
Runtime:               ~15–20 min per null per worker; full-ensemble ETA ~8 h
                       from resume at 16/100 (2026-09-16 23:47 IST)
Resumability:          row JSONs + per-null CIS checkpoints honored; crashed
                       run at 16/100 resumed same day, no code or seed changes
Degree verification:   every null aborts unless in+out degree sequences are
                       EXACTLY equal to the real graph (all nulls so far: PASS)
Superseded artifacts:  results/superseded/ (E10 pilot; 16-null interim report)
Final statistics:      py -m src.experiments.run_e10b stats  →  results/tables/e10b_results.json
                       then copied to results/final/e10b_final.json + archive here
```

Interim read (16 nulls, superseded by the final ensemble — recorded for
the audit trail): null δ mean 0.0746, sd 0.0139, max 0.0937; observed
δ = 0.0979; empirical p_delta = 0.0588; median-diff p = 0.8235. All
nulls degree-verified. Interpretation gate remains CLOSED until 100/100.
