import pytest

from app.editor.weights import Slot, WeightError, rebalance


def test_splits_evenly():
    assert rebalance([Slot(0), Slot(0), Slot(0), Slot(0)]) == [25, 25, 25, 25]


def test_leftover_goes_to_first_offers():
    assert rebalance([Slot(0), Slot(0), Slot(0)]) == [34, 33, 33]


def test_pinned_share_is_kept():
    shares = rebalance([Slot(25, pinned=True), Slot(0), Slot(0)])
    assert shares == [25, 38, 37]


def test_removed_offer_gets_zero():
    shares = rebalance([Slot(50), Slot(50, active=False), Slot(0)])
    assert shares == [50, 0, 50]


def test_removed_pinned_offer_frees_its_share():
    shares = rebalance([Slot(30, pinned=True, active=False), Slot(0), Slot(0)])
    assert shares == [0, 50, 50]


def test_only_pinned_offers_adding_up_to_100():
    assert rebalance([Slot(60, pinned=True), Slot(40, pinned=True)]) == [60, 40]


def test_pinned_over_100_is_rejected():
    with pytest.raises(WeightError, match="more than 100"):
        rebalance([Slot(70, pinned=True), Slot(40, pinned=True), Slot(0)])


def test_only_pinned_offers_below_100_is_rejected():
    with pytest.raises(WeightError, match="unpin"):
        rebalance([Slot(25, pinned=True), Slot(0, active=False)])


def test_pinned_100_leaves_zero_for_the_rest():
    assert rebalance([Slot(100, pinned=True), Slot(0)]) == [100, 0]


def test_no_active_offers():
    assert rebalance([Slot(50, active=False), Slot(50, active=False)]) == [0, 0]
    assert rebalance([]) == []
