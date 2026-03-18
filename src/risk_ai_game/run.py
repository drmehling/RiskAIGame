"""Run a game of Risk between AI agents."""

from .action import AttackAction
from .game_state import GameState
from .options import RiskAIGameOptions

# Basic blocking game main loop.
# For use in command line applicaitons.
# Returns the index of the winning player in the agent list, or -1 for a tie.
def run_game(opts: RiskAIGameOptions) -> int:
    agents = opts.agents

    game = GameState(num_players=len(agents))
    if opts.initial_board_setup is not None:
        opts.initial_board_setup(game)
    else:
        game.setup_random()

    telemetry = opts.game_telemetry
    if telemetry is not None:
        telemetry.on_game_start(game)

    if opts.verbose:
        print(f"Risk Game: {len(agents)} players, {len(game.board.all_territories())} territories")
        for agent in agents:
            territories = game.get_player_territories(agent.player_id)
            print(f"  {agent}: {len(territories)} territories")
        print()

    while game.get_winner() is None and game.turn_number < opts.max_turns:
        agent = agents[game.current_player]
        if telemetry is not None:
            telemetry.on_before_action(game)
        action = agent.choose_action(game)
        result = game.apply_action(action)
        if telemetry is not None:
            telemetry.on_action(game, action, result)

        if opts.verbose and isinstance(action, AttackAction):
            outcome = "CONQUERED" if result.get("conquered") else "repelled"
            print(
                f"  Turn {game.turn_number} | {agent} attacks "
                f"{action.from_territory} -> {action.to_territory}: "
                f"{result['attack_dice']} vs {result['defend_dice']} = {outcome}"
            )
            if "eliminated_player" in result:
                print(f"  *** Player {result['eliminated_player']} eliminated! ***")

    winner = game.get_winner()
    if telemetry is not None:
        telemetry.on_game_end(game, winner)

    if opts.verbose:
        print()
        if winner is not None:
            print(f"Winner: {agents[winner]} in {game.turn_number} turns!")
        else:
            print(f"No winner after {opts.max_turns} turns")
            for agent in agents:
                count = len(game.get_player_territories(agent.player_id))
                print(f"  {agent}: {count} territories")

    return winner if winner is not None else -1
