from pydantic import BaseModel
from typing import List, Dict, Tuple


class Order(BaseModel):
    id: int
    location: Tuple[float, float]
    deadline: int
    delivered: bool = False


class Vehicle(BaseModel):
    id: str
    location: Tuple[float, float]
    capacity: int


class Observation(BaseModel):
    time: int
    orders: List[Order]
    vehicles: List[Vehicle]


class Action(BaseModel):
    assignments: Dict[str, List[int]]  # vehicle_id → order_ids