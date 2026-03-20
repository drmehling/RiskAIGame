"""Greedy heuristic agent for Risk."""

import random
from .agent import Agent
from .action import Phase, DeployAction, AttackAction, FortifyAction, EndPhaseAction
from .game_state import CONTINENT_BONUSES


class GreedyAgent(Agent):
    """Picks locally optimal moves using board heuristics."""

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
        my_territories = game_state.get_player_territories(self.player_id)
        all_territories = game_state.board.all_territories()

        scores = {}
        for t in my_territories:
            score = 0.0

            # border pressure
            enemy_pressure = 0
            for n_name in t.neighbors:
                nb = game_state.board.get(n_name)
                if nb and nb.owner != self.player_id:
                    enemy_pressure += nb.armies
            if enemy_pressure > 0:
                score += enemy_pressure / max(1, t.armies) * 3.0

            # continent completion
            continent_score = self._continent_priority(
                t.continent, game_state, all_territories
            )
            score += continent_score

            # interior territories aren't worth deploying to
            has_enemy_neighbor = any(
                game_state.board.get(n) and game_state.board.get(n).owner != self.player_id
                for n in t.neighbors
            )
            if not has_enemy_neighbor:
                score *= 0.1

            scores[t.name] = score

        best = max(scores, key=scores.get)
        return DeployAction(best, game_state.armies_to_deploy)

    def _choose_attack(self, game_state):
        candidates = []

        for t in game_state.get_player_territories(self.player_id):
            if t.armies < 2:
                continue
            for n_name in t.neighbors:
                nb = game_state.board.get(n_name)
                if nb and nb.owner != self.player_id:
                    score = self._attack_score(t, nb, game_state)
                    candidates.append((score, t, nb))

        if not candidates:
            return EndPhaseAction()

        candidates.sort(key=lambda x: x[0], reverse=True)
        best_score, attacker, defender = candidates[0]

        # only attack if favorable
        if best_score <= 0:
            return EndPhaseAction()

        num_dice = min(3, attacker.armies - 1)
        return AttackAction(attacker.name, defender.name, num_dice)

    def _attack_score(self, attacker, defender, game_state):
        ratio = attacker.armies / max(1, defender.armies)
        score = (ratio - 1.0) * 5.0

        # bonus if this would complete a continent
        all_territories = game_state.board.all_territories()
        continent = defender.continent
        continent_territories = [t for t in all_territories if t.continent == continent]
        owned = sum(1 for t in continent_territories if t.owner == self.player_id)
        total = len(continent_territories)

        if owned == total - 1:
            bonus = CONTINENT_BONUSES.get(continent, 0)
            score += bonus * 3.0
        elif owned >= total - 2:
            bonus = CONTINENT_BONUSES.get(continent, 0)
            score += bonus * 1.5

        # don't attack with only 2 armies
        if attacker.armies <= 2:
            score -= 3.0

        return score

    def _choose_fortify(self, game_state):
        my_territories = game_state.get_player_territories(self.player_id)

        best_move = None
        best_value = 0.0

        for src in my_territories:
            if src.armies < 2:
                continue

            src_has_enemies = any(
                game_state.board.get(n) and game_state.board.get(n).owner != self.player_id
                for n in src.neighbors
            )

            for dst in my_territories:
                if dst.name == src.name:
                    continue

                dst_has_enemies = any(
                    game_state.board.get(n) and game_state.board.get(n).owner != self.player_id
                    for n in dst.neighbors
                )

                # move from interior to border
                if not src_has_enemies and dst_has_enemies:
                    if game_state._are_connected(src.name, dst.name):
                        enemy_pressure = sum(
                            game_state.board.get(n).armies
                            for n in dst.neighbors
                            if game_state.board.get(n) and game_state.board.get(n).owner != self.player_id
                        )
                        value = enemy_pressure / max(1, dst.armies)
                        if value > best_value:
                            best_value = value
                            best_move = (src, dst)

        if best_move:
            src, dst = best_move
            return FortifyAction(src.name, dst.name, src.armies - 1)

        return EndPhaseAction()

    def _continent_priority(self, continent, game_state, all_territories):
        continent_territories = [t for t in all_territories if t.continent == continent]
        total = len(continent_territories)
        owned = sum(1 for t in continent_territories if t.owner == self.player_id)
        bonus = CONTINENT_BONUSES.get(continent, 0)

        if owned == total:
            return bonus * 1.0
        elif owned == total - 1:
            return bonus * 4.0
        elif owned >= total // 2:
            return bonus * (owned / total) * 2.0
        else:
            return 0.0
