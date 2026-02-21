"""Agent classes for the Risk game."""

from abc import ABC, abstractmethod
import random
from .action import Phase, DeployAction, AttackAction, FortifyAction, EndPhaseAction


class Agent(ABC):
    def __init__(self, player_id, name=None):
        self.player_id = player_id
        self.name = name or f"{self.__class__.__name__}(P{player_id})"

    @abstractmethod
    def choose_action(self, game_state):
        pass

    def __repr__(self):
        return self.name


class RandomAgent(Agent):
    """Makes random decisions. Baseline agent for testing."""

    def __init__(self, player_id, aggression=0.5, name=None):
        super().__init__(player_id, name)
        self.aggression = aggression

    def choose_action(self, game_state):
        if game_state.phase == Phase.DEPLOY:
            return self._choose_deploy(game_state)
        elif game_state.phase == Phase.ATTACK:
            return self._choose_attack(game_state)
        elif game_state.phase == Phase.FORTIFY:
            return self._choose_fortify(game_state)

    def _choose_deploy(self, game_state):
        territories = game_state.get_player_territories(self.player_id)
        target = random.choice(territories)
        return DeployAction(target.name, game_state.armies_to_deploy)

    def _choose_attack(self, game_state):
        attackable = []
        for t in game_state.get_player_territories(self.player_id):
            if t.armies < 2:
                continue
            for neighbor_name in t.neighbors:
                neighbor = game_state.board.get(neighbor_name)
                if neighbor and neighbor.owner != self.player_id:
                    attackable.append((t, neighbor))

        if not attackable or random.random() > self.aggression:
            return EndPhaseAction()

        attacker, defender = random.choice(attackable)
        num_dice = min(3, attacker.armies - 1)
        return AttackAction(attacker.name, defender.name, num_dice)

    def _choose_fortify(self, game_state):
        return EndPhaseAction()


class AggressiveAgent(Agent):
    """Always attacks when possible, focuses forces on the front."""

    def __init__(self, player_id, name=None):
        super().__init__(player_id, name)

    def choose_action(self, game_state):
        if game_state.phase == Phase.DEPLOY:
            return self._choose_deploy(game_state)
        elif game_state.phase == Phase.ATTACK:
            return self._choose_attack(game_state)
        elif game_state.phase == Phase.FORTIFY:
            return self._choose_fortify(game_state)

    def _choose_deploy(self, game_state):
        # put all armies on territory with most enemy neighbors
        territories = game_state.get_player_territories(self.player_id)
        best = max(territories, key=lambda t: sum(
            1 for n in t.neighbors
            if game_state.board.get(n) and game_state.board.get(n).owner != self.player_id
        ))
        return DeployAction(best.name, game_state.armies_to_deploy)

    def _choose_attack(self, game_state):
        # pick the attack with best army ratio
        best_attack = None
        best_ratio = 0

        for t in game_state.get_player_territories(self.player_id):
            if t.armies < 2:
                continue
            for neighbor_name in t.neighbors:
                neighbor = game_state.board.get(neighbor_name)
                if neighbor and neighbor.owner != self.player_id:
                    ratio = t.armies / max(1, neighbor.armies)
                    if ratio > best_ratio:
                        best_ratio = ratio
                        best_attack = (t, neighbor)

        # only attack if we have decent odds
        if best_attack is None or best_ratio < 1.5:
            return EndPhaseAction()

        attacker, defender = best_attack
        num_dice = min(3, attacker.armies - 1)
        return AttackAction(attacker.name, defender.name, num_dice)

    def _choose_fortify(self, game_state):
        # move armies from interior to front line
        territories = game_state.get_player_territories(self.player_id)

        for t in territories:
            if t.armies < 2:
                continue
            enemy_neighbors = [
                n for n in t.neighbors
                if game_state.board.get(n) and game_state.board.get(n).owner != self.player_id
            ]
            if enemy_neighbors:
                continue  # already on front line

            # interior territory, try to move armies forward
            for neighbor_name in t.neighbors:
                neighbor = game_state.board.get(neighbor_name)
                if neighbor and neighbor.owner == self.player_id:
                    has_enemies = any(
                        game_state.board.get(nn) and game_state.board.get(nn).owner != self.player_id
                        for nn in neighbor.neighbors
                    )
                    if has_enemies:
                        return FortifyAction(t.name, neighbor_name, t.armies - 1)

        return EndPhaseAction()
