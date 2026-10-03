# Field Workflow: How CABA Fits Into Real Courier Operations

This document maps the constraint-aware batching system onto the real
operational workflow of an e-commerce courier service, and highlights
exactly where frontline delivery workers interact with the system.

## End-to-End Workflow

```text
Customer Order
      |
      v
Order Received  ------------------------->  [order_created_time recorded]
      |
      v
Product Prepared (kitchen / warehouse / seller)
      |
      v
Pickup Ready? ------ NO --> order waits, tracked as `pickup_ready_time`
      | YES
      v
Candidate Orders Identified  ------------->  CABA scans nearby ready orders
      |
      v
Compatibility Check  ---------------------->  src/constraints.py
      |  (reject incompatible pairs, explain why)
      v
Capacity Check  ---------------------------->  src/constraints.py
      |  (reject if weight/volume/order-count exceeded)
      v
Deadline Feasibility Check  ----------------->  src/constraints.py + src/routing.py
      |  (reject if predicted delivery misses promised_deadline)
      v
Workload Check  ----------------------------->  src/workload.py
      |  (reject if rider workload would become EXCESSIVE)
      v
Batch Created  ------------------------------>  src/batching_algorithm.py
      |
      v
Rider Assigned  (nearest feasible, lowest Batch Score)
      |
      v
Delivery Sequence  (nearest-neighbour route via src/routing.py)
      |
      v
Delivery Completed
      |
      v
Performance Measurement  --------------------->  src/evaluation.py
```

## Where Frontline Workers Interact With the System

| Stage | Rider-facing touchpoint |
|---|---|
| **Batch Created** | The rider sees the *final* assigned batch -- never an infeasible one. CABA rejects overloaded or incompatible combinations *before* they ever reach the rider's app/handheld. |
| **Rejected Batch (visible to Ops, not the rider)** | Operations staff see the explicit rejection reason (e.g. "Frozen and Hot Food incompatible") in the Streamlit dashboard's Batch Results table, so they can manually resolve edge cases rather than the rider discovering the conflict at the doorstep. |
| **Workload Band (LOW/MEDIUM/HIGH/EXCESSIVE)** | Shown to Ops before dispatch, so a rider is never handed an EXCESSIVE-workload batch. This is the direct, measurable expression of "frontline worker protection" required by the project spec. |
| **Pickup Readiness** | If an order is not ready, the rider is not made to wait at the pickup hub beyond `MAX_WAITING_TIME_MIN` (Section 8/9 of the spec) -- the order is deferred to the next round instead. |
| **Delivery Sequence** | The nearest-neighbour route order is what the rider actually follows on their handheld, minimizing backtracking within the batch. |
| **Disruption Handling** | If a rider goes offline mid-shift (Scenario A), their un-delivered/未-picked-up orders are automatically reconsidered by CABA in the next round against the remaining fleet -- riders are not expected to manually renegotiate their own reassignments. |

## Why This Matters

A naive "minimize distance" batching system can accidentally create batches
that are efficient *on paper* but unreasonable *in practice* -- e.g. 9 heavy
boxes for one rider, or a batch that forces a rider to wait 40 minutes at
pickup for a single late order. By putting the Workload Check and Pickup
Readiness Check *before* a batch is ever dispatched, CABA keeps the
optimization honest: it can only claim distance savings that do not come at
the frontline worker's expense.
