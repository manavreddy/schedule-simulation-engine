from __future__ import annotations
from datetime import date

from feasibility.models import Client, CreditorRules, Offer
from feasibility.engine import ScheduleRow


def simulate_schedule(
    client: Client,
    offer: Offer,
    rules: CreditorRules,
    cadence: list[date],
    creditor_payments: list[int],
    total_program_fee: int,
    start_creditor_idx: int = 0,
    extra_lump: tuple[date | None, int] = (None, 0),
    extra_monthly: int = 0,
    offer_total: int | None = None,
) -> list[ScheduleRow] | None:
    horizon = client.last_draft_date
    bank_fee = rules.bank_fee_cents
    expected_total = offer_total if offer_total is not None else sum(creditor_payments)
    k = len(creditor_payments)

    if start_creditor_idx + k > len(cadence):
        return None

    events: dict[date, dict[str, int]] = {}
    for entry in client.ledger:
        d = entry.date
        if client.as_of_date < d <= horizon:
            events.setdefault(d, {"cr": 0, "dr": 0})
            if entry.type == "credit":
                events[d]["cr"] += entry.amount_cents + extra_monthly
            else:
                events[d]["dr"] += entry.amount_cents

    lump_date, lump_amt = extra_lump
    if lump_date and lump_amt > 0:
        events.setdefault(lump_date, {"cr": 0, "dr": 0})
        events[lump_date]["cr"] += lump_amt

    cadence_set = set(cadence)
    all_dates = sorted(set(events) | cadence_set)

    balance = client.current_balance_cents
    remaining_fee = total_program_fee
    creditor_paid = 0
    rows: dict[date, ScheduleRow] = {}

    for d in all_dates:
        ev = events.get(d, {})
        balance += ev.get("cr", 0) - ev.get("dr", 0)
        if balance < 0:
            return None

        if d not in cadence_set:
            continue

        idx = cadence.index(d)
        if start_creditor_idx <= idx < start_creditor_idx + k:
            cp = creditor_payments[idx - start_creditor_idx]
            bf = bank_fee if cp > 0 else 0
        else:
            cp = bf = 0

        pf = min(remaining_fee, balance - cp - bf) if idx >= start_creditor_idx else 0
        if balance - cp - bf < 0:
            return None

        balance -= cp + bf + pf
        remaining_fee -= pf
        creditor_paid += cp

        if cp or pf or bf:
            rows[d] = ScheduleRow(
                date=d,
                creditor_payment_cents=cp,
                program_fee_cents=pf,
                bank_fee_cents=bf,
                balance_cents=balance,
            )

    if remaining_fee > 0 or creditor_paid != expected_total:
        return None

    return [rows[d] for d in cadence if d in rows]