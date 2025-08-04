from fastapi import FastAPI, HTTPException, Body, UploadFile, File
import json
from typing import List
from amount_partition.api import BudgetManagerApi
from amount_partition.models import Target, PeriodicDeposit
from amount_partition.schemas import (
    BalanceResponse, TargetResponse, DepositRequest, SetTargetRequest, WithdrawRequest, SpendRequest, AddToBalanceRequest, TransferRequest, NewBoxRequest, RemoveBoxRequest, NewLoanRequest, CreateDbRequest
)

app = FastAPI()

def get_manager(db_dir: str) -> BudgetManagerApi:
    return BudgetManagerApi(db_dir)

@app.get("/balances", response_model=List[BalanceResponse])
def get_balances(db_dir: str = "."):
    manager = get_manager(db_dir)
    return [BalanceResponse(name=k, amount=v) for k, v in manager.balances.items()]

@app.get("/list_balances")
def list_balances(db_dir: str = "."):
    manager = get_manager(db_dir)
    return manager.list_balances()

@app.post("/deposit")
def deposit(req: DepositRequest, db_dir: str = "."):
    manager = get_manager(db_dir)
    manager.deposit(req.amount, merge_with_credit=req.merge_with_credit)
    manager.dump_data()
    return {"free": manager.balances["free"]}

@app.get("/targets", response_model=List[TargetResponse])
def get_targets(db_dir: str = "."):
    manager = get_manager(db_dir)
    targets = manager.get_targets()
    print(targets)
    return [TargetResponse(name=k, goal=v.goal, due=v.due.strftime("%Y-%m")) for k, v in targets.items()]

@app.post("/set_target")
def set_target(req: SetTargetRequest, db_dir: str = "."):
    manager = get_manager(db_dir)
    manager.set_target(req.boxname, req.goal, req.due)
    manager.dump_data()
    return {"status": "ok"}

@app.post("/withdraw")
def withdraw(req: WithdrawRequest, db_dir: str = "."):
    manager = get_manager(db_dir)
    manager.withdraw(req.amount)
    manager.dump_data()
    return {"free": manager.balances["free"]}

@app.post("/spend")
def spend(req: SpendRequest, db_dir: str = "."):
    manager = get_manager(db_dir)
    manager.spend(req.boxname, req.amount, req.use_credit)
    manager.dump_data()
    return {"balance": manager.balances.get(req.boxname, 0), "credit-spent": manager.balances.get("credit-spent", 0)}

@app.post("/add_to_balance")
def add_to_balance(req: AddToBalanceRequest, db_dir: str = "."):
    manager = get_manager(db_dir)
    manager.add_to_balance(req.boxname, req.amount)
    manager.dump_data()
    return {"balance": manager.balances[req.boxname], "free": manager.balances["free"]}

@app.post("/transfer_between_balances")
def transfer_between_balances(req: TransferRequest, db_dir: str = "."):
    manager = get_manager(db_dir)
    manager.transfer_between_balances(req.from_box, req.to_box, req.amount)
    manager.dump_data()
    return {"from_box": manager.balances[req.from_box], "to_box": manager.balances[req.to_box]}

@app.post("/new_box")
def new_box(req: NewBoxRequest, db_dir: str = "."):
    manager = get_manager(db_dir)
    manager.new_box(req.boxname)
    manager.dump_data()
    return {"status": "ok"}

@app.post("/remove_box")
def remove_box(req: RemoveBoxRequest, db_dir: str = "."):
    manager = get_manager(db_dir)
    manager.remove_box(req.boxname)
    manager.dump_data()
    return {"status": "ok"}

@app.post("/new_loan")
def new_loan(req: NewLoanRequest, db_dir: str = "."):
    manager = get_manager(db_dir)
    manager.new_loan(req.amount, req.due)
    manager.dump_data()
    return {"status": "ok"}

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
    manager = get_manager(db_dir)
    return manager.to_json()

# Import database from JSON
@app.post("/import_json")
async def import_json(db_dir: str = ".", file: UploadFile = File(...)):
    try:
        contents = await file.read()
        data = json.loads(contents)
        BudgetManagerApi.from_json(db_dir, data)
        return {"status": "imported", "db_dir": db_dir}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to import JSON: {e}")