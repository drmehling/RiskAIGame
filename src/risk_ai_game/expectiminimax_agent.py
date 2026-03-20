"""Expectiminimax Agent for Risk.

Implements adversarial search with chance nodes to handle the stochastic
element of dice rolls. The search tree alternates between:
  - MAX nodes: current player picks the action maximizing expected value
  - MIN nodes: opponent picks the action minimizing our expected value
  - CHANCE nodes: dice outcomes weighted by probability

Due to the massive branching factor of Risk, the agent uses:
  - Depth-limited search
  - Move ordering and pruning (only top-k moves evaluated)
  - A heuristic evaluation function for leaf nodes
"""

import copy
import random
from .agent import Agent
from .action import Phase, DeployAction, AttackAction, FortifyAction, EndPhaseAction
from .game_state import GameState, CONTINENT_BONUSES


# Precomputed dice outcome probabilities for attacker vs defender.
# Key: (attacker_dice, defender_dice) -> list of (attacker_losses, defender_losses, probability)
DICE_OUTCOMES = {}


def _compute_dice_outcomes():
    """Precompute dice battle probabilities via enumeration."""
    from itertools import product

    for n_atk in range(1, 4):  # 1-3 attacker dice
        for n_def in range(1, 3):  # 1-2 defender dice
            outcomes = {}
            atk_faces = list(product(range(1, 7), repeat=n_atk))
            def_faces = list(product(range(1, 7), repeat=n_def))
            total = len(atk_faces) * len(def_faces)

            for atk_roll in atk_faces:
                for def_roll in def_faces:
                    a_sorted = sorted(atk_roll, reverse=True)
                    d_sorted = sorted(def_roll, reverse=True)
                    a_loss = 0
                    d_loss = 0
                    for a, d in zip(a_sorted, d_sorted):
                        if a > d:
                            d_loss += 1
                        else:
                            a_loss += 1
                    key = (a_loss, d_loss)
                    outcomes[key] = outcomes.get(key, 0) + 1

            result = []
            for (a_loss, d_loss), count in outcomes.items():
                result.append((a_loss, d_loss, count / total))
            DICE_OUTCOMES[(n_atk, n_def)] = result


_compute_dice_outcomes()


class ExpectiminimaxAgent(Agent):
    """Adversarial search agent using expectiminimax with depth limit.

    Args:
        player_id: The player index this agent controls.
        max_depth: Maximum search depth (each phase transition = 1 depth).
        top_k_moves: Only evaluate this many top moves per node to limit branching.
        name: Optional display name.
    """

    def __init__(self, player_id, max_depth=2, top_k_moves=5, name=None):
        super().__init__(player_id, name)
        self.max_depth = max_depth
        self.top_k_moves = top_k_moves

    def choose_action(self, game_state):
        if game_state.phase == Phase.DEPLOY:
            return self._choose_deploy(game_state)
        elif game_state.phase == Phase.ATTACK:
            return self._choose_attack(game_state)
        elif game_state.phase == Phase.FORTIFY:
            return self._choose_fortify(game_state)

    # ------------------------------------------------------------------ deploy

    def _choose_deploy(self, game_state):
        """Deploy all armies to the highest-value territory."""
        # For deploy, use heuristic directly (search branching is too wide
        # with all possible deploy splits).
        my_territories = game_state.get_player_territories(self.player_id)
        all_territories = game_state.board.all_territories()

        best_territory = None
        best_score = float("-inf")

        for t in my_territories:
            has_enemy = any(
                game_state.board.get(n) and game_state.board.get(n).owner != self.player_id
                for n in t.neighbors
            )
            if not has_enemy:
                continue

            # Simulate deploying here and evaluate
            sim = self._copy_state(game_state)
            sim_t = sim.board.get(t.name)
            sim_t.armies += game_state.armies_to_deploy
            sim.armies_to_deploy = 0
            sim.phase = Phase.ATTACK

            score = self._evaluate(sim)
            if score > best_score:
                best_score = score
                best_territory = t.name

        if best_territory is None:
            # Fallback: deploy to territory with most enemy neighbors
            best_territory = max(
                my_territories,
                key=lambda t: sum(
                    1 for n in t.neighbors
                    if game_state.board.get(n) and game_state.board.get(n).owner != self.player_id
                ),
            ).name

        return DeployAction(best_territory, game_state.armies_to_deploy)

    # ----------------------------------------------------------------- attack

    def _choose_attack(self, game_state):
        """Use expectiminimax search to choose the best attack or end phase."""
        candidates = self._get_attack_candidates(game_state)

        if not candidates:
            return EndPhaseAction()

        best_action = EndPhaseAction()
        # Evaluate ending the attack phase
        sim_end = self._copy_state(game_state)
        sim_end.phase = Phase.FORTIFY
        best_value = self._evaluate(sim_end)

        for action in candidates:
            value = self._expected_attack_value(game_state, action, depth=0)
            if value > best_value:
                best_value = value
                best_action = action

        return best_action

    def _expected_attack_value(self, game_state, attack_action, depth):
        """Compute expected value of an attack using dice probabilities."""
        attacker = game_state.board.get(attack_action.from_territory)
        defender = game_state.board.get(attack_action.to_territory)

        n_atk = attack_action.num_dice
        n_def = min(2, defender.armies)
        outcomes = DICE_OUTCOMES.get((n_atk, n_def), [])

        expected_value = 0.0
        for a_loss, d_loss, prob in outcomes:
            sim = self._copy_state(game_state)
            sim_attacker = sim.board.get(attack_action.from_territory)
            sim_defender = sim.board.get(attack_action.to_territory)

            sim_attacker.armies -= a_loss
            sim_defender.armies -= d_loss

            if sim_defender.armies <= 0:
                # Conquered
                sim_defender.owner = self.player_id
                moved = attack_action.num_dice
                sim_attacker.armies -= moved
                sim_defender.armies = moved

            if depth < self.max_depth:
                value = self._minimax(sim, depth + 1, is_max=True)
            else:
                value = self._evaluate(sim)

            expected_value += prob * value

        return expected_value

    def _minimax(self, game_state, depth, is_max):
        """Depth-limited minimax evaluation."""
        winner = game_state.get_winner()
        if winner is not None:
            return 1000.0 if winner == self.player_id else -1000.0

        if depth >= self.max_depth:
            return self._evaluate(game_state)

        if game_state.phase == Phase.ATTACK and game_state.current_player == self.player_id:
            # MAX node
            candidates = self._get_attack_candidates(game_state)
            if not candidates:
                return self._evaluate(game_state)

            best = self._evaluate(game_state)  # value of ending attack
            for action in candidates[:self.top_k_moves]:
                val = self._expected_attack_value(game_state, action, depth)
                best = max(best, val)
            return best
        else:
            # For other phases/players, just evaluate
            return self._evaluate(game_state)

    def _get_attack_candidates(self, game_state):
        """Get top-k attack actions sorted by heuristic army ratio."""
        candidates = []
        for t in game_state.get_player_territories(self.player_id):
            if t.armies < 2:
                continue
            for n_name in t.neighbors:
                nb = game_state.board.get(n_name)
                if nb and nb.owner != self.player_id:
                    num_dice = min(3, t.armies - 1)
                    ratio = t.armies / max(1, nb.armies)
                    candidates.append((ratio, AttackAction(t.name, n_name, num_dice)))

        candidates.sort(key=lambda x: x[0], reverse=True)
        return [action for _, action in candidates[: self.top_k_moves]]

    # ---------------------------------------------------------------- fortify

    def _choose_fortify(self, game_state):
        """Move armies from safe interior to most threatened border."""
        my_territories = game_state.get_player_territories(self.player_id)

        best_move = None
        best_value = self._evaluate(game_state)

        for src in my_territories:
            if src.armies < 2:
                continue
            src_has_enemies = any(
                game_state.board.get(n) and game_state.board.get(n).owner != self.player_id
                for n in src.neighbors
            )
            if src_has_enemies:
                continue  # don't weaken border

            for dst in my_territories:
                if dst.name == src.name:
                    continue
                dst_has_enemies = any(
                    game_state.board.get(n) and game_state.board.get(n).owner != self.player_id
                    for n in dst.neighbors
                )
                if not dst_has_enemies:
                    continue

                if game_state._are_connected(src.name, dst.name):
                    sim = self._copy_state(game_state)
                    sim_src = sim.board.get(src.name)
                    sim_dst = sim.board.get(dst.name)
                    armies_to_move = src.armies - 1
                    sim_src.armies -= armies_to_move
                    sim_dst.armies += armies_to_move

                    value = self._evaluate(sim)
                    if value > best_value:
                        best_value = value
                        best_move = FortifyAction(src.name, dst.name, armies_to_move)

        return best_move if best_move else EndPhaseAction()

    # -------------------------------------------------------------- evaluate

    def _evaluate(self, game_state):
        """Heuristic board evaluation from this agent's perspective.

        Components:
        - Territory count advantage
        - Army count advantage
        - Continent control bonuses
        - Border strength (ratio of our border armies to enemy border armies)
        """
        all_territories = game_state.board.all_territories()
        my_territories = [t for t in all_territories if t.owner == self.player_id]
        total = len(all_territories)

        if not my_territories:
            return -1000.0
        if len(my_territories) == total:
            return 1000.0

        # Territory ratio
        territory_score = (len(my_territories) / total) * 20.0

        # Army advantage
        my_armies = sum(t.armies for t in my_territories)
        total_armies = sum(t.armies for t in all_territories)
        army_score = (my_armies / max(1, total_armies)) * 15.0

        # Continent control
        continent_score = 0.0
        continent_counts = {}
        continent_totals = {}
        for t in all_territories:
            continent_totals[t.continent] = continent_totals.get(t.continent, 0) + 1
        for t in my_territories:
            continent_counts[t.continent] = continent_counts.get(t.continent, 0) + 1

        for continent, ct_total in continent_totals.items():
            owned = continent_counts.get(continent, 0)
            bonus = CONTINENT_BONUSES.get(continent, 0)
            if owned == ct_total:
                continent_score += bonus * 3.0
            elif owned >= ct_total - 1:
                continent_score += bonus * 1.5
            elif owned > ct_total // 2:
                continent_score += bonus * 0.5

        # Border strength
        border_score = 0.0
        for t in my_territories:
            for n_name in t.neighbors:
                nb = game_state.board.get(n_name)
                if nb and nb.owner != self.player_id:
                    ratio = t.armies / max(1, nb.armies)
                    border_score += min(ratio, 3.0)

        return territory_score + army_score + continent_score + border_score

    # ----------------------------------------------------------------- utils

    @staticmethod
    def _copy_state(game_state):
        """Deep copy the game state for simulation."""
        sim = GameState.__new__(GameState)
        sim.num_players = game_state.num_players
        sim.current_player = game_state.current_player
        sim.phase = game_state.phase
        sim.armies_to_deploy = game_state.armies_to_deploy
        sim.turn_number = game_state.turn_number

        from .board import Board
        sim.board = Board()
        for name, t in game_state.board.territories.items():
            sim_t = sim.board.get(name)
            sim_t.owner = t.owner
            sim_t.armies = t.armies

        return sim
