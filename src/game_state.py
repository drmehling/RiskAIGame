from board import Board
import random

class GameState:
    def __init__(self, num_players=2):
        self.board = Board()
        self.num_players = num_players
        self.current_player = 0

    def setup_random(self):
        territories = self.board.all_territories()
        random.shuffle(territories)
        for i, t in enumerate(territories):
            t.owner = i % self.num_players
            t.armies = 1

    def get_player_territories(self, player_id):
        return [t for t in self.board.all_territories() if t.owner == player_id]

    def next_turn(self):
        self.current_player = (self.current_player + 1) % self.num_players
