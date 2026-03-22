"""MCTS agent for Risk using UCT."""

import math
import random
import copy
from .agent import Agent, RandomAgent
from .action import Phase, DeployAction, AttackAction, FortifyAction, EndPhaseAction
from .game_state import GameState
from .options import RiskAIGameOptions
from .run import run_game


class MCTSNode:
    __slots__ = ["action", "parent", "children", "wins", "visits",
                 "untried_actions", "player_id"]

    def __init__(self, action=None, parent=None, player_id=None):
        self.action = action
        self.parent = parent
        self.children = []
        self.wins = 0.0
        self.visits = 0
        self.untried_actions = []
        self.player_id = player_id

    def ucb1(self, exploration=1.41):
        if self.visits == 0:
            return float("inf")
        exploitation = self.wins / self.visits
        exploration_term = exploration * math.sqrt(
            math.log(self.parent.visits) / self.visits
        )
        return exploitation + exploration_term

    def best_child(self, exploration=1.41):
        return max(self.children, key=lambda c: c.ucb1(exploration))

    def best_action_child(self):
        return max(self.children, key=lambda c: c.visits)

    @property
    def is_fully_expanded(self):
        return len(self.untried_actions) == 0

    @property
    def is_leaf(self):
        return len(self.children) == 0


class MCTSAgent(Agent):
    """UCT-based MCTS agent. Configurable simulation count and rollout depth."""

    def __init__(self, player_id, num_simulations=200, max_rollout_turns=100,
                 exploration=1.41, name=None):
        super().__init__(player_id, name)
        self.num_simulations = num_simulations
        self.max_rollout_turns = max_rollout_turns
        self.exploration = exploration

    def choose_action(self, game_state):
        if game_state.phase == Phase.DEPLOY:
            return self._choose_deploy(game_state)
        elif game_state.phase == Phase.ATTACK:
            return self._choose_attack(game_state)
        elif game_state.phase == Phase.FORTIFY:
            return self._choose_fortify(game_state)

    def _choose_deploy(self, game_state):
        actions = self._get_deploy_candidates(game_state)
        if len(actions) <= 1:
            return actions[0] if actions else DeployAction(
                game_state.get_player_territories(self.player_id)[0].name,
                game_state.armies_to_deploy,
            )
        return self._run_mcts(game_state, actions)

    def _get_deploy_candidates(self, game_state):
        candidates = []
        for t in game_state.get_player_territories(self.player_id):
            has_enemy = any(
                game_state.board.get(n) and game_state.board.get(n).owner != self.player_id
                for n in t.neighbors
            )
            if has_enemy:
                candidates.append(DeployAction(t.name, game_state.armies_to_deploy))
        # fallback
        if not candidates:
            t = game_state.get_player_territories(self.player_id)[0]
            candidates.append(DeployAction(t.name, game_state.armies_to_deploy))
        return candidates

    def _choose_attack(self, game_state):
        actions = self._get_attack_candidates(game_state)
        if not actions:
            return EndPhaseAction()
        # can always choose to stop
        actions.append(EndPhaseAction())
        return self._run_mcts(game_state, actions)

    def _get_attack_candidates(self, game_state):
        seen_targets = set()
        candidates = []
        attacks = []

        for t in game_state.get_player_territories(self.player_id):
            if t.armies < 2:
                continue
            for n_name in t.neighbors:
                nb = game_state.board.get(n_name)
                if nb and nb.owner != self.player_id:
                    num_dice = min(3, t.armies - 1)
                    ratio = t.armies / max(1, nb.armies)
                    attacks.append((ratio, t.name, n_name, num_dice))

        # best ratio per target, up to 8
        attacks.sort(key=lambda x: x[0], reverse=True)
        for ratio, from_t, to_t, dice in attacks:
            if to_t not in seen_targets and len(candidates) < 8:
                seen_targets.add(to_t)
                candidates.append(AttackAction(from_t, to_t, dice))

        return candidates

    def _choose_fortify(self, game_state):
        actions = self._get_fortify_candidates(game_state)
        if not actions:
            return EndPhaseAction()
        actions.append(EndPhaseAction())
        if len(actions) <= 1:
            return actions[0]
        return self._run_mcts(game_state, actions)

    def _get_fortify_candidates(self, game_state):
        candidates = []
        my_territories = game_state.get_player_territories(self.player_id)

        for src in my_territories:
            if src.armies < 2:
                continue
            src_has_enemies = any(
                game_state.board.get(n) and game_state.board.get(n).owner != self.player_id
                for n in src.neighbors
            )
            if src_has_enemies:
                continue

            for dst in my_territories:
                if dst.name == src.name:
                    continue
                dst_has_enemies = any(
                    game_state.board.get(n) and game_state.board.get(n).owner != self.player_id
                    for n in dst.neighbors
                )
                if dst_has_enemies and game_state._are_connected(src.name, dst.name):
                    candidates.append(
                        FortifyAction(src.name, dst.name, src.armies - 1)
                    )
                    break  # one target per source

        return candidates[:6]

    def _run_mcts(self, game_state, actions):
        root = MCTSNode(player_id=self.player_id)
        root.untried_actions = list(actions)

        for _ in range(self.num_simulations):
            node = root
            sim_state = _copy_state(game_state)

            # selection
            while node.is_fully_expanded and not node.is_leaf:
                node = node.best_child(self.exploration)
                if node.action is not None:
                    _apply_action_safe(sim_state, node.action)

            # expansion
            if node.untried_actions:
                action = node.untried_actions.pop(
                    random.randrange(len(node.untried_actions))
                )
                _apply_action_safe(sim_state, action)
                child = MCTSNode(action=action, parent=node, player_id=self.player_id)
                node.children.append(child)
                node = child

            # simulation
            result = self._rollout(sim_state)

            # backprop
            while node is not None:
                node.visits += 1
                node.wins += result
                node = node.parent

        # most visited = most robust
        if not root.children:
            return actions[0] if actions else EndPhaseAction()

        best = root.best_action_child()
        return best.action

    def _rollout(self, game_state):
        turn_limit = game_state.turn_number + self.max_rollout_turns

        while game_state.get_winner() is None and game_state.turn_number < turn_limit:
            player = game_state.current_player
            phase = game_state.phase

            if phase == Phase.DEPLOY:
                territories = game_state.get_player_territories(player)
                if territories:
                    t = random.choice(territories)
                    action = DeployAction(t.name, game_state.armies_to_deploy)
                else:
                    break
            elif phase == Phase.ATTACK:
                if random.random() < 0.5:
                    action = EndPhaseAction()
                else:
                    attackable = []
                    for t in game_state.get_player_territories(player):
                        if t.armies < 2:
                            continue
                        for n_name in t.neighbors:
                            nb = game_state.board.get(n_name)
                            if nb and nb.owner != player:
                                attackable.append((t, nb))
                    if attackable:
                        atk, defn = random.choice(attackable)
                        dice = min(3, atk.armies - 1)
                        action = AttackAction(atk.name, defn.name, dice)
                    else:
                        action = EndPhaseAction()
            elif phase == Phase.FORTIFY:
                action = EndPhaseAction()
            else:
                break

            try:
                game_state.apply_action(action)
            except (ValueError, IndexError):
                # Invalid action in rollout, just end phase
                try:
                    game_state.apply_action(EndPhaseAction())
                except ValueError:
                    break

        # score it
        winner = game_state.get_winner()
        if winner == self.player_id:
            return 1.0
        elif winner is not None:
            return 0.0
        else:
            # no winner yet, use territory ratio
            my_count = len(game_state.get_player_territories(self.player_id))
            total = len(game_state.board.all_territories())
            return my_count / total


def _copy_state(game_state):
    from .board import Board

    sim = GameState.__new__(GameState)
    sim.num_players = game_state.num_players
    sim.current_player = game_state.current_player
    sim.phase = game_state.phase
    sim.armies_to_deploy = game_state.armies_to_deploy
    sim.turn_number = game_state.turn_number

    sim.board = Board()
    for name, t in game_state.board.territories.items():
        sim_t = sim.board.get(name)
        sim_t.owner = t.owner
        sim_t.armies = t.armies

    return sim


def _apply_action_safe(game_state, action):
    try:
        game_state.apply_action(action)
    except (ValueError, IndexError):
        pass
