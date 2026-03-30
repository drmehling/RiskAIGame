#!/usr/bin/env python3
"""
Basic fastapi based dashboard for Risk.
See README to run in docker or locally: uvicorn src.dashboard:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import sys
from pathlib import Path

# This is pretty hamfisted, but ensure the risk_ai_game is importable when run from project root
ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import random
import threading
import traceback

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from risk_ai_game import game_state_to_render_dict, last_action_to_render_dict
from risk_ai_game.agent import Agent, AggressiveAgent, RandomAgent
from risk_ai_game.expectiminimax_agent import ExpectiminimaxAgent
from risk_ai_game.game_state import GameState
from risk_ai_game.greedy_agent import GreedyAgent
from risk_ai_game.mcts_agent import MCTSAgent

_AGENT_TYPES: tuple[str, ...] = (
    "aggressive",
    "random",
    "greedy",
    "expectiminimax",
    "mcts",
)


def _make_agent(agent_kind: str, player_id: int, display_name: str | None) -> Agent:
    kind = agent_kind.strip().lower()
    name = display_name.strip() if display_name and str(display_name).strip() else None
    if kind == "aggressive":
        return AggressiveAgent(player_id, name=name)
    if kind == "random":
        return RandomAgent(player_id, name=name)
    if kind == "greedy":
        return GreedyAgent(player_id, name=name)
    if kind == "expectiminimax":
        return ExpectiminimaxAgent(player_id, name=name)
    if kind == "mcts":
        return MCTSAgent(player_id, name=name)
    allowed = ", ".join(_AGENT_TYPES)
    raise ValueError(f"Unknown agent type {agent_kind!r}. Expected one of: {allowed}")


# a nonblocking game runner for the dashboard. Start, step, stop as needed.
# TODO: It might be advisable to move this to its own module in time, but this is fine for now.
class GameRunner:

    def __init__(self, max_turns: int = 1000):
        self.max_turns = max_turns
        self._game: GameState | None = None
        self._agents: list[Agent] | None = None
        self._stopped = False
        self._last_action = None
        self._last_result = None

    def start(
        self,
        num_players: int = 2,
        random_seed: int | None = None,
        player_configs: list[dict] | None = None,
    ) -> GameState | None:
        if num_players < 2:
            num_players = 2
        self._stopped = False
        self._last_action = None
        self._last_result = None
        if random_seed is not None:
            random.seed(random_seed)
        if player_configs is not None:
            if len(player_configs) != num_players:
                raise ValueError(
                    f"Expected {num_players} player slot(s), got {len(player_configs)} in 'players'."
                )
            self._agents = [
                _make_agent(str(c["agent"]), i, c.get("name"))
                for i, c in enumerate(player_configs)
            ]
        else:
            self._agents = [
                AggressiveAgent(0, name="Aggressive player") if i == 0 else RandomAgent(i)
                for i in range(num_players)
            ]
        self._game = GameState(num_players=num_players)
        self._game.setup_random()
        return self._game

    # Stop a game.
    def stop(self) -> None:
        self._stopped = True
    # Check if a game is running.
    def is_running(self) -> bool:
        if self._game is None or self._agents is None or self._stopped:
            return False
        winner = self._game.get_winner()
        return winner is None and self._game.turn_number < self.max_turns
    # Get the current game state.
    def get_state(self) -> GameState | None:
        return self._game

    # The most important method. Step the game by one action.
    # Returns the new game state and a boolean indicating if the game is still running.
    def step(self) -> tuple[GameState | None, bool]:
        self._last_action = None
        self._last_result = None
        if self._game is None or self._agents is None or self._stopped:
            return (self._game, False)
        winner = self._game.get_winner()
        if winner is not None or self._game.turn_number >= self.max_turns:
            return (self._game, False)
        agent = self._agents[self._game.current_player]
        action = agent.choose_action(self._game)
        result = self._game.apply_action(action)
        self._last_action = action
        self._last_result = result
        still_running = self.is_running()
        return (self._game, still_running)


# Now we add a little server to run the game and make stepping it accessible via a REST API.
app = FastAPI(title="Risk Game Demo")

# for debugging.
@app.exception_handler(Exception)
def show_500_traceback(request, exc):
    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    return PlainTextResponse(f"500 Error:\n\n{tb}", status_code=500, media_type="text/plain")
_game: GameRunner | None = None
# Uvicorn runs sync route handlers in a thread pool; without a lock, two fast step
# requests can both read the same GameState, choose actions, then apply in series—
# the second action may be illegal for the post-first state.
_game_lock = threading.Lock()


class PlayerSlot(BaseModel):
    agent: str
    name: str | None = None


class InitSettings(BaseModel):
    num_players: int = 2
    random_seed: int | None = None
    players: list[PlayerSlot] | None = None

    def to_dict(self) -> dict:
        return self.model_dump(exclude_none=False)

# All api responses are formatted the same.
# Basically we return the game state, with some additional metadata.
# Caller must hold _game_lock when reading mutating _game fields used here.
def _api_response(game, running: bool) -> dict:
    state = game_state_to_render_dict(game) if game else {}
    last_action = None
    if _game is not None and _game._last_action is not None and _game._last_result is not None:
        last_action = last_action_to_render_dict(_game._last_action, _game._last_result)
    current_player = game.current_player if game else 0
    phase = game.phase.name.lower() if game else "deploy"
    if phase == "deploy":
        phase = "reinforce"
    num_players = game.num_players if game else 2
    turn_number = game.turn_number if game else 0
    player_names = (
        [_game._agents[i].name for i in range(num_players)]
        if _game is not None and _game._agents is not None and len(_game._agents) >= num_players
        else None
    )
    return {
        "state": state,
        "running": running,
        "last_action": last_action,
        "current_player": current_player,
        "phase": phase,
        "num_players": num_players,
        "turn_number": turn_number,
        "player_names": player_names,
    }

# on client /api/start request, initiate a new game.
@app.post("/api/start")
def api_start(settings: InitSettings | None = None) -> dict:
    global _game
    with _game_lock:
        _game = GameRunner(max_turns=1000)
        opts = settings.to_dict() if settings else {}
        num_players = opts.get("num_players", 2)
        raw_players = opts.get("players")
        player_configs: list[dict] | None = None
        if raw_players is not None:
            player_configs = [
                {"agent": p["agent"], "name": p.get("name")} for p in raw_players
            ]
        try:
            game = _game.start(
                num_players=num_players,
                random_seed=opts.get("random_seed"),
                player_configs=player_configs,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        return _api_response(game, True)

# on client /api/stop request, stop the game.
@app.post("/api/stop")
def api_stop() -> dict:
    global _game
    with _game_lock:
        if _game is not None:
            _game.stop()
            _game = None
    return {"running": False}

# on client /api/state request, return the current game state.
@app.get("/api/state")
def api_state() -> dict:
    global _game
    with _game_lock:
        if _game is None or not _game.is_running():
            return {"state": {}, "running": False, "last_action": None, "current_player": 0, "phase": "reinforce", "num_players": 2, "turn_number": 0, "player_names": None}
        game = _game.get_state()
        return _api_response(game, True)

# on client /api/step request, step the game by one action.
@app.post("/api/step")
def api_step() -> dict:
    global _game
    with _game_lock:
        if _game is None:
            raise HTTPException(status_code=409, detail="No game; call POST /api/start first.")
        if not _game.is_running():
            raise HTTPException(status_code=409, detail="Game is stopped; call POST /api/start to restart.")
        game, running = _game.step()
        if game is None:
            raise HTTPException(status_code=409, detail="Game not running.")
        return _api_response(game, running)

# serve the static assets.
app.mount("/assets", StaticFiles(directory=str(ROOT / "src" / "assets")), name="assets")

# serve the (default)index.html file.
@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    try:
        html_path = ROOT / "static" / "index.html"
        return HTMLResponse(content=html_path.read_text())
    except Exception as e:
        tb = "".join(traceback.format_exception(type(e), e, e.__traceback__))
        return PlainTextResponse(f"500 Error:\n\n{tb}", status_code=500, media_type="text/plain")

# main entry point.
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.dashboard:app", host="0.0.0.0", port=8000, reload=True)
