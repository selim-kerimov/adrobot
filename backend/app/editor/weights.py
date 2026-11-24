"""Offer shares in a stream.

Keitaro takes whole percents and does not check that they add up to 100, so we do.
Pinned shares stay as they are. What is left of 100 is split evenly between the other
active offers; the leftover percents go one each to the first offers. Removed offers
get 0.
"""

from dataclasses import dataclass


class WeightError(ValueError):
    pass


@dataclass(frozen=True)
class Slot:
    share: int
    pinned: bool = False
    active: bool = True


def rebalance(slots: list[Slot]) -> list[int]:
    """Returns the new share for every slot, in the same order."""
    pinned = [slot.share for slot in slots if slot.active and slot.pinned]
    free_count = sum(1 for slot in slots if slot.active and not slot.pinned)
    left = 100 - sum(pinned)

    if left < 0:
        raise WeightError(f"pinned shares add up to {sum(pinned)}%, more than 100%")
    if free_count == 0 and pinned and left > 0:
        raise WeightError(f"pinned shares add up to {sum(pinned)}%, unpin one to fill 100%")

    base, extra = divmod(left, free_count) if free_count else (0, 0)
    shares = []
    for slot in slots:
        if not slot.active:
            shares.append(0)
        elif slot.pinned:
            shares.append(slot.share)
        else:
            shares.append(base + (1 if extra > 0 else 0))
            extra -= 1
    return shares
