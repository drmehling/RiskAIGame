import copy
from abc import ABC, abstractmethod
from typing import Any, Optional

from .game_state import GameState

# Implement a telemetry object to collect game statistics.
# The telemetry object will be called at various points in the game loop,
# providing the telemetry object the game state and actions.
# Extracting statistics from the game state and actions can then be done however one wishes.
class GameTelemetry(ABC):
    @abstractmethod
    def on_game_start(self, game_state: GameState) -> None:
        pass

    @abstractmethod
    def on_before_action(self, game_state: GameState) -> None:
        pass

    @abstractmethod
    def on_action(
        self,
        game_state: GameState,
        action: Any,
        result: dict,
    ) -> None:
        pass

    @abstractmethod
    def on_game_end(
        self,
        game_state: GameState,
        winner: Optional[int],
    ) -> None:
        pass

# A simple telemetry object example.
# Count the number of turns in a game.
class TurnCountCollector(GameTelemetry):
    def __init__(self) -> None:
        self.turns: int = 0

    def on_game_start(self, game_state: GameState) -> None:
        pass

    def on_before_action(self, game_state: GameState) -> None:
        pass

    def on_action(
        self,
        game_state: GameState,
        action: Any,
        result: dict,
    ) -> None:
        pass

    def on_game_end(self, game_state: GameState, winner: Optional[int]) -> None:
        self.turns = game_state.turn_number

# A simple telemetry object that counts how many territories each player has at the end of each turn.
class TerritoryCountCollector(GameTelemetry):
    def __init__(self) -> None:
        self.snapshots: list[dict] = []

    def on_game_start(self, game_state: GameState) -> None:
        pass

    def on_before_action(self, game_state: GameState) -> None:
        pass

    def on_action(
        self,
        game_state: GameState,
        action: Any,
        result: dict,
    ) -> None:
        counts = {
            p: len(game_state.get_player_territories(p))
            for p in range(game_state.num_players)
        }
        self.snapshots.append({
            "turn": game_state.turn_number,
            "phase": game_state.phase.name,
            **counts,
        })

    def on_game_end(self, game_state: GameState, winner: Optional[int]) -> None:
        pass

# A telemetry object that captures the initial and final game states.
# This could easily be expanded to capture all states.
class GameInitialFinalStates(GameTelemetry):
    def __init__(self) -> None:
        self.initial_state: GameState | None = None
        self.final_state: GameState | None = None

    def on_game_start(self, game_state: GameState) -> None:
        self.initial_state = copy.deepcopy(game_state)

    def on_before_action(self, game_state: GameState) -> None:
        pass

    def on_action(
        self,
        game_state: GameState,
        action: Any,
        result: dict,
    ) -> None:
        pass

    def on_game_end(self, game_state: GameState, winner: Optional[int]) -> None:
        self.final_state = game_state
