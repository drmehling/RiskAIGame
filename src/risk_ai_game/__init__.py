"""Risk AI Game - single import for all game code."""

from risk_ai_game.action import (
    Phase,
    DeployAction,
    AttackAction,
    FortifyAction,
    EndPhaseAction,
)
from risk_ai_game.agent import Agent, RandomAgent, AggressiveAgent
from risk_ai_game.board import Board
from risk_ai_game.game_state import GameState, CONTINENT_BONUSES
from risk_ai_game.render import (
    render_state,
    render_state_from_game_state,
    game_state_to_render_dict,
)
from risk_ai_game.territory import Territory

__all__ = [
    "Phase",
    "DeployAction",
    "AttackAction",
    "FortifyAction",
    "EndPhaseAction",
    "Agent",
    "RandomAgent",
    "AggressiveAgent",
    "Board",
    "GameState",
    "CONTINENT_BONUSES",
    "render_state",
    "render_state_from_game_state",
    "game_state_to_render_dict",
    "Territory",
]
