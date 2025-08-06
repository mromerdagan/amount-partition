from pydantic import BaseModel
from typing import Optional

class BalanceResponse(BaseModel):
    name: str
    amount: int

class TargetResponse(BaseModel):
    name: str
    goal: int
    due: str

class PeriodicDepositResponse(BaseModel):
    name: str
    amount: int
    target: int

class DepositRequest(BaseModel):
    amount: int
    merge_with_credit: Optional[bool] = True

class SetTargetRequest(BaseModel):
    boxname: str
    goal: int
    due: str  # YYYY-MM

class RemoveTargetRequest(BaseModel):
    name: str

class SetRecurringRequest(BaseModel):
    boxname: str
    monthly: int
    target: int

class RemoveRecurringRequest(BaseModel):
    boxname: str

class WithdrawRequest(BaseModel):
    amount: int = 0

class SpendRequest(BaseModel):
    boxname: str
    amount: int = 0
    use_credit: Optional[bool] = False

class AddToBalanceRequest(BaseModel):
    boxname: str
    amount: int

class TransferRequest(BaseModel):
    from_box: str
    to_box: str
    amount: int

class NewBoxRequest(BaseModel):
    boxname: str

class RemoveBoxRequest(BaseModel):
    boxname: str

class NewLoanRequest(BaseModel):
    amount: int
    due: str

class CreateDbRequest(BaseModel):
    location: str