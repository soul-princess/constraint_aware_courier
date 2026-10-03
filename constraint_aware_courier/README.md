# Constraint-Aware Batching Algorithm for Time-Sensitive and Incompatible E-Commerce Courier Deliveries

A complete, end-to-end academic prototype: synthetic data generation, a
naive baseline batching algorithm, the proposed **Constraint-Aware Batching
Algorithm (CABA)**, a routing/workload simulation layer, an evaluation
framework, a Streamlit dashboard, a pytest test suite, and full
documentation.

## Problem Statement

An e-commerce courier service delivers orders to gated apartments and
office complexes. Naive distance-based batching can violate promised
delivery times, pickup readiness, product compatibility, rider capacity, or
create unreasonable workload for delivery riders. This project builds a
working prototype that groups compatible orders for riders while respecting
all of these constraints simultaneously, quantifies the distance saved
*without* violating service or product conditions, and compares against a
simple baseline on both normal and disrupted operating days.

## Objectives

1. Implement a data-driven, explainable product-compatibility system.
2. Implement a naive baseline (nearest-neighbour, capacity-only) for fair comparison.
3. Implement CABA: a constraint-aware, multi-objective batching algorithm.
4. Protect frontline riders via explicit, measurable workload limits.
5. Simulate realistic routing (Haversine distance, no live maps API).
6. Run real experiments (normal day + 3 disruption scenarios) and report
   real, measured metrics -- never fabricated results.
7. Ship a working Streamlit dashboard, full test suite, and documentation.

## Features

- Configurable, reusable product-compatibility matrix + fine-grained group
  conflicts, with human-readable rejection reasons.
- Multi-round, full-operating-day simulation (riders complete several
  batches per shift, not just one).
<<<<<<< HEAD
- **Pluggable routing layer** (`src/routing.py`): Haversine distance is the
  active default; a documented (not-yet-implemented) OSRM/OpenRouteService
  hook exists for future real-road routing, selectable with one config
  change and no changes to any calling code.
- **Recovery / re-evaluation queue** (`src/batching_algorithm.py`): every
  order left unassigned after the main batching pass gets one more
  explicit, fully logged attempt against the *entire* current rider pool
  (not just the riders it was compared against during its original round)
  before being permanently marked unassigned -- without ever relaxing a
  hard constraint to force the assignment through.
- Explicit Rider Workload Score with LOW/MEDIUM/HIGH/EXCESSIVE banding.
- Three disruption scenarios: rider capacity loss, travel delay, urgent
  demand surge.
- Full pytest suite covering 5 required failure/edge cases plus the
  routing-provider and recovery-queue additions (**34 tests, all passing**).
- Streamlit dashboard with scenario/algorithm selectors, a side-by-side
  Baseline-vs-Proposed workflow table, a rider-workload chart with a
  "maximum allowed" reference line, a "Why was this order rejected?" table,
  order & batch tables, and 6+ interactive visualizations.
=======
- Explicit Rider Workload Score with LOW/MEDIUM/HIGH/EXCESSIVE banding.
- Three disruption scenarios: rider capacity loss, travel delay, urgent
  demand surge.
- Full pytest suite covering 5 required failure/edge cases (23 tests, all passing).
- Streamlit dashboard with scenario/algorithm selectors, order & batch
  tables, and 6+ interactive visualizations.
>>>>>>> 95de37805618e7e20d45ecc2599cc0ba6e99c39a

## Architecture

```
constraint_aware_courier/
├── app.py                     # Streamlit dashboard
├── run_experiments.py          # Runs all experiments, writes reports/
├── requirements.txt
├── config.py                   # All tunable parameters (single source of truth)
├── pytest.ini
├── data/
│   ├── raw/                    # Generated orders.csv, riders.csv
│   ├── processed/
│   └── scenarios/
├── src/
│   ├── data_generator.py       # Synthetic data generation (reproducible seed)
│   ├── preprocessing.py        # Load & clean datasets
│   ├── constraints.py          # Compatibility matrix + all hard constraints
│   ├── workload.py             # Rider Workload Score (frontline protection)
<<<<<<< HEAD
│   ├── routing.py              # Pluggable routing layer (Haversine default, OSRM future hook)
│   ├── baseline.py             # Naive nearest-neighbour baseline
│   ├── batching_algorithm.py   # CABA + recovery/re-evaluation queue
│   ├── disruption.py           # 3 disruption scenario generators
│   ├── evaluation.py           # Metrics + baseline-vs-CABA comparison
│   └── visualization.py        # Plotly chart builders
├── tests/                      # pytest suite (5 required edge cases + routing + recovery)
=======
│   ├── routing.py              # Haversine distance + travel-time approximation
│   ├── baseline.py             # Naive nearest-neighbour baseline
│   ├── batching_algorithm.py   # CABA -- the core algorithm
│   ├── disruption.py           # 3 disruption scenario generators
│   ├── evaluation.py           # Metrics + baseline-vs-CABA comparison
│   └── visualization.py        # Plotly chart builders
├── tests/                      # pytest suite (5 required edge cases)
>>>>>>> 95de37805618e7e20d45ecc2599cc0ba6e99c39a
├── notebooks/experiment.ipynb  # Executed experiment notebook (real outputs)
├── reports/                    # experiment_results.csv, failure_analysis.csv, user_feedback.csv
├── docs/                       # field_workflow, technical_documentation, methodology, limitations, error_analysis
└── presentation/               # 15-slide presentation content
```

## Installation

```bash
cd constraint_aware_courier
pip install -r requirements.txt
```

## Generate the Dataset

```bash
python -m src.data_generator
```

This writes `data/raw/orders.csv` (1,000 orders) and `data/raw/riders.csv`
(55 riders), using a fixed random seed for full reproducibility.

## Run the Experiments

```bash
python run_experiments.py
```

This runs the Normal Day scenario plus all 3 disruption scenarios, for both
the Baseline and CABA, and writes:
- `reports/experiment_results.csv` -- full metric comparison table
- `reports/failure_analysis.csv` -- itemized reasons for every unassigned order

## Run the Tests

```bash
pytest tests/ -v
```

<<<<<<< HEAD
34 tests covering: rider capacity exceeded, deadline infeasibility,
product/group incompatibility, pickup-readiness violations, rider
unavailability / disruption reassignment, the pluggable routing-provider
layer, and the recovery/re-evaluation queue.
=======
23 tests covering: rider capacity exceeded, deadline infeasibility,
product/group incompatibility, pickup-readiness violations, and rider
unavailability / disruption reassignment.
>>>>>>> 95de37805618e7e20d45ecc2599cc0ba6e99c39a

## Launch the Streamlit Dashboard

```bash
streamlit run app.py
```

Use the sidebar to switch between Normal Day / Rider Capacity Loss /
Travel Delay / Urgent Demand scenarios, and between Baseline / CABA /
Compare Both views.

## Run the Experiment Notebook

```bash
jupyter notebook notebooks/experiment.ipynb
```

(An already-executed copy with real output cells is included in this
repository.)

## Expected Outputs (Measured, Not Simulated)

On the bundled synthetic dataset (1,000 orders, 55 riders), a representative
run (see `reports/experiment_results.csv` for exact figures) shows:

| Metric | Baseline | CABA |
|---|---|---|
| Total distance (Normal Day) | ~4,148 km | ~3,468 km (**-16.4%**) |
| Deadline violations | 302 | **0** |
| Product incompatibility violations | 115 | **0** |
| Pickup readiness violations | 154 | **0** |
| Workload violations | 92 | **0** |
| Average rider workload | ~230 min | ~47 min |
| On-time delivery rate | 76.2% | **100%** |
| Unassigned orders | 0 | 182 (trade-off, see below) |

**Honest trade-off:** CABA achieves zero constraint violations and 100%
on-time delivery for every order it assigns, but leaves a portion of orders
unassigned when tight deadlines and fleet capacity make on-time,
constraint-respecting delivery genuinely infeasible. The baseline serves
every order but with substantial violations. This trade-off is discussed in
full in `docs/limitations.md`, `docs/error_analysis.md`, and
`reports/failure_analysis.csv`.

<<<<<<< HEAD
**This is not insertion-order luck.** A dedicated recovery/re-evaluation
pass (`src/batching_algorithm.py -> _recovery_pass`) gives every
unassigned order one more explicit, logged attempt against the *entire*
rider fleet before giving up on it. On the bundled dataset this recovers
**0 of 182** Normal Day unassigned orders (and 0/327, 0/183 in the two most
severe disruption scenarios) -- every attempt is logged in
`reports/failure_analysis.csv`, confirming these orders are genuinely
infeasible, not merely unlucky in which batch they were compared against
first. A further finding from this investigation: **100% of unassigned
orders are NORMAL/LOW priority; 0% are URGENT/HIGH** -- the priority queue
(Constraint 7) is working exactly as designed. See
`docs/error_analysis.md` Section 5b.

=======
>>>>>>> 95de37805618e7e20d45ecc2599cc0ba6e99c39a
## Error Analysis

See `docs/error_analysis.md` for a full breakdown of: why orders could not
be batched, which constraint caused each rejection, which disruption
scenario caused the most failures, whether distance reduction increased
rider workload (it did not -- both improved together), and the explicit
efficiency-vs-reliability trade-off measured across all four scenarios.

## Limitations (Summary -- Full Details in `docs/limitations.md`)

- Synthetic data (no real company dataset was available).
- No real-time GPS or live traffic API -- Haversine distance + configurable
  average speed only.
- Nearest-neighbour route sequencing (not a solved TSP).
- Simplified building-access delay model.
- Simplified, if reasonably comprehensive, product-compatibility rules.
- User validation (`reports/user_feedback.csv`) is clearly labelled
  **simulated**, not real stakeholder feedback.
