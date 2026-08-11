# """Candidate implementation goes here.

# Implement ``evaluate_offer`` so that it satisfies the rules in ASSIGNMENT.md and
# the example expectations in tests/test_cases.py. The dataclasses below define the
# required OUTPUT shape (see ASSIGNMENT.md "Output"). You may add helpers, modules,
# or rewrite internals freely, but keep ``evaluate_offer``'s signature and the
# serialized shape of ``Result`` (so the runner and tests work).
# """

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from feasibility.models import (
    Client, CreditorRules, Offer,
    offer_total_cents, program_fee_cents,
)


@dataclass
class ScheduleRow:
    date: date
    creditor_payment_cents: int
    program_fee_cents: int
    bank_fee_cents: int
    balance_cents: int


@dataclass
class FundsOption:
    amount_cents: int
    within_guardrail: bool
    reason: str
    date: date | None = None
    num_drafts: int | None = None


@dataclass
class AdditionalFunds:
    lump_sum: FundsOption
    monthly_increment: FundsOption


@dataclass
class Result:
    feasible: bool
    pay_shape_used: str | None = None
    schedule: list[ScheduleRow] | None = None
    additional_funds: AdditionalFunds | None = None

    def to_dict(self) -> dict:
        out: dict = {"feasible": self.feasible, "pay_shape_used": self.pay_shape_used}
        out["schedule"] = (
            [
                {
                    "date": r.date.isoformat(),
                    "creditor_payment_cents": r.creditor_payment_cents,
                    "program_fee_cents": r.program_fee_cents,
                    "bank_fee_cents": r.bank_fee_cents,
                    "balance_cents": r.balance_cents,
                }
                for r in self.schedule
            ]
            if self.schedule is not None
            else None
        )
        if self.additional_funds is None:
            out["additional_funds"] = None
        else:
            def opt(o: FundsOption) -> dict:
                d = {
                    "amount_cents": o.amount_cents,
                    "within_guardrail": o.within_guardrail,
                    "reason": o.reason,
                }
                if o.date is not None:
                    d["date"] = o.date.isoformat()
                if o.num_drafts is not None:
                    d["num_drafts"] = o.num_drafts
                return d

            out["additional_funds"] = {
                "lump_sum": opt(self.additional_funds.lump_sum),
                "monthly_increment": opt(self.additional_funds.monthly_increment),
            }
        return out


from feasibility.utils import get_cadence_dates, get_effective_floors
from feasibility.generators import (
    generate_even_schedule, generate_balloon_schedule, generate_staircase_schedules,
)
from feasibility.simulator import simulate_schedule
from feasibility.solvers import solve_min_lump_sum, solve_min_monthly_increment


def evaluate_offer(client: Client, offer: Offer, rules: CreditorRules) -> Result:
    offer_total = offer_total_cents(offer)
    total_fee = program_fee_cents(offer, rules)

    cadence = get_cadence_dates(client, offer)
    n = len(cadence)
    max_k = min(rules.max_payments, rules.max_terms, n)

    best_sched = None
    best_shape = None
    best_profile = None
    best_k = 0

    for k in range(1, max_k + 1):
        floors = get_effective_floors(k, rules)

        if rules.even_pays:
            p = generate_even_schedule(offer_total, k, floors)
            candidates = [(p, "even")] if p else []
        elif rules.is_ballooning_allowed:
            p = generate_balloon_schedule(offer_total, k, floors)
            candidates = [(p, "balloon")] if p else []
        else:
            candidates = [
                (s, "staircase")
                for s in generate_staircase_schedules(offer_total, k, floors, rules.max_segments)
            ]

        for payments, shape in candidates:
            sched = simulate_schedule(
                client, offer, rules, cadence, payments, total_fee,
                start_creditor_idx=n - k, offer_total=offer_total,
            )
            if sched is None:
                continue

            profile = [
                {row.date: row.program_fee_cents for row in sched}.get(d, 0)
                for d in cadence
            ]
            if best_sched is None or (profile, k) > (best_profile, best_k):
                best_sched, best_shape, best_profile, best_k = sched, shape, profile, k

    if best_sched is not None:
        return Result(feasible=True, pay_shape_used=best_shape, schedule=best_sched)

    lump = solve_min_lump_sum(client, offer, rules, cadence, offer_total, total_fee, max_k)
    inc = solve_min_monthly_increment(client, offer, rules, cadence, offer_total, total_fee, max_k)
    return Result(feasible=False, additional_funds=AdditionalFunds(lump_sum=lump, monthly_increment=inc))