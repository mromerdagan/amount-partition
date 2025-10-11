from dataclasses import dataclass
from datetime import datetime
from amount_partition.schemas import TargetResponse, PeriodicDepositResponse, BalanceResponse, RegularBalanceResponse, CreditBalanceResponse, FreeBalanceResponse, VirtualBalanceResponse, InstalmentBalanceResponse

class Balance:
    type_: str = "regular"
    schema_cls = RegularBalanceResponse
    
    def __init__(self, amount: int):
        self.amount = amount

    def __eq__(self, other):
        if not isinstance(other, Balance):
            return NotImplemented
        return self.amount == other.amount and self.type_ == other.type_

    def to_json(self) -> dict:
        return {
            "amount": self.amount,
            "type": self.type_,
        }
    
    def as_list(self) -> list:
        return [self.amount, self.type_]
    
    def to_balance_response(self):
        payload = {"type": self.type_, "amount": self.amount}
        if hasattr(self, "monthly_payment"):
            payload["monthly_payment"] = self.monthly_payment
        return self.schema_cls(**payload)

class CreditBalance(Balance):
    type_: str = "credit"
    schema_cls = CreditBalanceResponse

class FreeBalance(Balance):
    type_: str = "free"
    schema_cls = FreeBalanceResponse

class VirtualBalance(Balance):
    type_: str = "virtual"
    schema_cls = VirtualBalanceResponse

class InstalmentBalance(Balance):
    type_: str = "instalment"
    schema_cls = InstalmentBalanceResponse
    
    def __init__(self, amount: int, monthly_payment: int):
        super().__init__(amount)
        self.monthly_payment = monthly_payment

    def __eq__(self, other):
        if not isinstance(other, InstalmentBalance):
            return NotImplemented
        return super().__eq__(other) and self.monthly_payment == other.monthly_payment
    
    @property
    def exhausted(self) -> bool:
        return self.amount == 0

    def pay_instalment(self) -> int:
        """Pay the monthly instalment from the balance. Returns the amount paid."""
        if self.amount >= self.monthly_payment:
            self.amount -= self.monthly_payment
            return self.monthly_payment
        else:
            paid = self.amount
            self.amount = 0
            return paid
    
    def to_json(self) -> dict:
        data = super().to_json()
        data["monthly_payment"] = self.monthly_payment
        return data
    
    def as_list(self) -> list:
        return [self.amount, self.type_, self.monthly_payment]
    
    def to_balance_response(self):
        payload = {"type": self.type_, "amount": self.amount, "monthly_payment": self.monthly_payment}
        return self.schema_cls(**payload)

class BalanceFactory:
    @staticmethod
    def create_balance(amount: int, type_: str, *args) -> Balance:
        if type_ == "regular":
            return Balance(amount)
        elif type_ == "credit":
            return CreditBalance(amount)
        elif type_ == "free":
            return FreeBalance(amount)
        elif type_ == "virtual":
            return VirtualBalance(amount)
        elif type_ == "instalment":
            try:
                monthly_payment = int(args[0])
            except IndexError:
                raise ValueError(f"Missing monthly_payment for instalment balance")
            except ValueError:
                raise ValueError(f"Invalid monthly_payment for instalment balance: {args[0]!r}")
            return InstalmentBalance(amount, monthly_payment)
        else:
            raise ValueError(f"Unknown balance type: {type_}")
    
    @staticmethod
    def from_json(data: dict) -> Balance:
        type_ = data.get("type", "regular")
        if type_ == "regular":
            return Balance(amount=data['amount'])
        elif type_ == "credit":
            return CreditBalance(amount=data['amount'])
        elif type_ == "free":
            return FreeBalance(amount=data['amount'])
        elif type_ == "instalment":
            return InstalmentBalance(amount=data['amount'], monthly_payment=data.get('monthly_payment', 0))
        elif type_ == "virtual":
            return VirtualBalance(amount=data['amount'])
        else:
            raise ValueError(f"Unknown balance type in JSON: {type_}")

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
    # target = Target(goal=1000, due=datetime(2023, 12, 31))
    # print(target.as_dict())
    balance = InstalmentBalance(amount=5000, monthly_payment=450)
    print(balance.to_balance_response())
    print(balance.to_json())
    balance = BalanceFactory.from_json(balance.to_json())
    print(balance.to_balance_response())
    print(balance.to_json())