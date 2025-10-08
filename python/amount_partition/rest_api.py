from fastapi import FastAPI, HTTPException, Body, UploadFile, File, Query
import json
from typing import List, Dict
from amount_partition.api import BudgetManagerApi
from amount_partition.models import Balance, Target, PeriodicDeposit
from amount_partition.schemas import (
    BalanceResponse, NewInstalmentRequest, PlanAndApplyRequest, PlanDepositsRequest, TargetResponse, PeriodicDepositResponse, DepositRequest, SetTargetRequest, RemoveTargetRequest, SetRecurringRequest, RemoveRecurringRequest, WithdrawRequest, SpendRequest, AddToBalanceRequest, TransferRequest, NewBoxRequest, RemoveBoxRequest, NewLoanRequest, CreateDbRequest
)

app = FastAPI()

def get_manager(db_dir: str) -> BudgetManagerApi:
    return BudgetManagerApi.from_storage(db_dir)

@app.get("/list_balances")
def list_balances(db_dir: str = "."):
    try:
        manager = get_manager(db_dir)
        return manager.list_balances()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/balances", response_model=Dict[str, BalanceResponse])
def get_balances(db_dir: str = "."):
    """ Return balances as a dictionary of BalanceResponse """
    try:
        manager = get_manager(db_dir)
        balances: dict[str, Balance] = manager.balances
        return {name: balance.to_balance_response() for name, balance in balances.items()}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/targets", response_model=Dict[str, TargetResponse])
def get_targets(db_dir: str = "."):
    """ Return a dictionary of TargetResponse for each target """
    try:
        manager = get_manager(db_dir)
        targets: dict[str, Target] = manager.get_targets()
        return {
            name: target.to_target_response(name=name) 
            for name, target in targets.items()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/recurring", response_model=Dict[str, PeriodicDepositResponse])
def get_recurring(db_dir: str = "."):
    """ Return a dictionary of PeriodicDeposit for each recurring deposit """
    try:
        manager = get_manager(db_dir)
        recurring: dict[str, PeriodicDeposit] = manager.get_recurring()
        return {
            name: periodic.to_periodic_deposit_response(name=name) 
            for name, periodic in recurring.items()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/deposit")
def deposit(req: DepositRequest, db_dir: str = "."):
    try:
        manager = get_manager(db_dir)
        manager.deposit(req.amount, monthly=req.monthly)
        manager.dump_data(db_dir)
        return {"free": manager.balances["free"]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/withdraw")
def withdraw(req: WithdrawRequest, db_dir: str = "."):
    try:
        manager = get_manager(db_dir)
        manager.withdraw(req.amount)
        manager.dump_data(db_dir)
        return {"free": manager.balances["free"]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/add_to_balance")
def add_to_balance(req: AddToBalanceRequest, db_dir: str = "."):
    try:
        manager = get_manager(db_dir)
        manager.add_to_balance(req.boxname, req.amount)
        manager.dump_data(db_dir)
        return {"balance": manager.balances[req.boxname], "free": manager.balances["free"]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/spend")
def spend(req: SpendRequest, db_dir: str = "."):
    try:
        manager = get_manager(db_dir)
        manager.spend(req.boxname, req.amount, req.use_credit)
        manager.dump_data(db_dir)
        return {"balance": manager.balances.get(req.boxname, 0), "credit-spent": manager.balances.get("credit-spent", 0)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/transfer_between_balances")
def transfer_between_balances(req: TransferRequest, db_dir: str = "."):
    try:
        manager = get_manager(db_dir)
        manager.transfer_between_balances(req.from_box, req.to_box, req.amount)
        manager.dump_data(db_dir)
        return {"from_box": manager.balances[req.from_box], "to_box": manager.balances[req.to_box]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/new_box")
def new_box(req: NewBoxRequest, db_dir: str = "."):
    manager = get_manager(db_dir)
    try:
        manager.new_box(req.boxname)
        manager.dump_data(db_dir)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "ok"}

@app.post("/remove_box")
def remove_box(req: RemoveBoxRequest, db_dir: str = "."):
    try:
        manager = get_manager(db_dir)
        manager.remove_box(req.boxname)
        manager.dump_data(db_dir)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "ok"}

@app.post("/set_target")
def set_target(req: SetTargetRequest, db_dir: str = "."):
    try:
        manager = get_manager(db_dir)
        manager.set_target(req.boxname, req.goal, req.due)
        manager.dump_data(db_dir)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/remove_target")
def remove_target(req: RemoveTargetRequest, db_dir: str = "."):
    try:
        manager = get_manager(db_dir)
        manager.remove_target(req.name)
        manager.dump_data(db_dir)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/set_recurring")
def set_recurring(req: SetRecurringRequest, db_dir: str = "."):
    """ Set a recurring deposit for a specific balance. """
    try:
        manager = get_manager(db_dir)
        manager.set_recurring(req.boxname, req.monthly, req.target)
        manager.dump_data(db_dir)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/remove_recurring")
def remove_recurring(req: RemoveRecurringRequest, db_dir: str = "."):
    """ Remove a recurring deposit for a specific balance. """
    try:
        manager = get_manager(db_dir)
        manager.remove_recurring(req.boxname)
        manager.dump_data(db_dir)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/new_loan")
def new_loan(req: NewLoanRequest, db_dir: str = "."):
    try:
        manager = get_manager(db_dir)
        manager.new_loan(req.amount, req.due)
        manager.dump_data(db_dir)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/create_db")
def create_db(req: CreateDbRequest = Body(...)):
    try:
        BudgetManagerApi.create_db(req.location)
    except FileExistsError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create DB: {e}")
    return {"status": "created", "location": req.location}

# Export database as JSON
@app.get("/export_json")
def export_json(db_dir: str = "."):
    try:
        manager = get_manager(db_dir)
        return manager.to_json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Import database from JSON
@app.post("/import_json")
async def import_json(db_dir: str = ".", data: dict = Body(...)):
    try:
        manager = BudgetManagerApi.from_json(data)
        manager.dump_data(db_dir)
        return {"status": "imported", "db_dir": db_dir}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to import JSON: {e}")

@app.post("/plan_deposits")
def plan_deposits(req: PlanDepositsRequest = Body(...), db_dir: str = "."):
    """
    Compute a deposits plan and return it (no state changes).
    Response shape:
    {
      "status": "ok",
      "plan": { "<box>": <amount>, ... },
      "total": <sum of amounts>
    }
    """
    try:
        manager = get_manager(db_dir)
        plan = manager.plan_deposits(
            skip=req.skip,
            is_monthly=req.is_monthly,
            amount_to_use=req.amount_to_use,
        )
        return {"status": "ok", "plan": plan, "total": sum(plan.values())}
    except Exception as e:
        # Keep consistent with your other endpoints that treat manager errors as 400
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/plan_and_apply")
def plan_and_apply(req: PlanAndApplyRequest = Body(...), db_dir: str = "."):
    """
    Compute a deposits plan, apply it to balances, persist, and return the applied plan.
    Response shape:
    {
      "status": "applied",
      "plan": { "<box>": <amount>, ... },
      "total": <sum of amounts>
    }
    """
    try:
        manager = get_manager(db_dir)
        plan = manager.plan_and_apply(
            is_monthly=req.is_monthly,
            skip=req.skip,
            amount_to_use=req.amount_to_use,
        )
        manager.dump_data(db_dir)
        return {"status": "applied", "plan": plan, "total": sum(plan.values())}
    except ValueError as e:
        # e.g., insufficient 'free' funds, stale state, etc.
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to plan/apply deposits: {e}")

@app.post("/new_instalment")
def new_instalment(req: NewInstalmentRequest = Body(...), db_dir: str = "."):
    try:
        manager = get_manager(db_dir)
        manager.new_instalment(req.instalment_name, req.from_balance, req.num_instalments, req.monthly_payment)
        manager.dump_data(db_dir)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))



