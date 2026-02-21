#!/usr/bin/env python3
"""Run a game of Risk between AI agents."""

from risk_ai_game import run_game, RandomAgent, AggressiveAgent

if __name__ == "__main__":
    agents = [
        AggressiveAgent(0, name="Aggressive-P0"),
        RandomAgent(1, aggression=0.3, name="Random-P1"),
    ]
    run_game(agents, max_turns=1000, verbose=True)
