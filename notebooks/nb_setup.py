"""
Jupyter support for RiskAIGame.

Working in a jupyter notebook should be as simple as importing this module.
That should give you access to all game code.
That should give you access to jupyter specific (IPython) code.
"""

import sys
from pathlib import Path

# nb_setup.py lives in notebooks/, so parent is project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# Re-export commonly used items for convenience
from risk_ai_game import (
    GameState,
    render_state,
    render_state_from_game_state,
)

# Draw the game state into a jupyter notebook
# This convenience function is here to ensure jupyter (IPython) code does not
# pollute our main package.
def display_game_state(state, player_colors=None, width=None):
    from IPython.display import SVG, display

    svg_bytes = render_state_from_game_state(state, player_colors=player_colors, width=width)
    display(SVG(svg_bytes))

# Display a map in a "typical" way from game state.
def display_map(territory_fills, territory_text, width=None):
    from IPython.display import SVG, display

    svg_bytes = render_state(territory_fills, territory_text, width=width)
    display(SVG(svg_bytes))
