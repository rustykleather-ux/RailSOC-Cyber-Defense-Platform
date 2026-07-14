from dataclasses import dataclass

@dataclass
class TrackBlock:
    id: int
    name: str
    start_mp: float
    end_mp: float
    occupied: bool = False
    occupied_by: str | None = None