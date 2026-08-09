def generate_even_schedule(offer_total: int, k: int, floors: list[int]) -> list[int] | None:
    q, r = divmod(offer_total, k)
    payments = [q] * (k - r) + [q + 1] * r if k > 1 else [offer_total]
    if any(p < f for p, f in zip(payments, floors)):
        return None
    return payments

def generate_balloon_schedule(offer_total: int, k: int, floors: list[int]) -> list[int] | None:
    if k == 1:
        return [offer_total] if offer_total >= floors[0] else None
    payments = list(floors[:k - 1])
    remainder = offer_total - sum(payments)
    if remainder < payments[-1] or remainder < floors[k - 1]:
        return None
    payments.append(remainder)
    return payments

def generate_staircase_schedules(
    offer_total: int, k: int, floors: list[int], max_segments: int
) -> list[list[int]]:
    if k == 1:
        return [[offer_total]] if offer_total >= floors[0] else []

    seen = set()
    results = []

    def _add(candidate):
        key = tuple(candidate)
        if key not in seen and len(set(candidate)) <= max_segments:
            seen.add(key)
            results.append(candidate)

    for tail_len in range(1, k):
        head_len = k - tail_len
        head = list(floors[:head_len])

        if len(set(head)) + 1 > max_segments:
            head = [max(floors[:head_len])] * head_len

        remainder = offer_total - sum(head)
        if remainder <= 0:
            continue

        q, r = divmod(remainder, tail_len)
        if q < head[-1] or q < max(floors[head_len:]):
            continue

        tail = [q] * (tail_len - r) + [q + 1] * r
        _add(head + tail)

    q, r = divmod(offer_total, k)
    even = [q]*(k - r) + [q + 1]*r
    if all(p >= f for p, f in zip(even, floors)):
        _add(even)

    return results
