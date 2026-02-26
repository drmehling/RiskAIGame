#!/usr/bin/env python3
"""Run a game of Risk between AI agents."""

from risk_ai_game import run_game, RandomAgent, AggressiveAgent
from risk_ai_game.options import RiskAIGameOptions

if __name__ == "__main__":
    opts = RiskAIGameOptions(
        agents=[
            AggressiveAgent(0, name="Aggressive-P0"),
            RandomAgent(1, aggression=0.3, name="Random-P1"),
        ],
        max_turns=1000,
        verbose=True,
    )
    run_game(opts)
