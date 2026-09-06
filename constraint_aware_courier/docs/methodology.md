# Methodology

## Why a Greedy Constructive Heuristic Instead of Exact Optimization?

The problem as specified involves simultaneously satisfying 8 constraint
families (capacity, compatibility, readiness, deadlines, workload, max
stops, urgency, disruption) across 1000+ orders and 50+ riders, with
multiple pickup rounds per rider per day. Formulated as an exact
mixed-integer program, this is a variant of the multi-depot, multi-trip
vehicle routing problem with time windows and side constraints (MDMTVRPTW)
-- known to be NP-hard, and generally solved in industry with either:
1. Metaheuristics (large neighbourhood search, genetic algorithms), or
2. Real-time constructive heuristics with periodic re-optimization.

For an academic prototype that must run interactively inside a Streamlit
dashboard (sub-30-second response expected for the full 1000-order dataset),
a **constructive greedy heuristic with an explicit, auditable scoring
function** is the practical and explainable choice -- and is also the
approach most real-world last-mile courier systems actually use in
production, precisely because it is fast, debuggable, and every rejection
has a plain-English explanation.

## Design Principles

1. **Hard constraints are never "soft-penalized" into acceptance.**
   Capacity and product-compatibility violations receive no score at all --
   a batch that fails them is rejected outright, regardless of how much
   distance it would have saved. This directly implements the spec's
   requirement that CABA "must NOT simply minimize distance."

2. **Multi-round simulation of the full operating day.**
   A rider's `max_orders_per_batch` caps a single *trip*, not their whole
   shift. CABA and the baseline both simulate riders completing repeated
   pickup rounds (bounded by `shift_start`/`shift_end`) so the full
   day's ~1000 orders are realistically distributed across ~50 riders,
   rather than artificially capping total throughput at one round.

3. **Same input data, same routing model, fair comparison.**
   Both the baseline and CABA consume the *exact same* `orders` and
   `riders` DataFrames (including under disruption scenarios) and use the
   *exact same* Haversine-based routing/time model. Any difference in
   results is attributable to the batching *logic*, not to different
   assumptions.

4. **Explainability over marginal optimality.**
   CABA does not guarantee the mathematically optimal set of batches (a
   true optimum would require solving the underlying NP-hard problem
   exactly). It guarantees that every accepted batch satisfies all hard
   constraints, and every rejection is traceable to a specific, logged
   reason -- which is more operationally useful for a courier business than
   an unexplainable black-box optimum.

## Reproducibility

- All random generation uses `numpy.random.default_rng(seed)` with
  `config.RANDOM_SEED = 42` (and small fixed offsets for independent
  streams, e.g. riders use `seed + 1`, disruption scenarios use
  `seed + 100/200`).
- Running `python -m src.data_generator` (or `run_experiments.py`, which
  calls the same loader) on the same machine with the same seed always
  produces byte-identical `orders.csv` / `riders.csv`.

## Threats to Validity

- Synthetic data, while distributionally realistic, cannot capture true
  real-world correlations (e.g. actual traffic patterns, real customer
  address clustering). See `docs/limitations.md`.
- The nearest-neighbour route sequencing within a batch is a heuristic, not
  a solved TSP -- for batches with 3+ stops the true optimal route could be
  marginally shorter.
- The greedy insertion order (urgent-first, then earliest-ready) is one
  reasonable priority policy among several valid alternatives; a different
  tie-breaking rule could shift the exact set of feasible batches.
