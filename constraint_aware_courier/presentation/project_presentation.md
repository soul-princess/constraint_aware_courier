# Project Presentation: Constraint-Aware Courier Batching (CABA)

*12-15 slide structure. Each slide: Title, Key Points, Suggested Visual, Speaker Explanation.*

---

## Slide 1 -- Title
**Title:** Constraint-Aware Batching Algorithm for Time-Sensitive and Incompatible E-Commerce Courier Deliveries

**Key points:**
- CSE academic project
- End-to-end working prototype (data -> algorithm -> app)

**Visual:** Project logo/title slide with a delivery-route icon.

**Speaker notes:** Introduce the project name, your name, and the one-line
pitch: "A batching system that saves distance without breaking delivery
promises or overloading riders."

---

## Slide 2 -- Problem
**Key points:**
- Naive batching (group by proximity) can violate delivery deadlines,
  mix incompatible products, or overload riders.
- Real courier operations must respect 8+ simultaneous constraints.

**Visual:** Simple diagram of a rider carrying frozen + hot food in one bag with a red X.

**Speaker notes:** Ground the problem in a relatable failure mode before
introducing the solution.

---

## Slide 3 -- Existing Approach (Baseline)
**Key points:**
- Nearest-neighbour, capacity-only batching
- Ignores compatibility, deadlines, readiness, workload
- Implemented and measured in this project, not just described

**Visual:** `plot_distance_comparison` bar chart preview (baseline bar only).

**Speaker notes:** Emphasize that the baseline is a real, working
implementation used for fair comparison -- not a strawman.

---

## Slide 4 -- Proposed Solution (CABA)
**Key points:**
- Constraint-Aware Batching Algorithm
- Greedy constructive heuristic + explicit hard-constraint checks +
  multi-objective scoring
- Rejects rather than commits violations

**Visual:** The field-workflow diagram from `docs/field_workflow.md`.

**Speaker notes:** State the core idea: score-based insertion among
*only* the feasible batches, never among infeasible ones.

---

## Slide 5 -- System Architecture
**Key points:**
- `data_generator -> preprocessing -> baseline/CABA -> routing/workload ->
  evaluation -> Streamlit app`
- Modular `src/` package, `pytest` test suite, `config.py` single source of truth

**Visual:** The folder-tree architecture diagram.

**Speaker notes:** Walk through the pipeline left to right, one module at a time.

---

## Slide 6 -- Dataset
**Key points:**
- 1,000 synthetic orders, 55 riders, 40 buildings (apartments + offices)
- Reproducible (fixed random seed)
- Realistic distributions: urgent orders, frozen/fragile/heavy items,
  not-ready orders, tight delivery windows

**Visual:** `plot_delivery_locations` scatter map.

**Speaker notes:** Explain *why* synthetic data was necessary (no real
company data available) and how distributions were chosen to be realistic.

---

## Slide 7 -- Constraint Model
**Key points:**
- Configurable compatibility matrix (6 product categories)
- Fine-grained `incompatible_group` conflicts
- Capacity, readiness, deadline, workload, max-stops constraints

**Visual:** The compatibility matrix table.

**Speaker notes:** Give one concrete rejection example: "Frozen + Hot Food
-> rejected, here's why."

---

## Slide 8 -- Algorithm (CABA)
**Key points:**
- Priority-ordered insertion (urgent first)
- Batch Score = distance + deadline_risk + workload + waiting -
  urgent_bonus
- Hard constraints rejected outright, never scored

**Visual:** The Batch Score formula, plus a small worked numeric example.

**Speaker notes:** Walk through one order's insertion decision step by step.

---

## Slide 9 -- Baseline Comparison (Methodology)
**Key points:**
- Both algorithms run on the *identical* input data and routing model
- Comparison table: 15 required metrics

**Visual:** `reports/experiment_results.csv` table (Normal Day rows).

**Speaker notes:** Stress fairness of comparison -- same data, same routing,
only the batching logic differs.

---

## Slide 10 -- Normal-Day Experiment
**Key points (actual measured results):**
- CABA: ~16% distance reduction, 0 constraint violations, 100% on-time delivery
- Baseline: more orders served, but hundreds of deadline/compatibility/
  readiness/workload violations

**Visual:** `plot_violation_comparison` + `plot_on_time_comparison`.

**Speaker notes:** Present numbers plainly; do not oversell -- the trade-off
(fewer orders served vs. zero violations) is the interesting finding.

---

## Slide 11 -- Disruption Experiment
**Key points (actual measured results):**
- Scenario A (rider loss -25%): CABA saved ~29% distance
- Scenario B (travel delay +75%): CABA saved ~33% distance
- Scenario C (urgent surge): CABA saved ~18% distance
- CABA maintains 0 violations and 100% on-time rate in every scenario

**Visual:** `plot_scenario_comparison` grouped bar chart across scenarios.

**Speaker notes:** Explain that CABA's relative advantage often *increases*
under disruption, since a rigid baseline routing keeps committing to
now-infeasible batches while CABA adapts.

---

## Slide 12 -- Failure / Edge Cases
**Key points:**
- 5 tested edge cases: capacity exceeded, deadline infeasible, incompatible
  products, pickup not ready, rider unavailable
- All covered by `pytest` (`tests/test_*.py`), all passing

**Visual:** Test suite pass screenshot / summary.

**Speaker notes:** Briefly describe one test in detail (e.g.
`test_caba_reassigns_when_rider_becomes_unavailable`).

---

## Slide 13 -- Results Summary
**Key points:**
- Full metrics table across all 4 scenarios in `reports/experiment_results.csv`
- Distance saved, workload reduced ~80%, unassigned-order trade-off disclosed

**Visual:** Summary scorecard (Dashboard screenshot from the Streamlit app).

**Speaker notes:** Tie back to the objective function priorities stated in Slide 8.

---

## Slide 14 -- User / Stakeholder Validation
**Key points:**
- Validation questionnaire (7 questions) targeting riders, ops staff, managers
- `reports/user_feedback.csv` -- clearly labelled SIMULATED example responses
- Real deployment would require actual field data collection

**Visual:** Questionnaire table.

**Speaker notes:** Be explicit that the feedback shown is simulated, not real.

---

## Slide 15 -- Conclusion & Future Work
**Key points:**
- CABA demonstrates measurable distance savings *without* sacrificing
  service reliability or overloading riders
- Honest limitation: some orders remain unassigned under tight capacity --
  see `docs/limitations.md`
- Future work: multiple pickup hubs, exact/metaheuristic optimization for
  smaller sub-problems, live traffic integration, real user validation

**Visual:** Roadmap arrow graphic.

**Speaker notes:** End on the honest trade-off and a concrete, achievable
next step, rather than overclaiming production-readiness.
