from dataclasses import dataclass
from datetime import datetime

@dataclass
class Target:
    goal: int
    due: datetime
    
    def months_left(self, curr_month_payed: bool = False) -> int:
        today_ = datetime.today()
        months = (self.due.year - today_.year) * 12 + (self.due.month - today_.month)
        return max(0, months - (1 if curr_month_payed else 0))

    def monthly_payment(self, balance: float, curr_month_payed: bool = False) -> float:
        months = self.months_left(curr_month_payed)
        if months == 0:
            return 0.0
        return (self.goal - balance) / months

@dataclass
class PeriodicDeposit:
    amount: int
    target: int
