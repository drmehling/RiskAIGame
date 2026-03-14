from collections.abc import Callable
from typing import Optional

from .agent import Agent
from .game_state import GameState
from .telemetry import GameTelemetry


class RiskAIGameOptions:
    def __init__(
        self,
        # The agents that will play the game.
        agents: list[Agent],
        # maximum number of turns to play before declaring a tie.
        max_turns: int = 500,
        # Verbose output.
        verbose: bool = True,
        # TODO: random_seed needs to be supported for reproducibility.
        random_seed: Optional[int] = None,
        # You can provide a function to initialize the board state.
        initial_board_setup: Optional[Callable[[GameState], None]] = None,
        # You can provide a telemetry object to collect game statistics.
        game_telemetry: Optional[GameTelemetry] = None,
    ):
        if not agents:
            raise ValueError("agents must be a non-empty list")
        self.agents = agents
        self.max_turns = max_turns
        self.verbose = verbose
        self.random_seed = random_seed
        self.initial_board_setup = initial_board_setup
        self.game_telemetry = game_telemetry
