
from pathlib import Path
from lxml import etree

# This is a mapping of game state territory names to the tags in assets/risk.map.svg
BOARD_NAME_TO_SVG_ID = {
    "Alaska": "alaska",
    "Northwest Territory": "northwest_ter",
    "Greenland": "greenland",
    "Alberta": "alberta",
    "Ontario": "ontario",
    "Quebec": "quebec",
    "Western United States": "western_us",
    "Eastern United States": "eastern_us",
    "Central America": "central_america",
    "Venezuela": "venezuela",
    "Brazil": "brazil",
    "Peru": "peru",
    "Argentina": "argentina",
    "Iceland": "iceland",
    "Great Britain": "great_britain",
    "Scandinavia": "scandanavia",
    "Northern Europe": "northern_europe",
    "Western Europe": "western_europe",
    "Southern Europe": "southern_europe",
    "Ukraine": "russia",
    "North Africa": "north_africa",
    "Egypt": "egypt",
    "East Africa": "east_africa",
    "Congo": "central_africa",
    "South Africa": "south_africa",
    "Madagascar": "madagascar",
    "Ural": "ural",
    "Siberia": "siberia",
    "Yakutsk": "yakutsk",
    "Kamchatka": "kamchatka",
    "Irkutsk": "irkutsk",
    "Mongolia": "mongolia",
    "Japan": "japan",
    "China": "china",
    "Afghanistan": "afghanistan",
    "Middle East": "middle_east",
    "India": "india",
    "Siam": "souheast_asia",
    "Indonesia": "indonesia",
    "New Guinea": "papua_new_guinea",
    "Western Australia": "western_australia",
    "Eastern Australia": "eastern_australia",
}

PLAYER_COLORS = [
    "#C94A44",  # red
    "#4C78A8",  # blue
    "#59A14F",  # green
    "#E3B23C",  # yellow
    "#8E6BBE",  # purple
    "#2F2F2F",  # black
]

# generate a dictionary which describes "last action taken"
def last_action_to_render_dict(action, result):
    if action is None or result is None:
        return None
    from .action import AttackAction, DeployAction
    if isinstance(action, AttackAction):
        from_svg = BOARD_NAME_TO_SVG_ID.get(action.from_territory)
        to_svg = BOARD_NAME_TO_SVG_ID.get(action.to_territory)
        if from_svg is None or to_svg is None:
            return None
        return {
            "type": "attack",
            "from": from_svg,
            "to": to_svg,
            "attacker_losses": result.get("attacker_losses", 0),
            "defender_losses": result.get("defender_losses", 0),
            "conquered": result.get("conquered", False),
        }
    if isinstance(action, DeployAction):
        svg_id = BOARD_NAME_TO_SVG_ID.get(action.territory)
        if svg_id is None:
            return None
        return {
            "type": "reinforce",
            "territory": svg_id,
            "armies": action.armies,
        }
    return None


# Convert GameState to a dictionary useable by rendering code below.
def game_state_to_render_dict(game_state):
    result = {}
    for t in game_state.board.all_territories():
        svg_id = BOARD_NAME_TO_SVG_ID.get(t.name)
        if svg_id is not None and t.owner is not None:
            result[svg_id] = {"owner": t.owner, "armies": t.armies}
    return result


# This code is tricky. Traverse the SVG tree, setting path fills and text values
# based lookups of territory names.
# Returns a modivied SVG as bytes for easy display.
def render_state(territory_fills, territory_text, width=None):
    parser = etree.XMLParser(remove_blank_text=False)
    tree = etree.parse(find_svg_path(), parser)
    root = tree.getroot()

    # helper: set the style attribute of an SVG element.
    def set_style_attr(el, key, value):
        style = el.get("style", "")
        parts = [p.strip() for p in style.split(";") if p.strip()]
        style_map = dict(p.split(":", 1) for p in parts if ":" in p)
        style_map[key] = value
        el.set("style", ";".join(f"{k}:{v}" for k, v in style_map.items()))

    # helper: fetch a group in the SVG tree by its id.
    # IDs are currently territory names.
    def get_path_in_group(group):
        paths = group.xpath("./*[local-name()='path']")
        return paths[0] if paths else None

    # Each group has a child called "text" which we can set to a label string.
    def get_text_in_group(group):
        texts = group.xpath("./*[local-name()='text']")
        return texts[0] if texts else None

    for terr_id, color in territory_fills.items():
        groups = root.xpath(f'//*[local-name()="g" and @id="{terr_id}"]')
        if groups:
            path_el = get_path_in_group(groups[0])
            if path_el is not None:
                path_el.set("fill", color)
                set_style_attr(path_el, "fill", color)

    for text_key, value in territory_text.items():
        terr_id = text_key.rstrip("_count") if text_key.endswith("_count") else text_key
        groups = root.xpath(f'//*[local-name()="g" and @id="{terr_id}"]')
        if groups:
            text_el = get_text_in_group(groups[0])
            if text_el is not None:
                text_el.text = str(value)

    # We also set the width of the SVG here as it seems like the most robust way to control it.
    if width is not None:
        root.set("width", f"{width}px")
        view_box = root.get("viewBox")
        if view_box:
            parts = view_box.split()
            if len(parts) >= 4:
                _, _, vb_w, vb_h = parts[:4]
                try:
                    h = int(float(width) * float(vb_h) / float(vb_w))
                    root.set("height", f"{h}px")
                except (ValueError, ZeroDivisionError):
                    pass

    return etree.tostring(root, encoding="utf-8")


# The primary method to render our GameState into an SVG.
# Returns the SVG as bytes for easy display.
# Accepts either a GameState or a dict from game_state_to_render_dict().
def render_state_from_game_state(state, player_colors=None, width=None):
    if not isinstance(state, dict):
        state = game_state_to_render_dict(state)
    colors = player_colors or PLAYER_COLORS

    territory_fills = {}
    territory_text = {}
    for tid, data in state.items():
        owner = data.get("owner", 0)
        armies = data.get("armies", 0)
        territory_fills[tid] = colors[owner % len(colors)]
        territory_text[tid] = str(armies)

    return render_state(territory_fills, territory_text, width=width)


# Find the map .svg. It's part of the package, so it shouldn't go missing ever.
def find_svg_path():
    p = Path(__file__).resolve().parent.parent / "assets" / "risk.map.svg"
    if not p.exists():
        raise FileNotFoundError(f"SVG not found at {p}")
    return p
