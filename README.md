# Risk
Risk is a strategy board game for 2-6 players invented in 1957 by French film
director Albert Lamorisse as La *Conquête du Monde*[^risk-wiki]. It was
subsequently sold to Parker Brothers in America and has become one of the most
successful board games of all time. Game rules are widely available and
standardized[^risk-rules].
# General GamePlay Description
A Risk game is played on a board arranged like a world map with 42 territories.
![Risk map image](./img/risk-map.png)[^risk-strategy-mit]
It is frequently cited[^risk-strategy-mit] that a Risk game map is comprised of a
graph with nodes and edges, making it highly amenable to AI agent gameplay.
![Risk graph image](./img/risk-graph.png)[^risk-strategy-mit]
## Game Sequence
Gameplay in Risk is not overly complex, but is comprised of several phases each of
which can be seen as a separate game in itself.
* **Setup** An initial setup phase in which players iteratively choose their
territories. During this phase players vie for strategic positions offering later
advantages.
* **Player Turns** Players now take turns doing the following which comprise their
turn:
* **Card Play** A player can turn in cards for bonus armies depending on their
hand.
* **Reinforce** A player is awarded armies and place them strategically on the
board. Armies are awarded according to the number of territories players hold.
Bonuses are awarded if a player holds an entire continent. Players here vie to
optimize placement according to their desire to attack or defend.
* **Attack** Players can now iteratively attack territories which border their
own. Battles are conduced via die rolls and specific rules. Attackers can attack
any number of times and call off an attack at any time if things are not going
favorably.
* **Fortify** Players may end their turn by moving as many armies as they like
from *one* territory to an adjacent territory.
## Victory Conditions
A player is eliminated if they have 0 territories.
Typically when one player remains, that player is the victor. There are variants,
but this is the typical "world conquest" mode.
# Proposal
We propose implementing a somewhat simplified version of Risk in python, and then
implement various AI agents to play the game. Strategies and problem solving
approaches will be tried out in the agents, demonstrating several approaches to
solving the problems presented by the game and optimizing victory conditions.
## Game Simplifications
As Risk can be a fairly complex game we'd suggest the following practical
simplifications to make our implementation manageable and focused on AI Agent
implementation and not the idiosyncrasies of the game:
* **Eliminate the Card Game** which is nearly a game in itself. reinforcements
would be determined entirely by territories held and continent bonuses. This
removes some reward dynamics and reduces state branching, allowing us to focus on
player strategic positioning and combat decision-making.
* **Eliminate the Setup Phase** As this is practically a game in itself, our
simulations would probably improve if we always proceed from some known game
configurations or even random (or random "balanced") placement.
## AI Task Environment Properties
| Property | Classification | Notes |
|----------|----------------|------|
| **Observability** | Fully observable | All territory ownership and army counts
are visible to all players |
| **Agents** | Multi-agent (adversarial) | Multiple competing AI agents |
| **Determinism** | Stochastic | Dice rolls introduce probabilistic outcomes in
combat |
| **Episodic vs Sequential** | Sequential | Actions affect future states and long-
term outcomes |
| **Static vs Dynamic** | Static (turn-based) | Environment does not change while
an agent is deciding |
| **Discrete vs Continuous** | Discrete | Finite territories, armies, and actions |
| **Environment Knowledge** | Known | Rules and transition probabilities are known
|
To summarize: we propose a game which will be modeled as a fully observable,
stochastic, multi-agent, sequential decision process over a graph-structured state
space, where agents act to maximize their probability of eventual victory.
## Game Definition
### Initial State
The initial state is simply the full board configuration at the moment the first
player begins their first turn.
Since we might not include the setup phase as part of agent decision-making, this
state already includes:
* Every territory assigned to a player
* An initial number of armies placed on each territory
* A defined player turn order
* The game ready to begin at the Reinforcement phase
In other words, the game starts from a complete, playable board, not from an empty
map.
We may generate this starting board randomly (while keeping things balanced) or
choose from a small set of predefined fair configurations. The goal is to avoid
setup complexity while ensuring no player has an unfair advantage at the start.
### State Space
The state space is the set of all possible board situations the game could ever be
in.
To describe a state, you need to know:
* Who owns each territory
* How many armies are on each territory
* Whose turn it is
* Which phase of the turn we’re in (reinforce, attack, or fortify)
If any one of those things changes, the game is in a different state.
Please note that Because there are very many ways armies can be distributed across
42 territories, the number of possible states is enormous. This is one reason why
simple brute-force planning won't be practical. We will instead need some other AI
agent heuristics.
# Action Space
The action space is everything a player is allowed to do on their turn.
Because Risk has several game phases, the actions available depend on what phase
we're in:
* Reinforcement phase: The player decides where to place their new armies among the
territories they control.
* Attack phase: The player can choose to attack neighboring enemy territories. They
decide which territory to attack from, which one to attack, and whether to keep
attacking or stop.
* Fortify phase: At the end of the turn, the player can move armies from one of
their territories to another to improve their defensive position.
The action taken by an agent will therefore depend on both the current board
configuration and the current phase. Presumably, a correct action can be generated
from that unique set of information.
# Transition Model
The transition model describes how the game state changes after a player takes an
action.
Some actions change the board in a predictable way:
* Placing reinforcement armies
* Moving armies during fortify
Other actions are probabilistic:
* Attacks are resolved with dice rolls, so the outcome isn’t guaranteed. The same
attack could succeed or fail depending on chance.
Combat in Risk introduces randomness. That makes the environment partly predictable
and partly uncertain.
# Reward
The reward defines what the AI agent is trying to achieve.
At the highest level, the goal is simply "win the game". This suggests rewards
like:
* A reward for having 0 opponents ("winning")
* “intermediate” rewards to help guide decision-making, like:
* Gaining or losing territories
* Controlling continents
* Eliminating an opponent
# Game Deliverables and Process
The game files should be made available to reviewers as a unified `.zip` archive.
The `.zip` archive would contain:
* **A Readme** containing simple instructions as to how to build and run the game.
* **A Dockerfile** allowing reviewers to build and run the container, and which
will almost 100% guarantee they run into no build/run issues.
* **The python code for the game**, separated into `.py` files as necessary.
* **Optional Jupyter Notebooks** Which can invoke the local python game code to do
analyses/graphs for various game configurations. For example: do an analysis of
1000 games played between two different AI agents, and graph results.
* **Additional Dashboard HTML templates/assets** to support the required dashboard.
This would allow reviewers to set up gameplay parameters via a browser window,
start games and view them as they progress. Additional debug information may also
be presented.

## Build and Run

### Build the Docker Image

Required since we're not currently pulling a pre-built image off a server. 

```bash
docker build -t risk .
```

In the future we might provide a pre-built image to make running easier if we're inclined.

### Run the Docker Container (default entry point)

Runs `src/main.py`. Use `--rm` so the container is removed when it exits:

The default entry point is specified in the `Dockerfile`. Change as needed.

```bash
docker run --rm risk
```

### Edit/Run Local Files Mounted to the Container (run without rebuilding container)

If we mount the local source directories into the Docker container we can edit and run them without having to rebuild the container. If we start `bash` in the container we can then iteratively edit/run/edit for faster development if you want to do that.

```bash
docker run --rm -it -v "$(pwd):/app" -w /app risk bash
```

### To Run Specific Python Files (not necessarily the default)

With no extra arguments:

```bash
docker run --rm risk python src/your_script.py
```

With optional arguments passed to your script:

```bash
docker run --rm risk python src/your_script.py --option value
```

### Run the example Jupyter notebook

Start Jupyter in the container and expose port 8888 (`--rm` removes the container when you stop it):

```bash
docker run --rm -p 127.0.0.1:8888:8888 risk \
    jupyter notebook --ip=0.0.0.0 --allow-root \
    --NotebookApp.token='' --NotebookApp.password=''
```

Then:

1. Open a browser and go to **http://localhost:8888**. You should something like:

![jupyter file tree](./img/jupyter-tree.png)

2. In the file browser, open **notebooks** → **example.ipynb** (or whatever you file wish), and run the cells as normal.

![jupyter example](./img/jupyter-example.png)

The command above circumvents the use of tokens/password for simplicity. If you want to use them, then remove those arguments and when for a token, copy the `?token=...` URL from the terminal output and use that, or paste the token into the login field.


# Citations and Other Sources
[^risk-wiki]: https://en.wikipedia.org/wiki/Risk_(game)
[^risk-rules]: https://www.hasbro.com/common/instruct/risk.pdf
[^risk-strategy-mit]: https://web.mit.edu/sp.268/www/risk.pdf
[^risk-math](https://www.businessinsider.com/how-to-use-math-to-win-at-the-board-
game-risk-2013-7)
