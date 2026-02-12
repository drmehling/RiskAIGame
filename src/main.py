#!/usr/bin/env python3

from game_state import GameState

def main():
    game = GameState(num_players=2)
    game.setup_random()

    print("Risk Game initialized")
    print(f"Total territories: {len(game.board.all_territories())}")

    for p in range(game.num_players):
        territories = game.get_player_territories(p)
        print(f"Player {p}: {len(territories)} territories")

if __name__ == "__main__":
    main()
