# Viva Questions & Model Answers
## Constraint-Aware Batching Algorithm (CABA) for Courier Deliveries

---

## Section A — Problem & Motivation

**Q1. What real-world problem does this project solve?**
Naive delivery batching (grouping orders purely by geographic proximity) can
violate delivery deadlines, mix incompatible products (e.g. frozen + hot
food), overload a single rider, or force a rider to wait for an order that
isn't ready. This project builds a batching system that reduces travel
distance *while never breaking these operational promises*.

**Q2. Why can't you just use the shortest-path / minimum-distance batch every time?**
Because minimum distance is only one of several competing goals. A batch
that saves 2 km but delivers a frozen item next to hot food, or forces a
rider to carry 9 heavy boxes, is not usable in practice. The project's core
argument is that distance should be minimized *subject to* hard operational
constraints, not instead of them.

**Q3. Why did you use synthetic data instead of a real dataset?**
No real courier company dataset was available for an academic project. The
synthetic generator (`src/data_generator.py`) produces data with realistic,
justified distributions (category-dependent weight/volume, a minority of
urgent/not-ready/tight-window orders, clustered building locations) rather
than uniform random noise, and uses a fixed seed so results are
reproducible.

---

## Section B — Data & Preprocessing

**Q4. What fields does an order have, and why include `incompatible_group` separately from `product_category`?**
`product_category` (Normal/Fragile/Heavy/Frozen/Hot Food/Chemical) captures
broad conflicts (e.g. Frozen vs Hot Food). `incompatible_group` captures
finer conflicts *within* the same category — e.g. two Frozen orders from
different cold-chain vendors that still can't share one insulated bag. This
demonstrates the compatibility system isn't hard-coded to only one level of
granularity.

**Q5. How do you guarantee reproducibility?**
Every random draw uses `numpy.random.default_rng(seed)` with a fixed
`config.RANDOM_SEED = 42`. Riders use `seed + 1` (a different stream so
rider randomness doesn't correlate with order randomness), and disruption
scenarios use `seed + 100 / + 200`. Running the generator twice on the same
machine produces byte-identical CSVs.

**Q6. What cleaning happens in preprocessing?**
Datetime columns are parsed from strings to `pandas.Timestamp`; weight/volume
are clipped to a small positive minimum to guard against zero/negative
values; rows missing required fields (`order_id`, coordinates, deadline)
are dropped with a logged warning count — the pipeline never silently
proceeds with malformed rows.

---

## Section C — Constraints & Compatibility

**Q7. Walk me through how a batch gets rejected for incompatibility.**
`check_batch_compatibility()` checks every pairwise combination of orders in
the candidate batch against `COMPATIBILITY_MATRIX` (a symmetric lookup
table). If any pair is disallowed (e.g. Frozen+Hot Food), it returns a
`ConstraintResult(passed=False, reason="...")` with the specific order IDs
and category names named in plain English — the caller never has to guess
why.

**Q8. Why is the compatibility matrix a dictionary and not if/else statements?**
The spec explicitly required a "reusable, configurable" system, not logic
hard-coded into one function. A dictionary lookup means adding a new
product category or changing one rule is a one-line edit, and the matrix
can be inspected/audited independently of the code that uses it.

**Q9. What happens if two categories aren't in the matrix at all?**
`_lookup_compatibility()` fails safe — an unknown pair defaults to **not
allowed** rather than silently permitting an unconfigured combination. This
is a deliberate safety choice: an unrecognised product pair should require
explicit sign-off, not be assumed benign.

**Q10. How is rider capacity checked?**
`check_capacity()` sums the batch's total weight and volume and compares
against `rider["capacity_kg"]` / `capacity_volume`, and also checks the
order count against `max_orders_per_batch`. All three are independent hard
limits — exceeding any one rejects the batch.

**Q11. What does "pickup readiness" mean and how is it enforced?**
An order might not be physically ready when a rider arrives (e.g. food
still cooking). `check_pickup_readiness()` computes how long the rider
would have to wait past the batch's start time; if that exceeds
`MAX_WAITING_TIME_MIN` (15 minutes), the order is excluded rather than
forcing the rider to idle.

**Q12. Why is there a "deadline safety buffer" instead of just checking against the raw deadline?**
Real deliveries have small, unmodelled variance (a slightly longer lift
wait, a slower elevator). A 5-minute buffer (`DEADLINE_SAFETY_BUFFER_MIN`)
means CABA only accepts batches with some slack, not ones that are
razor-thin against the promise.

---

## Section D — Algorithm Design (CABA)

**Q13. Explain the CABA algorithm end-to-end in your own words.**
Orders are sorted URGENT-first, then by earliest pickup-ready time. For
each order, CABA checks every currently open batch (one per active rider)
against all hard constraints in order: capacity → compatibility → max
stops → readiness → deadline → workload. Among all batches where insertion
is feasible, it picks the one with the lowest Batch Score. If no open batch
works, it tries opening a new batch with the nearest unused rider. If
literally no rider can take the order, it's deferred to the next pickup
round; if no rider has shift time left, it's reported unassigned with a
reason.

**Q14. Why not solve this as an exact optimization problem (e.g. an ILP)?**
Because it's a variant of the multi-depot, multi-trip vehicle routing
problem with time windows (MDMTVRPTW), which is NP-hard. Solving it exactly
for 1,000 orders and 55 riders would not finish in interactive time inside
a dashboard. A greedy constructive heuristic with explicit constraint
checking is the standard, explainable approach used by real production
courier systems, and is appropriate for a real-time academic prototype.

**Q15. What is the Batch Score, and why does it exist?**
```
Batch Score = distance_cost
            + deadline_risk_penalty
            + workload_penalty
            + waiting_time_penalty
            − urgent_priority_bonus
```
It's how CABA chooses *among multiple feasible* options — lower is better.
It exists because the project explicitly forbids optimizing for distance
alone; deadline risk, workload, and waiting time all pull the score in a
direction that keeps the algorithm honest about trade-offs, and urgent
orders get a bonus that biases them toward the best available batch.

**Q16. Are hard constraints ever included in the score?**
No — that's a critical design decision. If a batch violates capacity or
compatibility, it is rejected outright before scoring is even computed. The
score only ranks *already-feasible* options. This guarantees the priority
order from the spec: (1) no product violations, (2) no capacity violations,
(3) no deadline violations, (4) reasonable workload, (5) reduced distance.

**Q17. Why does CABA process orders "urgent-first, then earliest-ready"? Could you choose a different order?**
Yes — this is one reasonable priority policy, not the only valid one. It
was chosen because urgent orders have the least slack and should get first
access to the best batches while options are still open. A different
tie-break (e.g. shortest-deadline-first, or fairness-weighted) would
change *which* specific orders end up unassigned when capacity is tight,
but wouldn't change the fact that hard constraints are still enforced.

**Q18. What is a "pickup round," and why did you add multi-round simulation?**
A round is one pickup trip. `max_orders_per_batch` caps a single trip, not
a rider's whole day. Without multi-round simulation, each rider could only
ever complete one batch, so with 55 riders capped at 4-9 orders each, only
~300 of 1,000 orders could ever be served — that's not how a real shift
works. The multi-round loop lets a rider finish a batch, become available
again (`available_at = batch_start + travel_time`), and pick up more
orders until their shift ends.

**Q19. What happens to an order that no rider can ever serve?**
It is never silently dropped. It appears in `unassigned_order_ids` with an
explicit reason string (e.g. "Deadline violation: ORD00123 predicted
delivery ... misses promised deadline ... late by 214.3 min"), which is
what populates `reports/failure_analysis.csv`.

---

## Section E — Baseline & Fair Comparison

**Q20. How is the baseline different from CABA, mechanically?**
The baseline also uses nearest-neighbour proximity and respects capacity
during assignment, but it does **not** check compatibility, deadlines,
readiness, or workload before committing a batch — it only measures and
counts those as violations afterward. It's a "naive but safe" system: it
never crashes, but it doesn't stop itself from making bad decisions.

**Q21. Why must the baseline and CABA use identical input data and routing model?**
So that any difference in the results is attributable *only* to the
batching logic, not to different assumptions about distance, speed, or
demand. Both call the exact same `src/routing.py` functions and consume
the exact same `orders`/`riders` DataFrames per scenario.

---

## Section F — Routing & Workload

**Q22. What distance metric do you use, and what are its limits?**
Haversine great-circle distance between synthetic lat/lon coordinates. It's
a straight-line distance, not road distance, so it underestimates real
travel by roughly the "circuity factor" of the road network (commonly
1.2–1.4x in dense cities). This is disclosed in `docs/limitations.md`; it
doesn't bias the *comparison* since both algorithms use the same model.

**Q23. How is travel time estimated?**
`distance_km / AVERAGE_SPEED_KMPH × 60`, multiplied by a `delay_multiplier`
for disruption scenarios (e.g. 1.75x for the travel-delay scenario). Fixed
per-stop building access delay and per-order service time are added on top.

**Q24. How are stops within a batch sequenced?**
A nearest-neighbour heuristic starting from the hub: repeatedly visit the
closest unvisited stop. It's not a solved Travelling Salesman Problem, so
it's not guaranteed optimal, but it's fast and explainable — appropriate
given the batch sizes involved (typically ≤6 stops).

**Q25. What is the Rider Workload Score, and what does each term mean?**
```
workload_score = service_time + access_time + waiting_time + handling_time
```
`service_time`: time to hand over each package. `access_time`: distinct
stops × building access delay. `waiting_time`: minutes the rider waits for
not-yet-ready orders. `handling_time`: extra overhead for fragile/heavy/
frozen items (careful handling, insulated bags). It's reported *separately*
from distance so a reader can't miss "did this optimization dump extra
burden on the rider?"

**Q26. What are the LOW/MEDIUM/HIGH/EXCESSIVE bands for?**
They translate a raw minutes figure into an operationally meaningful label
for dispatch staff. Any batch scoring at or above the EXCESSIVE threshold
(210 minutes) is rejected by CABA outright — this is the concrete,
measurable expression of "frontline worker protection" required by the
spec.

---

## Section G — Disruption Handling

**Q27. What are the three disruption scenarios and how is each implemented?**
- **A. Rider capacity loss**: a random 25% of riders are marked
  `UNAVAILABLE` in the riders DataFrame.
- **B. Travel delay**: a 1.75x multiplier is applied throughout routing/time
  calculations — no data is mutated, only the calculation.
- **C. Urgent demand surge**: 15% of non-urgent orders are converted to
  `URGENT` with a tightened `promised_deadline`.

**Q28. How does CABA "recover" when a rider becomes unavailable mid-fleet?**
There's no special recovery code — it falls out of the normal round-based
loop. An unavailable rider is simply excluded from `rider_lookup` at the
start, so every order that would have gone to them is naturally
reconsidered against the remaining active riders in the same round, or
carried to the next round. This is tested directly in
`test_caba_reassigns_when_rider_becomes_unavailable`.

**Q29. Which disruption hurt performance the most, and why?**
Rider Capacity Loss and Travel Delay both hurt on-time completeness the
most (327 unassigned orders vs 182 on a normal day), because both directly
shrink effective fleet throughput. Urgent Demand Surge left a similar count
unassigned to the normal day (183) because it doesn't reduce capacity — it
only reshuffles which orders are time-critical.

---

## Section H — Evaluation & Results

**Q30. What were the actual measured results on the Normal Day scenario?**
Baseline: ~4,148 km total distance, 302 deadline / 115 product / 154
readiness / 92 workload violations, 76.2% on-time rate, 0 unassigned.
CABA: ~3,468 km (−16.4%), 0 violations of any kind, 100% on-time rate, 182
unassigned orders (deadline-infeasible). Average rider workload dropped
from ~230 min to ~47 min.

**Q31. Isn't leaving 182 orders unassigned a failure?**
It's a disclosed trade-off, not a hidden failure. Those orders are
deadline-infeasible for *any* rider given the fleet's actual capacity —
the baseline "solves" this by delivering them late anyway (hence its 302
deadline violations), while CABA refuses to make a promise it can't keep.
Which behaviour is "better" depends on business priorities: CABA optimizes
for reliability, the baseline optimizes for raw coverage.

**Q32. Did reducing distance increase rider workload?**
No — the opposite was observed. CABA's average *and* maximum rider
workload were both lower than the baseline's in every scenario, because
CABA explicitly rejects batches that would push workload into the
EXCESSIVE band, while the baseline has no such check. Efficiency and
worker protection improved together here, not at each other's expense.

**Q33. How do you know these numbers aren't fabricated?**
`run_experiments.py` actually executes both algorithms against the same
loaded dataset and writes the measured output to
`reports/experiment_results.csv`; nothing is typed in by hand. The
notebook (`notebooks/experiment.ipynb`) is also pre-executed with real
output cells, and the full pytest suite passes, confirming the underlying
constraint logic behaves as specified.

**Q34. What metrics did you use for comparison, and why so many?**
15 metrics spanning distance, batch structure, every violation category,
workload (average and maximum), on-time rate (overall and urgent-only),
unassigned count, and execution time. A single metric like "distance
saved" alone would hide the trade-offs (e.g. it wouldn't show that CABA
achieves that saving partly by declining infeasible orders) — the full set
is needed to tell an honest story.

---

## Section I — Testing

**Q35. What are the 5 required failure/edge cases, and where are they tested?**
1. Rider capacity exceeded → `tests/test_capacity.py`
2. Deadline cannot be met → `tests/test_deadline.py`
3. Incompatible products → `tests/test_compatibility.py`
4. Pickup order not ready → `tests/test_readiness.py`
5. Rider becomes unavailable → `tests/test_disruption.py`

**Q36. Give an example of a specific test and what it proves.**
`test_frozen_and_hot_food_incompatible` constructs one Frozen order and one
Hot Food order, calls `check_pair_compatibility()`, and asserts the result
fails with both category names present in the reason string — proving both
that the rule is enforced and that the explanation is meaningful, not just
a boolean.

**Q37. Why test constraint functions directly instead of only testing the whole algorithm?**
Unit-testing `constraints.py` in isolation (with hand-built `pd.Series`
objects, not the full dataset) makes failures traceable to one specific
rule rather than needing to debug the entire 1,000-order pipeline. It also
runs in milliseconds instead of seconds.

---

## Section J — Limitations & Critical Thinking

**Q38. What's the single biggest limitation of this project, and how would you address it in a real deployment?**
The single central hub assumption combined with straight-line distance is
the biggest gap from reality. A production system would need multiple
pickup hubs and real road-network routing (via a maps API), which would
change the absolute distance/time numbers, though the *relative* comparison
between baseline and CABA would likely hold directionally.

**Q39. If distance savings varied between 16% and 33% across scenarios, which number should a business expect?**
None of them as a fixed guarantee — the range itself is the finding. CABA's
efficiency gain adapts to operating conditions (it's higher precisely when
capacity is under more pressure, e.g. Disruption A/B), so a real deployment
should expect a range conditioned on demand/capacity ratio, not a single
constant percentage.

**Q40. What would you do differently if you had more time?**
Add an escalation path for unassigned orders (on-demand gig riders,
proactive customer notification of a revised window) instead of leaving
them permanently unserved; support multiple pickup hubs; replace
nearest-neighbour sequencing with a small exact TSP solver for batches
under ~8 stops; and calibrate distance/speed against real road-network
data instead of Haversine.

---

## Quick-Reference: One-Line Answers

| Question | One-line answer |
|---|---|
| Language/stack? | Python 3.11, Pandas, NumPy, Plotly, Streamlit, pytest |
| Core algorithm type? | Greedy constructive heuristic with multi-objective scoring |
| Hard constraints? | Capacity, compatibility, readiness, deadline, workload, max stops |
| Distance metric? | Haversine great-circle distance |
| Random seed? | 42 (`config.RANDOM_SEED`) |
| Dataset size? | 1,000 orders, 55 riders, 40 buildings |
| # of disruption scenarios? | 3 (rider loss, travel delay, urgent surge) |
| # of pytest tests? | 23, all passing |
| Normal-day distance saved? | ~16.4% |
| Normal-day violation count (CABA)? | 0 |
| Normal-day on-time rate (CABA)? | 100% |
| Biggest trade-off? | Reliability (CABA) vs coverage (baseline) |
