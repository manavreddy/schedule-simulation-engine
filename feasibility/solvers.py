from __future__ import annotations
from datetime import date

from feasibility.models import Client, CreditorRules, Offer,  round_off
from feasibility.engine import FundsOption
from feasibility.utils import get_effective_floors
from feasibility.generators import generate_even_schedule, generate_balloon_schedule, generate_staircase_schedules
from feasibility.simulator import simulate_schedule


def _get_candidates(offer_total, k, rules):
    floors = get_effective_floors(k, rules)
    if rules.even_pays:
        p = generate_even_schedule(offer_total, k, floors)
        return [p] if p else []
    elif rules.is_ballooning_allowed:
        p = generate_balloon_schedule(offer_total, k, floors)
        return [p] if p else []
    else:
        return generate_staircase_schedules(offer_total, k, floors, rules.max_segments)


def is_any_feasible(
    client: Client, offer: Offer, rules: CreditorRules,
    cadence: list[date], offer_total: int, total_program_fee: int, max_k: int,
    extra_lump: tuple[date | None, int] = (None, 0), extra_monthly: int = 0,
) -> bool:
    for k in range(1, max_k + 1):
        for payments in _get_candidates(offer_total, k, rules):
            result = simulate_schedule(
                client, offer, rules, cadence, payments, total_program_fee,
                start_creditor_idx=0,
                extra_lump=extra_lump, extra_monthly=extra_monthly,
                offer_total=offer_total,
            )
            if result is not None:
                return True
    return False


def solve_min_lump_sum(
    client: Client, offer: Offer, rules: CreditorRules,
    cadence: list[date], offer_total: int, total_program_fee: int, max_k: int,
) -> FundsOption:
    target_date = client.first_draft_date
    if target_date <= client.as_of_date:
        target_date = cadence[0]

    lo, hi = 0, offer_total + total_program_fee + 100000
    best = hi
    while lo <= hi:
        mid = (lo + hi) // 2
        if is_any_feasible(client, offer, rules, cadence, offer_total,
                           total_program_fee, max_k, extra_lump=(target_date, mid)):
            best = mid
            hi = mid - 1
        else:
            lo = mid + 1

    limit = round_off(0.65 * offer_total)
    ok = best <= limit
    return FundsOption(
        amount_cents=best, date=target_date, within_guardrail=ok,
        reason="" if ok else f"Lump sum {best} exceeds {limit} (65% of offer).",
    )


def solve_min_monthly_increment(
    client: Client, offer: Offer, rules: CreditorRules,
    cadence: list[date], offer_total: int, total_program_fee: int, max_k: int,
) -> FundsOption:
    num_drafts = sum(
        1 for e in client.ledger
        if e.type == "credit" and client.as_of_date < e.date <= client.last_draft_date
    )

    lo, hi = 0, offer_total + total_program_fee + 100000
    best = hi
    while lo <= hi:
        mid = (lo + hi) // 2
        if is_any_feasible(client, offer, rules, cadence, offer_total,
                           total_program_fee, max_k, extra_monthly=mid):
            best = mid
            hi = mid - 1
        else:
            lo = mid + 1

    limit = max(10000, round_off(0.40 * client.draft_amount_cents))
    ok = best <= limit
    return FundsOption(
        amount_cents=best, num_drafts=num_drafts, within_guardrail=ok,
        reason="" if ok else f"Monthly increment {best} exceeds {limit}.",
    )
