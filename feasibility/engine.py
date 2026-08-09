# """Candidate implementation goes here.

# Implement ``evaluate_offer`` so that it satisfies the rules in ASSIGNMENT.md and
# the example expectations in tests/test_cases.py. The dataclasses below define the
# required OUTPUT shape (see ASSIGNMENT.md "Output"). You may add helpers, modules,
# or rewrite internals freely, but keep ``evaluate_offer``'s signature and the
# serialized shape of ``Result`` (so the runner and tests work).
# """

# from __future__ import annotations

# from dataclasses import asdict, dataclass
# from datetime import date

# from feasibility.models import (Client, CreditorRules, Offer, is_end_of_month,
#                                  end_of_month,monthly_payment_dates, default_first_payment_date,
#                                  add_months)

# import math


# @dataclass
# class ScheduleRow:
#     date: date
#     creditor_payment_cents: int
#     program_fee_cents: int
#     bank_fee_cents: int
#     balance_cents: int


# @dataclass
# class FundsOption:
#     amount_cents: int
#     within_guardrail: bool
#     reason: str
#     # lump-sum only:
#     date: date | None = None
#     # monthly-increment only:
#     num_drafts: int | None = None


# @dataclass
# class AdditionalFunds:
#     lump_sum: FundsOption
#     monthly_increment: FundsOption

# @dataclass
# class Result:
#     feasible: bool
#     # One of "even", "staircase", or "balloon" — the shape your solution produced
#     # (driven by the creditor flags). None when infeasible.
#     pay_shape_used: str | None = None
#     schedule: list[ScheduleRow] | None = None
#     additional_funds: AdditionalFunds | None = None

#     def to_dict(self) -> dict:
#         out: dict = {"feasible": self.feasible, "pay_shape_used": self.pay_shape_used}
#         out["schedule"] = (
#             [
#                 {
#                     "date": r.date.isoformat(),
#                     "creditor_payment_cents": r.creditor_payment_cents,
#                     "program_fee_cents": r.program_fee_cents,
#                     "bank_fee_cents": r.bank_fee_cents,
#                     "balance_cents": r.balance_cents,
#                 }
#                 for r in self.schedule
#             ]
#             if self.schedule is not None
#             else None
#         )
#         if self.additional_funds is None:
#             out["additional_funds"] = None
#         else:
#             def opt(o: FundsOption) -> dict:
#                 d = {
#                     "amount_cents": o.amount_cents,
#                     "within_guardrail": o.within_guardrail,
#                     "reason": o.reason,
#                 }
#                 if o.date is not None:
#                     d["date"] = o.date.isoformat()
#                 if o.num_drafts is not None:
#                     d["num_drafts"] = o.num_drafts
#                 return d

#             out["additional_funds"] = {
#                 "lump_sum": opt(self.additional_funds.lump_sum),
#                 "monthly_increment": opt(self.additional_funds.monthly_increment),
#             }
#         return out

# def evaluate_offer(client: Client, offer: Offer, rules: CreditorRules) -> Result:
#     """Evaluate a single offer. See ASSIGNMENT.md for the full specification.

#     Return a Result with feasible=True and a schedule when the offer fits, or
#     feasible=False with additional_funds (minimum lump sum AND minimum monthly
#     increment) when it does not.
#     """
#     result = Result(feasible=False)
#     program_fee = round_off(rules.program_fee_pct*offer.original_balance_cents)
#     creditor_fee = round_off(offer.settlement_pct*offer.original_balance_cents)
#     bank_fee = rules.bank_fee_cents
#     to_be_paid = offer.current_balance_cents
#     schedule : list[ScheduleRow] = []
#     current = 0
#     transactions = client.ledger
#     credits =sorted((row for row in transactions if row.type == "credit"),
#                      key=lambda row: (row.date.year, row.date.month, row.date.day))
#     debits = sorted((row for row in transactions if row.type == "debit"),
#                      key=lambda row: (row.date.year, row.date.month, row.date.day))
#     first_payment_date = offer.first_payment_date or default_first_payment_date(client)
#     max_payments = min(rules.max_terms, rules.max_payments)    # cadence_dates = monthly_payment_dates(first_payment_date, count)
#     month = 0
#     last_payment = 0
#     max_token_pays = 0
#     while(to_be_paid > 0):
#         current += sum(row.amount_cents for row in credits if row.date == add_months(first_payment_date, month))
#         current -= sum(row.amount_cents for row in debits if row.date == add_months(first_payment_date, month))

#         if current < rules.min_payment_cents+bank_fee:
#             break

#         elif current == rules.min_payment_cents+bank_fee and max_token_pays < rules.max_token_pays:
#             current -= program_fee+ bank_fee
#             s = ScheduleRow(date=add_months(first_payment_date, month),  bank_fee_cents=bank_fee,
#                             program_fee_cents=program_fee, creditor_payment_cents=current-program_fee-bank_fee,
#                             balance_cents=0)
#             program_fee = 0
#             schedule.append(s)

#         elif current == rules.min_payment_cents+bank_fee and max_token_pays == rules.max_token_pays:
#             break

#         elif current > rules.min_payment_cents+bank_fee:
#             if max_token_pays < rules.max_token_pays:

#                 s = ScheduleRow(date=add_months(first_payment_date, month),  bank_fee_cents=bank_fee,
#                                 program_fee_cents=0, creditor_payment_cents=current-bank_fee,
#                                 balance_cents=0)
            


#     return result
#     raise NotImplementedError("Implement evaluate_offer — see ASSIGNMENT.md")



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


from feasibility.utils import get_cadence_dates, get_effective_floors, round_off
from feasibility.generators import (
    generate_even_schedule, generate_balloon_schedule, generate_staircase_schedules,
)
from feasibility.simulator import simulate_schedule
from feasibility.solvers import solve_min_lump_sum, solve_min_monthly_increment


def evaluate_offer(client: Client, offer: Offer, rules: CreditorRules) -> Result:
    offer_total = round_off(offer_total_cents(offer))
    total_fee = round_off(program_fee_cents(offer, rules))

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