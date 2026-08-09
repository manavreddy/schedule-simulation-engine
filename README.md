# Settlement Feasibility & Fee Engine — Take-home

Welcome, and thanks for taking the time. The full problem is in
[`ASSIGNMENT.md`](./ASSIGNMENT.md). This README is just orientation.

## The task in one line

Given a client's escrow account, a settlement offer, and a creditor's rules,
decide whether the offer is affordable (and schedule it, collecting our fee as
early as allowed) or — if not — compute the minimum extra funding needed.

## Setup

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

## Layout

```
hiring_takehome/
├── ASSIGNMENT.md            # full specification — read this
├── feasibility/
│   ├── models.py            # data models, JSON loaders, date/EOM helpers (provided)
│   ├── engine.py            # evaluate_offer entry point, Result / ScheduleRow dataclasses
│   ├── utils.py             # cadence generation, floor computation, round-half-up
│   ├── generators.py        # payment schedule generation (even, balloon, staircase)
│   ├── simulator.py         # day-by-day SDA balance simulation
│   └── solvers.py           # binary search for min lump sum / monthly increment
├── cases/                   # four example cases (client.json / offer.json / creditor_rules.json)
│   ├── case1_feasible_even
│   ├── case2_infeasible_minima
│   ├── case3_balloon
│   └── case4_tiers
├── tests/
│   ├── test_smoke.py        # scaffolding sanity tests (pass out of the box)
│   └── test_cases.py        # example expectations — make these pass, then add your own
├── run.py                   # python run.py cases/<case>
└── requirements.txt
```

## Run

```bash
# evaluate a single case (prints the Result as JSON)
python run.py cases/case1_feasible_even

# tests
pytest -q
```

Out of the box, `tests/test_smoke.py` passes and `tests/test_cases.py` fails —
the latter is your target. Go beyond those four cases with your own tests.

## What to submit

Your implementation, your tests, and a short README section describing:
- your approach and the alternatives you considered,
- **your interpretation of the payment shapes** (even / staircase / balloon — we
  left these loosely defined on purpose),
- assumptions you made, and known edge cases / limitations.

Budget ~5–6 hours. Prefer a correct, well-tested core over breadth. When in
doubt, write down your assumption and keep going.

---

## Approach

The engine determines the best feasible schedule by evaluating possible shapes and term lengths, prioritizing the early collection of our program fee.

1. **Determine allowed shapes:** For each candidate term length `k` (from 1 to `max_k`), the engine checks the creditor rules. If `even_pays` is true, it generates an even schedule. Otherwise, if `is_ballooning_allowed` is true, it generates a balloon schedule. If neither is set, it generates heuristic staircase schedules respecting `max_segments`.
2. **Check feasibility and collect fees:** Each generated schedule candidate is passed to the simulator. The simulator steps chronologically through the SDA ledger, ensuring the balance never drops below zero while greedily collecting the program fee as early as possible on or after the first creditor payment.
3. **Select the optimal schedule:** All feasible schedules are compared based on their fee collection profile. A lexicographical comparison is used to strictly prefer schedules that collect more fee on earlier dates.
4. **Calculate minimum additional funds (if infeasible):** If no schedule is feasible, the engine uses binary search to find the minimum upfront lump sum or the minimum monthly increment that would satisfy the constraints.

---

## Assumptions

1. **Cadence includes the horizon only when it fits the pattern.**
   `last_draft_date` joins the cadence only if it matches the monthly recurrence (EOM→EOM or same day-of-month). Otherwise it acts purely as a scheduling bound.

2. **Creditor payments may start on any consecutive cadence dates.**
   "Starting at `first_payment_date`" defines where the cadence begins, not where creditor payments must begin. Payments are placed on the last `k` cadence dates, allowing earlier dates to serve as fee-only months.

3. **Program fees are collected greedily on every valid date.**
   To satisfy the objective of front-loading program fees, the simulator greedily collects as much program fee as the available SDA balance allows on every cadence date, starting from the first creditor payment date.

4. **`even_pays` takes precedence over `is_ballooning_allowed`.**
    If both flags are true, `even_pays` wins.

5. **Lump sum is placed on `first_draft_date`.**
   An earlier lump is "weakly more useful" per the assignment. The engine uses the earliest point where cash enters the SDA.

6. **Staircase steps are placed heuristically to favor front-loading.**
   The assignment doesn't prescribe where steps should go under the `max_segments` rule. Rather than exhaustively searching all possible partitions (which scales poorly), the engine assumes steps should be deferred: early payments are locked to their minimum floors, and the remainder is pushed into a uniform final segment. If the early floors alone require too many segments, they are flattened to the highest required floor.
