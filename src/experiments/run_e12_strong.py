"""E12-strengthened: visual-centrifugal (and other super_class) enrichment
among top-CIS chokepoints, with rigorous controls.

The raw 21/50 (11.7x vs whole-brain base rate) is NOT directly interpretable:
- the selection universe is the 3,518 TESTED neurons (centrality-ranked
  candidates), not all 139,255 neurons;
- CIS grows with degree, so a degree-matched null is the honest control.

Design (pre-registered here before unblinding new numbers):
  K in {25, 50, 100} top-CIS neurons (k=32 rerank, main run).
  Controls per K:
    A. tested-universe random draw (3,518 candidates) - 10,000 replicates
    B. degree-matched draw: for each top-K node, a random tested neuron
       within +/-10% total degree (nearest-degree fallback) - 10,000 reps
  Statistics: empirical p = (1 + #{rep >= obs}) / (1 + n_rep);
              enrichment z = (obs - mean_rep) / sd_rep;
              EN = expected count under each null.
Also: per-super_class enrichment table at K=50 and a descriptive
visual_type breakdown of the top-50.

Run:  py -m src.experiments.run_e12_strong
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from src.data.loaders import PROJECT_ROOT

TABLES = PROJECT_ROOT / "results" / "tables"
PROCESSED = PROJECT_ROOT / "data" / "processed"
N_REP = 10_000
KS = (25, 50, 100)
FOCUS = "visual_centrifugal"


def main() -> None:
    df = pd.read_parquet(TABLES / "e07_annotated.parquet")
    rr = pd.read_parquet(TABLES / "e06_rerank_k32.parquet")

    core = pd.read_parquet(PROCESSED / "neuron_core.parquet")[
        ["root_id", "super_class"]]
    df = df.merge(core, on="root_id", how="left", suffixes=("", "_core"))
    df["sc"] = df["super_class_core"].fillna("unannotated")

    tested = df.set_index("target")
    n_tested = len(tested)
    vc_tested = tested["sc"].eq(FOCUS).to_numpy()
    deg = tested["total_degree"].to_numpy(dtype=float)
    log_deg = np.log10(deg + 1.0)

    results: dict = {"n_tested": int(n_tested),
                     "vc_tested_count": int(vc_tested.sum()),
                     "vc_tested_rate": float(vc_tested.mean())}

    for K in KS:
        top = rr.nlargest(K, "cis_mean")["target"].astype(int).to_numpy()
        sub = tested.loc[top]
        obs = int(sub["sc"].eq(FOCUS).sum())

        rng = np.random.default_rng(2026 + K)
        # Control A: uniform over tested universe
        repA = rng.choice(n_tested, size=(N_REP, K), replace=True)
        cntA = vc_tested[repA].sum(axis=1)

        # Control B: degree-matched (per-slot, +/-10% log-degree, fallback
        # nearest degree). poolB is (N_REP, K): column j = replicate draws
        # for slot j, so sum(axis=1) counts VC hits per replicate.
        order = np.argsort(log_deg)
        sorted_ld = log_deg[order]
        poolB = np.empty((N_REP, K), dtype=np.int64)
        tested_idx = tested.index.to_numpy()
        pos_of = {t: i for i, t in enumerate(tested_idx)}
        for j, t in enumerate(top):
            ld = log_deg[pos_of[t]]
            lo, hi = ld - np.log10(1.1), ld + np.log10(1.1)
            idx_lo = np.searchsorted(sorted_ld, lo, side="left")
            idx_hi = np.searchsorted(sorted_ld, hi, side="right")
            if idx_hi > idx_lo:
                pool = order[idx_lo:idx_hi]
            else:  # fallback: nearest 100 degrees
                pos = np.searchsorted(sorted_ld, ld)
                pool = order[max(0, pos - 50):pos + 50]
            poolB[:, j] = pool[rng.integers(0, len(pool), size=N_REP)]
        cntB = vc_tested[poolB].sum(axis=1)

        pA = (1 + int((cntA >= obs).sum())) / (N_REP + 1)
        pB = (1 + int((cntB >= obs).sum())) / (N_REP + 1)
        zA = (obs - cntA.mean()) / max(cntA.std(ddof=1), 1e-12)
        zB = (obs - cntB.mean()) / max(cntB.std(ddof=1), 1e-12)
        results[f"K{K}"] = {
            "observed_vc": obs,
            "expected_A_tested_universe": float(cntA.mean()),
            "expected_B_degree_matched": float(cntB.mean()),
            "p_A": pA, "p_B": pB, "z_A": float(zA), "z_B": float(zB),
            "enrichment_vs_tested": float(obs / max(cntA.mean(), 1e-12)),
            "enrichment_vs_degree_matched": float(obs / max(cntB.mean(), 1e-12)),
        }
        print(f"[E12] K={K}: obs={obs}  E(A)={cntA.mean():.1f}  "
              f"E(B)={cntB.mean():.1f}  pA={pA:.4f}  pB={pB:.4f}  "
              f"zB={zB:.1f}", flush=True)

    # per-super_class enrichment at K=50 (vs tested universe + degree-matched)
    K = 50
    top = rr.nlargest(K, "cis_mean")["target"].astype(int).to_numpy()
    sub = tested.loc[top]
    rng = np.random.default_rng(77)
    rep = rng.choice(n_tested, size=(N_REP, K), replace=True)
    rows = []
    top_pos = tested.index.get_indexer(top)  # positional ids into tested
    for sc, cnt in tested["sc"].value_counts().items():
        ind = (tested["sc"] == sc).to_numpy()
        obs_n = int(ind[top_pos].sum())
        exp = float(ind[rep].sum(axis=1).mean())
        rows.append({
            "super_class": sc, "observed_top50": obs_n,
            "expected_tested": round(exp, 2),
            "enrichment": round(obs_n / max(exp, 1e-12), 2),
            "tested_count": int(cnt),
        })
    results["per_class_top50"] = sorted(
        rows, key=lambda r: -r["enrichment"])

    # descriptive visual_type breakdown of top-50
    results["top50_visual_type"] = (sub["visual_type"].value_counts()
                                    .head(15).to_dict())
    results["top50_names"] = sub["name"].head(50).tolist()

    (TABLES / "e12_strong_results.json").write_text(json.dumps(results, indent=2))
    print(json.dumps({k: v for k, v in results.items()
                      if not k.startswith("top50_names")}, indent=2))


if __name__ == "__main__":
    main()
