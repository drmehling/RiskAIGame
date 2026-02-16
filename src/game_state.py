"""Game state and logic for Risk."""

from board import Board
from action import Phase, DeployAction, AttackAction, FortifyAction, EndPhaseAction
import random

# continent bonuses (from the rulebook)
CONTINENT_BONUSES = {
    "North America": 5,
    "South America": 2,
    "Europe": 5,
    "Africa": 3,
    "Asia": 7,
    "Australia": 2,
}


class GameState:
    def __init__(self, num_players=2):
        self.board = Board()
        self.num_players = num_players
        self.current_player = 0
        self.phase = Phase.DEPLOY
        self.armies_to_deploy = 0
        self.turn_number = 0

    def setup_random(self):
        """Randomly deal out territories and put 1 army on each."""
        territories = self.board.all_territories()
        random.shuffle(territories)
        for i, t in enumerate(territories):
            t.owner = i % self.num_players
            t.armies = 1
        self.armies_to_deploy = self.get_reinforcements(self.current_player)

    def get_player_territories(self, player_id):
        return [t for t in self.board.all_territories() if t.owner == player_id]

    def get_reinforcements(self, player_id):
        """Calculate how many armies a player gets. base + continent bonuses"""
        territories = self.get_player_territories(player_id)
        base = max(3, len(territories) // 3)

        # check continent bonuses
        continent_counts = {}
        for t in territories:
            continent_counts[t.continent] = continent_counts.get(t.continent, 0) + 1

        all_territories = self.board.all_territories()
        continent_totals = {}
        for t in all_territories:
            continent_totals[t.continent] = continent_totals.get(t.continent, 0) + 1

        bonus = 0
        for continent, total in continent_totals.items():
            if continent_counts.get(continent, 0) == total:
                bonus += CONTINENT_BONUSES.get(continent, 0)

        return base + bonus

    def apply_action(self, action):
        """Apply action and return result dict."""
        if isinstance(action, DeployAction):
            return self._apply_deploy(action)
        elif isinstance(action, AttackAction):
            return self._apply_attack(action)
        elif isinstance(action, FortifyAction):
            return self._apply_fortify(action)
        elif isinstance(action, EndPhaseAction):
            return self._apply_end_phase()
        else:
            raise ValueError(f"Unknown action type: {type(action)}")

    def _apply_deploy(self, action):
        if self.phase != Phase.DEPLOY:
            raise ValueError(f"Cannot deploy during {self.phase} phase")

        territory = self.board.get(action.territory)
        if territory is None:
            raise ValueError(f"Unknown territory: {action.territory}")
        if territory.owner != self.current_player:
            raise ValueError(f"{action.territory} not owned by player {self.current_player}")
        if action.armies < 1 or action.armies > self.armies_to_deploy:
            raise ValueError(f"Invalid army count: {action.armies}")

        territory.armies += action.armies
        self.armies_to_deploy -= action.armies

        if self.armies_to_deploy == 0:
            self.phase = Phase.ATTACK

        return {"deployed": action.armies, "territory": action.territory}

    def _apply_attack(self, action):
        if self.phase != Phase.ATTACK:
            raise ValueError(f"Cannot attack during {self.phase} phase")

        attacker = self.board.get(action.from_territory)
        defender = self.board.get(action.to_territory)

        if attacker is None or defender is None:
            raise ValueError("Invalid territory name")
        if attacker.owner != self.current_player:
            raise ValueError(f"{action.from_territory} not owned by current player")
        if defender.owner == self.current_player:
            raise ValueError("Cannot attack your own territory")
        if action.to_territory not in attacker.neighbors:
            raise ValueError(f"{action.to_territory} not adjacent to {action.from_territory}")
        if attacker.armies < 2:
            raise ValueError("Need at least 2 armies to attack")
        if action.num_dice < 1 or action.num_dice > 3:
            raise ValueError("Dice must be 1-3")
        if action.num_dice >= attacker.armies:
            raise ValueError(f"Not enough armies for {action.num_dice} dice")

        # roll dice
        attack_dice = sorted([random.randint(1, 6) for _ in range(action.num_dice)], reverse=True)
        defend_dice_count = min(2, defender.armies)
        defend_dice = sorted([random.randint(1, 6) for _ in range(defend_dice_count)], reverse=True)

        # compare highest dice pairs
        attacker_losses = 0
        defender_losses = 0
        for a, d in zip(attack_dice, defend_dice):
            if a > d:
                defender_losses += 1
            else:
                attacker_losses += 1  # ties go to defender

        attacker.armies -= attacker_losses
        defender.armies -= defender_losses

        conquered = False
        if defender.armies <= 0:
            conquered = True
            defender.owner = self.current_player
            # move armies in
            moved = action.num_dice
            attacker.armies -= moved
            defender.armies = moved

        result = {
            "attack_dice": attack_dice,
            "defend_dice": defend_dice,
            "attacker_losses": attacker_losses,
            "defender_losses": defender_losses,
            "conquered": conquered,
            "from": action.from_territory,
            "to": action.to_territory,
        }

        if conquered:
            eliminated = self._check_elimination()
            if eliminated is not None:
                result["eliminated_player"] = eliminated

        return result

    def _apply_fortify(self, action):
        if self.phase != Phase.FORTIFY:
            raise ValueError(f"Cannot fortify during {self.phase} phase")

        src = self.board.get(action.from_territory)
        dst = self.board.get(action.to_territory)

        if src is None or dst is None:
            raise ValueError("Invalid territory")
        if src.owner != self.current_player or dst.owner != self.current_player:
            raise ValueError("Both territories must be yours")
        if action.armies < 1 or action.armies >= src.armies:
            raise ValueError("Invalid number of armies to move")
        if not self._are_connected(action.from_territory, action.to_territory):
            raise ValueError("Territories are not connected through your land")

        src.armies -= action.armies
        dst.armies += action.armies
        self._advance_turn()

        return {"from": action.from_territory, "to": action.to_territory, "armies": action.armies}

    def _apply_end_phase(self):
        if self.phase == Phase.DEPLOY:
            if self.armies_to_deploy > 0:
                raise ValueError(f"Still have {self.armies_to_deploy} armies to deploy")
            self.phase = Phase.ATTACK
        elif self.phase == Phase.ATTACK:
            self.phase = Phase.FORTIFY
        elif self.phase == Phase.FORTIFY:
            self._advance_turn()
        return {"phase_ended": self.phase.name}

    def _advance_turn(self):
        self.current_player = (self.current_player + 1) % self.num_players
        self.phase = Phase.DEPLOY
        self.armies_to_deploy = self.get_reinforcements(self.current_player)
        self.turn_number += 1

    def next_turn(self):
        """kept for backwards compat"""
        self._advance_turn()

    def _are_connected(self, src_name, dst_name):
        """BFS to check if territories are connected through owned land."""
        player = self.board.get(src_name).owner
        visited = set()
        queue = [src_name]
        while queue:
            current = queue.pop(0)
            if current == dst_name:
                return True
            if current in visited:
                continue
            visited.add(current)
            t = self.board.get(current)
            for n in t.neighbors:
                nb = self.board.get(n)
                if nb and nb.owner == player and n not in visited:
                    queue.append(n)
        return False

    def _check_elimination(self):
        for p in range(self.num_players):
            if len(self.get_player_territories(p)) == 0:
                return p
        return None

    def get_winner(self):
        alive = [p for p in range(self.num_players) if self.get_player_territories(p)]
        if len(alive) == 1:
            return alive[0]
        return None

    def get_legal_actions(self):
        """Get all valid actions for current player/phase."""
        actions = []
        player = self.current_player

        if self.phase == Phase.DEPLOY:
            for t in self.get_player_territories(player):
                for n in range(1, self.armies_to_deploy + 1):
                    actions.append(DeployAction(t.name, n))

        elif self.phase == Phase.ATTACK:
            actions.append(EndPhaseAction())
            for t in self.get_player_territories(player):
                if t.armies < 2:
                    continue
                for neighbor_name in t.neighbors:
                    neighbor = self.board.get(neighbor_name)
                    if neighbor and neighbor.owner != player:
                        max_dice = min(3, t.armies - 1)
                        for dice in range(1, max_dice + 1):
                            actions.append(AttackAction(t.name, neighbor_name, dice))

        elif self.phase == Phase.FORTIFY:
            actions.append(EndPhaseAction())
            for t in self.get_player_territories(player):
                if t.armies < 2:
                    continue
                for other in self.get_player_territories(player):
                    if other.name != t.name and self._are_connected(t.name, other.name):
                        for n in range(1, t.armies):
                            actions.append(FortifyAction(t.name, other.name, n))

        return actions
