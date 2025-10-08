import json
from collections import OrderedDict
from datetime import datetime
from amount_partition.api import BudgetManagerApi
from amount_partition.client.budget_manager_client import BudgetManagerClient

class LocalBudgetManagerClient(BudgetManagerClient):
    
    def __init__(self, db_dir: str = '.'):
        self.db_dir = db_dir
    
    def create_db(self, db_dir: str):
        BudgetManagerApi.create_db(db_dir)
        
    def list_balances(self):
        manager = BudgetManagerApi.from_storage(self.db_dir)
        return manager.list_balances()

    def get_balances(self):
        manager = BudgetManagerApi.from_storage(self.db_dir)
        return manager.balances
    
    def get_targets(self, curr_month_payed: bool = False):
        manager = BudgetManagerApi.from_storage(self.db_dir)
        return manager.get_targets()
    
    def get_recurring(self):
        manager = BudgetManagerApi.from_storage(self.db_dir)
        return manager.get_recurring()

    def deposit(self, amount: int, monthly: bool = False):
        manager = BudgetManagerApi.from_storage(self.db_dir)
        manager.deposit(amount, monthly=monthly)
        manager.dump_data(self.db_dir)
        return {"free": manager.balances['free']}

    def withdraw(self, amount: int = 0):
        manager = BudgetManagerApi.from_storage(self.db_dir)
        manager.withdraw(amount)
        manager.dump_data(self.db_dir)
        return {"free": manager.balances['free']}

    def add_to_balance(self, boxname: str, amount: int):
        manager = BudgetManagerApi.from_storage(self.db_dir)
        manager.add_to_balance(boxname, amount)
        manager.dump_data(self.db_dir)
        return {"balance": manager.balances[boxname], "free": manager.balances["free"]}

    def spend(self, boxname: str, amount: int = None, use_credit: bool = True):
        manager = BudgetManagerApi.from_storage(self.db_dir)
        if amount is None:
            manager.spend(boxname, use_credit=use_credit)
        else:
            manager.spend(boxname, amount, use_credit=use_credit)
        manager.dump_data(self.db_dir)
        return {"balance": manager.balances.get(boxname, 0), "credit-spent": manager.balances.get("credit-spent", 0)}
    
    def transfer_between_balances(self, from_box: str, to_box: str, amount: int):
        manager = BudgetManagerApi.from_storage(self.db_dir)
        manager.transfer_between_balances(from_box, to_box, amount)
        manager.dump_data(self.db_dir)
        return {"from_box": manager.balances[from_box], "to_box": manager.balances[to_box]}
    
    def new_box(self, boxname: str):
        manager = BudgetManagerApi.from_storage(self.db_dir)
        manager.new_box(boxname)
        manager.dump_data(self.db_dir)

    def remove_box(self, boxname: str):
        manager = BudgetManagerApi.from_storage(self.db_dir)
        manager.remove_box(boxname)
        manager.dump_data(self.db_dir)

    def set_target(self, boxname: str, goal: int, due: str):
        manager = BudgetManagerApi.from_storage(self.db_dir)
        manager.set_target(boxname, goal, due)
        manager.dump_data(self.db_dir)
    
    def remove_target(self, boxname: str):
        manager = BudgetManagerApi.from_storage(self.db_dir)
        manager.remove_target(boxname)
        manager.dump_data(self.db_dir)
    
    def set_recurring(self, boxname: str, monthly: int, target: int):
        manager = BudgetManagerApi.from_storage(self.db_dir)
        manager.set_recurring(boxname, monthly, target)
        manager.dump_data(self.db_dir)
    
    def remove_recurring(self, boxname: str):
        manager = BudgetManagerApi.from_storage(self.db_dir)
        manager.remove_recurring(boxname)
        manager.dump_data(self.db_dir)

    def new_loan(self, amount: int, due: str):
        manager = BudgetManagerApi.from_storage(self.db_dir)
        manager.new_loan(amount, due)
        manager.dump_data(self.db_dir)
    
    def export_json(self):
        manager = BudgetManagerApi.from_storage(self.db_dir)
        data = manager.to_json()
        return data

    def import_json(self, data: dict):
        manager = BudgetManagerApi.from_json(data)
        manager.dump_data(self.db_dir)

    def plan_deposits(self, skip: str, is_monthly: bool, amount_to_use: int):
        manager = BudgetManagerApi.from_storage(self.db_dir)
        return manager.plan_deposits(skip, is_monthly, amount_to_use)

    def plan_and_apply(self, skip: str, is_monthly: bool, amount_to_use: int):
        manager = BudgetManagerApi.from_storage(self.db_dir)
        data = manager.plan_and_apply(skip, is_monthly, amount_to_use)
        manager.dump_data(self.db_dir)
        return data

if __name__ == "__main__":
    manager = LocalBudgetManagerClient("/tmp/partition-bp")
    manager.new_box("t4")
