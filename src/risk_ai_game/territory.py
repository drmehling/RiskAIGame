from dataclasses import dataclass

@dataclass
class Territory:
    name: str
    continent: str
    neighbors: list[str]
    owner: int | None = None
    armies: int = 0
