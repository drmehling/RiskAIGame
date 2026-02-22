"""Run a game of Risk between AI agents."""

from .action import AttackAction
from .game_state import GameState

# Basic blocking game main loop.
# For use in command line applicaitons.
def run_game(agents, max_turns=500, verbose=True):
    game = GameState(num_players=len(agents))
    game.setup_random()

    if verbose:
        print(f"Risk Game: {len(agents)} players, {len(game.board.all_territories())} territories")
        for agent in agents:
            territories = game.get_player_territories(agent.player_id)
            print(f"  {agent}: {len(territories)} territories")
        print()

    while game.get_winner() is None and game.turn_number < max_turns:
        agent = agents[game.current_player]
        action = agent.choose_action(game)
        result = game.apply_action(action)

        if verbose and isinstance(action, AttackAction):
            outcome = "CONQUERED" if result.get("conquered") else "repelled"
            print(
                f"  Turn {game.turn_number} | {agent} attacks "
                f"{action.from_territory} -> {action.to_territory}: "
                f"{result['attack_dice']} vs {result['defend_dice']} = {outcome}"
            )
            if "eliminated_player" in result:
                print(f"  *** Player {result['eliminated_player']} eliminated! ***")

    winner = game.get_winner()
    if verbose:
        print()
        if winner is not None:
            print(f"Winner: {agents[winner]} in {game.turn_number} turns!")
        else:
            print(f"No winner after {max_turns} turns")
            for agent in agents:
                count = len(game.get_player_territories(agent.player_id))
                print(f"  {agent}: {count} territories")

    return winner
