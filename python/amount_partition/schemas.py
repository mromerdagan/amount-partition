from pydantic import BaseModel, Field
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
    use_credit: bool = True

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
    

class PlanDepositsRequest(BaseModel):
    skip: str = Field(default="", description="Comma-separated balance names to skip")
    is_monthly: bool = Field(default=True, description="True for regular monthly deposit; False for additional deposits")
    amount_to_use: int = Field(default=0, ge=0, description="Total amount to linearly scale the plan to (0 = no scaling)")

class PlanAndApplyRequest(PlanDepositsRequest):
    pass