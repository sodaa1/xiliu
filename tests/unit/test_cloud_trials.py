from concurrent.futures import ThreadPoolExecutor

import pytest

from xiliu.api.errors import WebError
from xiliu.cloud.identity import IdentityStore
from xiliu.cloud.trials import TrialLedger


def setup_ledger(tmp_path, *, daily=100, clock=lambda: 1_800_000_000):
    identity = IdentityStore(tmp_path)
    user = identity.register("alice", "long-enough-password")
    return identity, user["id"], TrialLedger(identity, daily_limit=daily, clock=clock)


def consume(ledger, user, request):
    ledger.reserve(user, request, "payload", source="trial")
    ledger.started(user, request)
    ledger.settle(user, request, {"type": "final", "text": "done"})


def test_five_trials_persist_and_duplicate_never_reserves_again(tmp_path):
    identity, user, ledger = setup_ledger(tmp_path)
    for number in range(5):
        consume(ledger, user, f"request-{number:04}")
    assert ledger.balance(user)["remaining"] == 0
    with pytest.raises(WebError, match="试用"):
        ledger.reserve(user, "request-0006", "payload", source="trial")
    duplicate = ledger.reserve(user, "request-0000", "payload", source="trial")
    assert duplicate["fresh"] is False and duplicate["receipt"]["text"] == "done"
    assert TrialLedger(identity).balance(user)["remaining"] == 0
    with pytest.raises(WebError):
        ledger.reserve(user, "request-0000", "changed", source="trial")


def test_only_one_concurrent_fifth_trial_and_own_is_independent(tmp_path):
    _, user, ledger = setup_ledger(tmp_path)
    for number in range(4):
        consume(ledger, user, f"request-{number:04}")

    def reserve(number):
        try:
            return ledger.reserve(user, f"parallel-{number:04}", "payload", source="trial")
        except WebError:
            return None

    with ThreadPoolExecutor(max_workers=8) as pool:
        assert sum(result is not None for result in pool.map(reserve, range(8))) == 1
    ledger.reserve(user, "own-request-1", "payload", source="own")
    ledger.settle(user, "own-request-1", {"type": "final"})
    assert ledger.balance(user)["remaining"] == 0


def test_refund_unstarted_and_conservatively_recover_dispatched_orphans(tmp_path):
    now = [1_800_000_000]
    identity, user, ledger = setup_ledger(tmp_path, clock=lambda: now[0])
    ledger.reserve(user, "request-fail", "payload", source="trial")
    ledger.dispatched(user, "request-fail")
    ledger.settle(user, "request-fail", {"type": "error"})
    assert ledger.balance(user)["remaining"] == 5
    ledger.reserve(user, "request-safe", "payload", source="trial")
    now[0] += 121
    recovered = TrialLedger(identity, clock=lambda: now[0])
    assert recovered.balance(user)["remaining"] == 5
    recovered.reserve(user, "request-crash", "payload", source="trial")
    recovered.dispatched(user, "request-crash")
    now[0] += 121
    assert TrialLedger(identity, clock=lambda: now[0]).balance(user)["remaining"] == 4


def test_daily_capacity_is_atomic_across_accounts(tmp_path):
    identity, alice, ledger = setup_ledger(tmp_path, daily=1)
    bob = identity.register("bobby", "long-enough-password")["id"]
    consume(ledger, alice, "request-alice")
    with pytest.raises(WebError):
        ledger.reserve(bob, "request-bobby", "payload", source="trial")
