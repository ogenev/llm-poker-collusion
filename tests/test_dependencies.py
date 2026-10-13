from importlib import import_module
from importlib.metadata import version

from poker_collusion.poker import PokerHand


def test_inspect_and_openspiel_load_together() -> None:
    inspect = import_module("inspect_ai")
    assert callable(inspect.Task)
    assert version("inspect-ai")
    assert version("open-spiel")
    assert PokerHand((0, 1, 2)).current_player == 0
