from dataclasses import dataclass
from datetime import datetime

@dataclass
class Target:
    goal: int
    due: datetime

@dataclass
class PeriodicDeposit:
    amount: int
    target: int
