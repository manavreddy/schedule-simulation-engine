from datetime import date
import math

from feasibility.models import (
    Client,
    Offer,
    CreditorRules,
    is_end_of_month,
    end_of_month,
    default_first_payment_date,
    add_months,
)


def round_off(amount: float) -> int:
    return math.floor(amount + 0.5)


def get_cadence_dates(client: Client, offer: Offer) -> list[date]:
    start = offer.first_payment_date or default_first_payment_date(client)
    horizon = client.last_draft_date
    is_eom = is_end_of_month(start)
    cadence = []
    i = 0
    while True:
        d = end_of_month(add_months(start, i)) if is_eom else add_months(start, i)
        if d > horizon:
            break
        cadence.append(d)
        i += 1

    if horizon not in cadence:
        if (is_eom and is_end_of_month(horizon)) or (not is_eom and horizon.day == start.day):
            cadence.append(horizon)

    return cadence


def get_effective_floors(k: int, rules: CreditorRules) -> list[int]:
    floors = []
    running_max = 0
    for i in range(1, k + 1):
        f = rules.min_payment_cents + 1 if i > rules.max_token_pays else rules.min_payment_cents
        for tier_from, tier_min in rules.min_payment_tiers:
            if i >= tier_from:
                f = max(f, tier_min)
        running_max = max(running_max, f)
        floors.append(running_max)
    return floors
