"""Actions for the Risk game - deploy, attack, fortify phases."""

from dataclasses import dataclass
from enum import Enum, auto


class Phase(Enum):
    DEPLOY = auto()
    ATTACK = auto()
    FORTIFY = auto()


@dataclass
class DeployAction:
    territory: str
    armies: int


@dataclass
class AttackAction:
    from_territory: str
    to_territory: str
    num_dice: int


@dataclass
class FortifyAction:
    from_territory: str
    to_territory: str
    armies: int


@dataclass
class EndPhaseAction:
    pass
