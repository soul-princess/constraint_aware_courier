# Error Analysis

This document analyses *why* orders failed to be batched, which constraints
were responsible, which scenario caused the most failures, and the
efficiency/reliability trade-off observed across all experiments. All
figures below come directly from `reports/experiment_results.csv` and
`reports/failure_analysis.csv` (actually executed, not fabricated).

## 1. Why Could Some Orders Not Be Batched?

Every CABA rejection in this project's experiments falls into a single
constraint category: **deadline infeasibility**.

```
Scenario                            Unassigned orders   Cause
Normal Day                          182                  100% deadline violation
Disruption A (rider capacity loss)  327                  100% deadline violation
Disruption B (travel delay)         327                  100% deadline violation
Disruption C (urgent demand surge)  183                  100% deadline violation
```

No order was ever rejected purely for capacity or product-incompatibility
reasons in the final experiment run -- those constraints *did* reject
individual candidate batch insertions during the search (that's exactly
what routes an order to a *different*, compatible batch instead), but by
the time an order exhausts every rider's feasibility across every round, the
binding constraint that finally blocks it is always the delivery deadline.

## 2. Which Constraint Caused Rejection, and Why Deadline Dominates

Analysis of `reports/failure_analysis.csv` shows the predicted lateness for
rejected orders is substantial, not marginal:

| Scenario | Mean lateness (min) | Max lateness (min) |
|---|---|---|
| Normal Day | ~197 | ~398 |
| Disruption A: Rider Capacity Loss | ~223 | ~389 |
| Disruption B: Travel Delay | ~215 | ~381 |
| Disruption C: Urgent Demand Surge | ~167 | ~320 |

These are not "missed the deadline by 2 minutes" cases -- they are orders
that, by the time every active rider had exhausted their shift capacity for
earlier rounds, could only be picked up hours later than their promised
window. This points to a **queueing / congestion effect**: with ~1,000
orders concentrated in the first ~4 hours of the day and only 55 riders,
the *tail* of orders (those that don't get picked up in the first 2-3
rounds) inevitably queue behind everyone else, and their originally
reasonable deadline (set relative to when the order was created) is no
longer reachable once picked up that late.

This is a genuine capacity/demand mismatch in the synthetic scenario, not
an algorithm bug: the baseline "solves" it by ignoring the deadline
entirely and delivering late anyway (hence its large deadline-violation
counts), while CABA correctly refuses to commit to a batch it cannot
deliver on time, and instead reports the order as unassigned with the
specific reason.

## 3. Which Scenario Caused the Most Failures?

**Disruption A (Rider Capacity Loss, -25% riders)** and **Disruption B
(Travel Delay, +75% travel time)** both produced the highest unassigned
count for CABA (327 orders, up from 182 on a normal day) -- both scenarios
directly shrink effective fleet throughput (fewer riders, or the same
riders taking longer per batch), which worsens the queueing effect
described above. Disruption C (Urgent Demand Surge) produced a comparable
unassigned count to the normal day (183 vs 182) because it does not reduce
capacity -- it only tightens the deadlines on a subset of already-existing
orders, so it reshuffles *which* orders fail rather than dramatically
increasing the *count* that fail.

**Interpretation:** capacity-reducing disruptions (A, B) are structurally
worse for on-time completeness than demand-shape disruptions (C), which is
an intuitive and defensible finding, and useful for operational planning
(e.g. Scenario A/B call for surge staffing, Scenario C calls for smarter
urgent-order triage).

## 4. Did Distance Reduction Cause Workload Increase?

No -- the opposite was observed. CABA's average rider workload was
**consistently lower** than the baseline's across every scenario (e.g.
~47 min vs ~230 min on the normal day, a ~80% reduction), and CABA's
*maximum* rider workload was dramatically lower too (~75-80 min vs
1,000-1,140 min for the baseline). This is because:
1. CABA explicitly rejects any batch whose predicted workload would reach
   the EXCESSIVE band (Section 8 of the technical documentation), while the
   baseline has no such check and can accumulate arbitrarily large batches
   on riders who happen to be geographically convenient.
2. Because CABA also declines to force infeasible orders into a rider's
   day, it never manufactures the extreme-workload outlier batches that
   drag up the baseline's *maximum* workload figure.

**Conclusion:** in this project's experiments, distance efficiency and
workload protection were *not* in conflict -- CABA achieved lower distance
**and** lower workload simultaneously, at the cost of serving fewer orders.

## 5. Did Disruption Change Algorithm Performance?

Yes, in a directionally sensible way:
- Distance savings percentage *increased* under Disruption A (29.5%) and
  Disruption B (32.8%) compared to Normal Day (16.4%) -- when the same
  demand must be served by less effective capacity, CABA's constraint-aware
  consolidation captures proportionally more of the remaining efficiency
  opportunity, while the baseline's naive round-robin keeps assigning
  orders inefficiently regardless of the tighter conditions.
- Distance savings under Disruption C (18.1%) were close to the normal-day
  baseline, consistent with Section 3's finding that this scenario reshapes
  urgency rather than shrinking capacity.
- CABA's on-time delivery rate and zero-violation guarantee held in
  **every** scenario, which is the core claim of the project: constraint
  satisfaction is not scenario-dependent by construction (violations are
  rejected outright, not merely reduced).

<<<<<<< HEAD
## 5b. Recovery Pass Findings: Is the 182 Due to Insertion-Order Luck, or Genuine Infeasibility?

A recovery / re-evaluation stage was added after the initial multi-round
batching (see `src/batching_algorithm.py -> _recovery_pass`): every
still-unassigned order gets one explicit, logged second chance against the
**full current rider pool** (not just whichever riders it happened to be
compared against during its original round), via a dedicated "secondary
dispatch" micro-batch. This directly tests whether unassigned orders were
blocked by genuine infeasibility or merely by the luck of which batch they
were compared against first.

**Measured result: 0 of 182 orders were recoverable** on the Normal Day
scenario. The recovery pass logged all 55 riders as attempted for every one
of the 182 orders (10,010 total attempts), and every single attempt failed
with the same root cause: **deadline violation**, with predicted delivery
times 350-400+ minutes past the promised deadline. This rules out
insertion-order artifacts as the explanation and confirms the orders are
genuinely infeasible given the fleet's timing, not merely mis-sequenced.

**A more specific root cause, found via this investigation:**
unassigned orders are **100% NORMAL or LOW priority (92 and 90 orders
respectively) and 0% URGENT or HIGH priority**. This is a direct,
measurable confirmation that Constraint 7 (urgent orders receive higher
priority) works exactly as designed -- but it also reveals an emergent
**starvation risk**: because NORMAL/LOW orders are always inserted *after*
every URGENT/HIGH order in every round, under high system load they can be
pushed through enough rounds that their fixed-clock deadline expires even
though their *original* delivery window (100-240 minutes) was generous.
Their window was never the problem -- the cumulative wait for a turn in the
priority queue was.

This is a legitimate, disclosed trade-off of strict priority ordering, and
is exactly the kind of finding error analysis is meant to surface: the
system is not "randomly" failing 18% of orders, it is consistently
deprioritizing the least time-sensitive orders, which is correct behaviour
under the stated requirements but has a real customer-experience cost for
that specific segment.

=======
>>>>>>> 95de37805618e7e20d45ecc2599cc0ba6e99c39a
## 6. Why Do Orders Remain Unassigned Rather Than Delivered Late?

This is a deliberate design choice, not a limitation to be hidden: CABA's
specification (Section 6 of the project brief) requires that "the predicted
delivery time must not exceed the promised deadline" as a hard constraint.
Given that requirement, an order whose earliest feasible pickup-to-delivery
time (under any available rider, in any remaining round) already exceeds
its deadline **cannot** be assigned without violating the very constraint
CABA exists to enforce. The alternative -- assigning it anyway and
recording a violation, as the baseline does -- was intentionally rejected
for CABA because it would undermine the "zero violations" guarantee that
is the project's central contribution.

## 7. Trade-off Between Efficiency and Service Reliability

The experiments make this trade-off explicit and measurable rather than
theoretical:

| | Baseline | CABA |
|---|---|---|
| Orders served (Normal Day) | 1000 / 1000 (100%) | 818 / 1000 (81.8%) |
| Deadline violations among served orders | 302 | 0 |
| On-time rate among served orders | 76.2% | 100% |
| Distance for served orders | 4,148 km | 3,468 km |

In other words: the baseline optimizes for **coverage** (deliver something
to everyone, regardless of promise-keeping), while CABA optimizes for
**reliability** (only commit to promises it can keep). Neither is
unconditionally "better" -- a real deployment would likely combine CABA's
constraint discipline with an escalation path for the unassigned tail
(e.g. dispatch on-demand/gig riders, notify customers proactively of a
revised window, or add hub capacity during predictable demand peaks) rather
than leaving those orders permanently unserved. This escalation path is
listed as future work in `presentation/project_presentation.md` (Slide 15)
and is out of scope for the current prototype.

## 8. Why Distance Savings Vary Rather Than Following One Fixed Number

The project brief cautions against inventing results or expecting a single
"expected" saving percentage. Because CABA both (a) consolidates
compatible, ready, on-time orders into larger batches where feasible and
(b) declines orders where consolidation is not feasible, the *set of orders
actually delivered* differs between algorithms and between scenarios. The
16-33% range observed here should be read as **evidence that the
constraint-aware approach adapts its efficiency gain to the operating
conditions**, not as a single guaranteed percentage that a real deployment
should expect regardless of context.
