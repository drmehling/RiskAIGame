from .agent import Agent
from .greedy_agent import GreedyAgent
from .action import Phase, DeployAction, AttackAction, FortifyAction, EndPhaseAction
from .game_state import GameState, CONTINENT_BONUSES

# dice outcomes after expeciminimax
DICE_OUTCOMES = {}

def _compute_dice_outcomes():
    from itertools import product

    for n_atk in range(1, 4):
        for n_def in range(1, 3):
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

            DICE_OUTCOMES[(n_atk, n_def)] = [
                (a_loss, d_loss, count / total)
                for (a_loss, d_loss), count in outcomes.items()
            ]

_compute_dice_outcomes()

# An Expectiminimax agent using;
# basic successor function based on greedy agent with variations.
# very simple but effective evaluation function using reinforcement count.
# uses a depth-limited search with a greedy action as the initial action.
# then uses a top-k actions to search the tree.
class ExpectiminimaxAgent2(Agent):
    def __init__(self, player_id, max_depth=1, top_k=3, name=None):
        super().__init__(player_id, name)
        self.max_depth = max_depth
        self.top_k = top_k
        self.greedy = GreedyAgent(player_id)

    def choose_action(self, game_state):
        if self.max_depth <= 0:
            return self.greedy.choose_action(game_state)

        actions = self._generate_actions(game_state)
        if not actions:
            return EndPhaseAction()

        greedy_action = actions[0]
        best_action = greedy_action
        # implementing alpha-beta pruning
        # alpha is the best value found so far for the maximizing player
        # beta is the best value found so far for the minimizing player
        alpha = float("-inf")
        beta = float("inf")
        best_value = self._action_value(game_state, greedy_action, 0, alpha, beta)
        alpha = best_value

        for action in actions[1:]:
            value = self._action_value(game_state, action, 0, alpha, beta)
            if value > best_value:
                best_value = value
                best_action = action
            alpha = max(alpha, value)

        return best_action

    def _action_value(self, game_state, action, depth, alpha, beta):
        if isinstance(action, AttackAction):
            return self._expected_attack_value(game_state, action, depth, alpha, beta)

        sim = self._apply_action(game_state, action)
        return self._search(sim, depth + 1, alpha, beta)

    # the primary recursive search function.
    def _search(self, game_state, depth, alpha, beta):
        winner = game_state.get_winner()
        if winner is not None:
            return 1000.0 if winner == self.player_id else -1000.0

        if depth >= self.max_depth:
            return self._evaluate(game_state)

        actions = self._generate_actions(game_state)
        if not actions:
            return self._evaluate(game_state)

        is_max = (game_state.current_player == self.player_id)

        if is_max:
            # accrue the best alpha value.
            v = float("-inf")
            for action in actions:
                v = max(v, self._action_value(game_state, action, depth, alpha, beta))
                alpha = max(alpha, v)
                # bail if best score is already better than the worst score.
                if alpha >= beta:
                    break
            return v
        else:
            v = float("inf")
            for action in actions:
                v = min(v, self._action_value(game_state, action, depth, alpha, beta))
                beta = min(beta, v)
                # bail if best score is already worse than the best score.
                if beta <= alpha:
                    break
            return v

    # the expected value calculation for the attack action.
    # Primary implementation of the expected value calculation for the attack action.
    def _expected_attack_value(self, game_state, action, depth, alpha, beta):
        attacker = game_state.board.get(action.from_territory)
        defender = game_state.board.get(action.to_territory)

        if attacker is None or defender is None:
            return self._evaluate(game_state)
        if attacker.owner != game_state.current_player:
            return self._evaluate(game_state)
        if defender.owner == game_state.current_player:
            return self._evaluate(game_state)
        if attacker.armies < 2:
            return self._evaluate(game_state)

        n_atk = min(action.num_dice, attacker.armies - 1)
        n_def = min(2, defender.armies)
        outcomes = DICE_OUTCOMES.get((n_atk, n_def), [])

        if not outcomes:
            return self._evaluate(game_state)

        total = 0.0
        acting_player = game_state.current_player

        for a_loss, d_loss, prob in outcomes:
            sim = self._copy_state(game_state)
            sim_attacker = sim.board.get(action.from_territory)
            sim_defender = sim.board.get(action.to_territory)

            sim_attacker.armies -= a_loss
            sim_defender.armies -= d_loss

            if sim_defender.armies <= 0:
                sim_defender.owner = acting_player

                move_armies = min(n_atk, sim_attacker.armies - 1) if sim_attacker.armies > 1 else 1
                move_armies = max(1, move_armies)
                sim_attacker.armies -= move_armies
                sim_defender.armies = move_armies

            total += prob * self._search(sim, depth + 1, alpha, beta)

        return total

    def _generate_actions(self, game_state):
        if game_state.phase == Phase.DEPLOY:
            return self._generate_deploy_actions(game_state)
        elif game_state.phase == Phase.ATTACK:
            return self._generate_attack_actions(game_state)
        elif game_state.phase == Phase.FORTIFY:
            return self._generate_fortify_actions(game_state)
        return []

    def _action_key(self, action):
        if isinstance(action, EndPhaseAction):
            return ("end",)
        if isinstance(action, DeployAction):
            return ("deploy", action.territory, action.armies)
        if isinstance(action, AttackAction):
            return ("attack", action.from_territory, action.to_territory, action.num_dice)
        if isinstance(action, FortifyAction):
            return ("fortify", action.from_territory, action.to_territory, action.armies)
        return (type(action).__name__, repr(action))

    # if duplicate actions are found in the action list, just keep the first one.
    def _dedupe_keep_order(self, actions):
        seen = set()
        out = []
        for action in actions:
            key = self._action_key(action)
            if key not in seen:
                seen.add(key)
                out.append(action)
        return out

    def _generate_deploy_actions(self, game_state):
        greedy_action = self.greedy.choose_action(game_state)

        if self.top_k <= 1:
            return [greedy_action]

        player = game_state.current_player
        my_territories = game_state.get_player_territories(player)
        all_territories = game_state.board.all_territories()

        scored = []
        for t in my_territories:
            score = self._deploy_score(t, game_state, player, all_territories)
            action = DeployAction(t.name, game_state.armies_to_deploy)
            scored.append((score, action))

        scored.sort(key=lambda x: x[0], reverse=True)

        actions = [greedy_action]
        for _, action in scored:
            actions.append(action)
            if len(self._dedupe_keep_order(actions)) >= self.top_k:
                break

        return self._dedupe_keep_order(actions)[:self.top_k]

    def _generate_attack_actions(self, game_state):
        greedy_action = self.greedy.choose_action(game_state)

        if self.top_k <= 1:
            return [greedy_action]

        player = game_state.current_player
        scored = []

        for t in game_state.get_player_territories(player):
            if t.armies < 2:
                continue
            for n_name in t.neighbors:
                nb = game_state.board.get(n_name)
                if nb and nb.owner != player:
                    score = self._attack_score(t, nb, game_state, player)
                    action = AttackAction(t.name, nb.name, min(3, t.armies - 1))
                    scored.append((score, action))

        scored.sort(key=lambda x: x[0], reverse=True)

        actions = [greedy_action]

        for score, action in scored:
            if score <= 0:
                break
            actions.append(action)
            if len(self._dedupe_keep_order(actions)) >= self.top_k:
                break

        actions.append(EndPhaseAction())

        return self._dedupe_keep_order(actions)[:self.top_k]

    def _generate_fortify_actions(self, game_state):
        greedy_action = self.greedy.choose_action(game_state)

        if self.top_k <= 1:
            return [greedy_action]

        player = game_state.current_player
        my_territories = game_state.get_player_territories(player)

        scored = []

        for src in my_territories:
            if src.armies < 2:
                continue

            src_has_enemies = any(
                game_state.board.get(n) and game_state.board.get(n).owner != player
                for n in src.neighbors
            )

            for dst in my_territories:
                if src.name == dst.name:
                    continue

                dst_has_enemies = any(
                    game_state.board.get(n) and game_state.board.get(n).owner != player
                    for n in dst.neighbors
                )

                if not src_has_enemies and dst_has_enemies and game_state._are_connected(src.name, dst.name):
                    enemy_pressure = sum(
                        game_state.board.get(n).armies
                        for n in dst.neighbors
                        if game_state.board.get(n) and game_state.board.get(n).owner != player
                    )
                    value = enemy_pressure / max(1, dst.armies)
                    action = FortifyAction(src.name, dst.name, src.armies - 1)
                    scored.append((value, action))

        scored.sort(key=lambda x: x[0], reverse=True)

        actions = [greedy_action]
        for _, action in scored:
            actions.append(action)
            if len(self._dedupe_keep_order(actions)) >= self.top_k:
                break

        actions.append(EndPhaseAction())

        return self._dedupe_keep_order(actions)[:self.top_k]

    # the primary evaluation function.
    # Keeping this as simple as possible as it seems effective.
    def _evaluate(self, game_state):
        winner = game_state.get_winner()
        if winner is not None:
            return 1000.0 if winner == self.player_id else -1000.0
        return float(self._reinforcement_count(game_state, self.player_id))

    def _reinforcement_count(self, game_state, player_id):
        territories = game_state.board.territories.values()
        continent_sizes = game_state.board.continent_sizes()

        owned_count = 0
        owned_by_continent = {c: 0 for c in continent_sizes}

        for t in territories:
            if t.owner == player_id:
                owned_count += 1
                owned_by_continent[t.continent] += 1

        if owned_count == 0:
            return 0

        territory_bonus = max(3, owned_count // 3)

        continent_bonus = 0
        for continent, count in owned_by_continent.items():
            if count == continent_sizes[continent]:
                continent_bonus += CONTINENT_BONUSES.get(continent, 0)

        return territory_bonus + continent_bonus

    def _deploy_score(self, territory, game_state, player_id, all_territories):
        score = 0.0

        enemy_pressure = 0
        for n_name in territory.neighbors:
            nb = game_state.board.get(n_name)
            if nb and nb.owner != player_id:
                enemy_pressure += nb.armies
        if enemy_pressure > 0:
            score += enemy_pressure / max(1, territory.armies) * 3.0

        score += self._continent_priority(territory.continent, game_state, player_id, all_territories)

        has_enemy_neighbor = any(
            game_state.board.get(n) and game_state.board.get(n).owner != player_id
            for n in territory.neighbors
        )
        if not has_enemy_neighbor:
            score *= 0.1

        return score

    def _attack_score(self, attacker, defender, game_state, player_id):
        ratio = attacker.armies / max(1, defender.armies)
        score = (ratio - 1.0) * 5.0

        all_territories = game_state.board.all_territories()
        continent = defender.continent
        continent_territories = [t for t in all_territories if t.continent == continent]
        owned = sum(1 for t in continent_territories if t.owner == player_id)
        total = len(continent_territories)

        if owned == total - 1:
            bonus = CONTINENT_BONUSES.get(continent, 0)
            score += bonus * 3.0
        elif owned >= total - 2:
            bonus = CONTINENT_BONUSES.get(continent, 0)
            score += bonus * 1.5

        if attacker.armies <= 2:
            score -= 3.0

        return score

    def _continent_priority(self, continent, game_state, player_id, all_territories):
        continent_territories = [t for t in all_territories if t.continent == continent]
        total = len(continent_territories)
        owned = sum(1 for t in continent_territories if t.owner == player_id)
        bonus = CONTINENT_BONUSES.get(continent, 0)

        if owned == total:
            return bonus * 1.0
        elif owned == total - 1:
            return bonus * 4.0
        elif owned >= total // 2:
            return bonus * (owned / total) * 2.0
        else:
            return 0.0

    def _apply_action(self, game_state, action):
        sim = self._copy_state(game_state)
        player = sim.current_player

        if isinstance(action, DeployAction):
            t = sim.board.get(action.territory)
            t.armies += action.armies
            sim.armies_to_deploy = 0
            sim.phase = Phase.ATTACK
            return sim

        if isinstance(action, EndPhaseAction):
            if sim.phase == Phase.ATTACK:
                sim.phase = Phase.FORTIFY
            elif sim.phase == Phase.FORTIFY:
                sim.current_player = 1 - sim.current_player
                sim.phase = Phase.DEPLOY
                sim.armies_to_deploy = self._reinforcement_count(sim, sim.current_player)
                sim.turn_number += 1
            return sim

        if isinstance(action, FortifyAction):
            src = sim.board.get(action.from_territory)
            dst = sim.board.get(action.to_territory)
            armies = min(action.armies, src.armies - 1)
            if armies > 0:
                src.armies -= armies
                dst.armies += armies

            sim.current_player = 1 - player
            sim.phase = Phase.DEPLOY
            sim.armies_to_deploy = self._reinforcement_count(sim, sim.current_player)
            sim.turn_number += 1
            return sim

        return sim

    @staticmethod
    def _copy_state(game_state):
        sim = GameState.__new__(GameState)
        sim.num_players = game_state.num_players
        sim.current_player = game_state.current_player
        sim.phase = game_state.phase
        sim.armies_to_deploy = game_state.armies_to_deploy
        sim.turn_number = game_state.turn_number

        sim.board = game_state.board.copy_state()
        return sim
