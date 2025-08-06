from dataclasses import dataclass
from datetime import datetime
from amount_partition.schemas import TargetResponse, PeriodicDepositResponse

@dataclass
class Target:
    goal: int
    due: datetime
    
    def to_target_response(self, name:str) -> 'TargetResponse':
        return TargetResponse(
            name=name,
            goal=self.goal,
            due=self.due.strftime("%Y-%m"),
        )
    
    @classmethod
    def from_target_response(cls, target_response: TargetResponse) -> 'Target':
        return Target(
            goal=target_response.goal,
            due=datetime.strptime(target_response.due, "%Y-%m")
        )
    
    def to_json(self) -> dict:
        return {
            "goal": self.goal,
            "due": self.due.strftime("%Y-%m"),
        }
    
    @classmethod
    def from_json(cls, data: dict) -> 'Target':
        return cls(
            goal=data['goal'],
            due=datetime.strptime(data['due'], "%Y-%m")
        )
    
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
    
    def to_periodic_deposit_response(self, name: str) -> PeriodicDepositResponse:
        return PeriodicDepositResponse(
            name=name,
            amount=self.amount,
            target=self.target
        )
    
    @classmethod
    def from_periodic_deposit_response(cls, periodic_response: PeriodicDepositResponse) -> 'PeriodicDeposit':
        return cls(
            amount=periodic_response.amount,
            target=periodic_response.target
        )
    
    def to_json(self) -> dict:
        return {
            "amount": self.amount,
            "target": self.target
        }
    
    @classmethod
    def from_json(cls, data: dict) -> 'PeriodicDeposit':
        return cls(
            amount=data['amount'],
            target=data['target']
        )

if __name__ == "__main__":
    target = Target(goal=1000, due=datetime(2023, 12, 31))
    print(target.as_dict())