#!/usr/bin/env python
"""Independent verification of the E10B final statistics.

Recomputes every E10B-dependent manuscript number from
results/tables/e10b_nulls.csv (the per-null rows) and cross-checks it
against results/tables/e10b_results.json and results/final/e10b_final.json.
Run:  py scripts/verify_e10b_final.py
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
T = ROOT / "results" / "tables"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def main() -> None:
    df = pd.read_csv(T / "e10b_nulls.csv")
    final = json.loads((ROOT / "results" / "final" / "e10b_final.json").read_text())
    obs_d = final["observed"]["cliffs_delta"]
    obs_m = final["observed"]["median_diff"]

    n = len(df)
    p_d = (1 + int((df["cliffs_delta"] >= obs_d).sum())) / (1 + n)
    p_m = (1 + int((df["median_diff"] >= obs_m).sum())) / (1 + n)
    z = (obs_d - df["cliffs_delta"].mean()) / df["cliffs_delta"].std(ddof=1)

    recomputed = {
        "n_nulls": n,
        "delta_mean": round(df["cliffs_delta"].mean(), 4),
        "delta_sd": round(df["cliffs_delta"].std(ddof=1), 4),
        "delta_max": round(df["cliffs_delta"].max(), 4),
        "delta_p95": round(df["cliffs_delta"].quantile(0.95), 4),
        "p_delta": round(p_d, 4),
        "p_median_diff": round(p_m, 4),
        "z_vs_null": round(z, 3),
        "nulls_with_delta_ge_obs": int((df["cliffs_delta"] >= obs_d).sum()),
        "all_degree_verified": bool(df["in_degree_exact_match"].all()
                                    and df["out_degree_exact_match"].all()),
        "status_counts": df["status"].value_counts().to_dict(),
    }
    print("RECOMPUTED FROM e10b_nulls.csv:")
    print(json.dumps(recomputed, indent=2))

    print("\nJSON CONSISTENCY (final vs tables):")
    print("  final/e10b_final.json   sha", sha(ROOT / "results" / "final" / "e10b_final.json"))
    print("  tables/e10b_results.json sha", sha(T / "e10b_results.json"))
    same = json.loads((T / "e10b_results.json").read_text()) == final
    print("  identical content:", same)

    print("\nARCHIVE COPY MATCH (results/e10b/):")
    print("  nulls csv:",
          sha(T / "e10b_nulls.csv") == sha(ROOT / "results" / "e10b" / "e10b_nulls.csv"))

    e09 = json.loads((T / "e09_results.json").read_text())
    print("\nOBSERVED-DELTA PROVENANCE:")
    print("  E09 primary (k=8 screening):", round(e09["cliffs_delta_matched"], 4))
    print("  E10B observed (k=4 panel, same estimator as nulls):", round(obs_d, 4))

    checks = {
        "n==100": bool(n == 100),
        "p_delta matches JSON": bool(abs(p_d - final["empirical_p_delta"]) < 1e-9),
        "p_median matches JSON":
            bool(abs(p_m - final["empirical_p_median_diff"]) < 1e-9),
        "delta_mean matches JSON":
            bool(abs(df["cliffs_delta"].mean() - final["null_delta_mean"]) < 1e-9),
        "degree verified in JSON": bool(final["all_nulls_degree_verified"]),
        "tables==final JSON": bool(same),
    }
    ok = all(checks.values())
    print("\nCHECKS:", ok, json.dumps(checks))
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
