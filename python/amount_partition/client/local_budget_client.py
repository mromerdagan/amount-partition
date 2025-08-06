from amount_partition.api import BudgetManagerApi
from amount_partition.client.budget_manager_client import BudgetManagerClient

class LocalBudgetManagerClient(BudgetManagerClient):
    
    def __init__(self, db_dir: str = '.'):
        self.manager = BudgetManagerApi(db_dir)
        
    def list_balances(self):
        return self.manager.list_balances()

    def get_balances(self):
        return self.manager.balances
    
    def get_targets(self, curr_month_payed: bool = False):
        return self.manager.get_targets()
    
    def get_recurring(self):
        return self.manager.get_recurring()

    def deposit(self, amount: int, merge_with_credit: bool = False):
        self.manager.deposit(amount, merge_with_credit=merge_with_credit)
        self.manager.dump_data()
        return {"free": self.manager.balances['free']}

    def withdraw(self, amount: int = 0):
        self.manager.withdraw(amount)
        self.manager.dump_data()
        return {"free": self.manager.balances['free']}

    def add_to_balance(self, boxname: str, amount: int):
        self.manager.add_to_balance(boxname, amount)
        self.manager.dump_data()
        return {"balance": self.manager.balances[boxname], "free": self.manager.balances["free"]}

    def spend(self, boxname: str, amount: int = None, use_credit: bool = False):
        if amount is None:
            self.manager.spend(boxname, use_credit=use_credit)
        else:
            self.manager.spend(boxname, amount, use_credit=use_credit)
        self.manager.dump_data()
        return {"balance": self.manager.balances.get(boxname, 0), "credit-spent": self.manager.balances.get("credit-spent", 0)}
    
    def transfer_between_balances(self, from_box: str, to_box: str, amount: int):
        self.manager.transfer_between_balances(from_box, to_box, amount)
        self.manager.dump_data()
        return {"from_box": self.manager.balances[from_box], "to_box": self.manager.balances[to_box]}
    
    def new_box(self, boxname: str):
        self.manager.new_box(boxname)
        self.manager.dump_data()

    def remove_box(self, boxname: str):
        self.manager.remove_box(boxname)
        self.manager.dump_data()

    def set_target(self, boxname: str, goal: int, due: str):
        self.manager.set_target(boxname, goal, due)
        self.manager.dump_data()
    
    def remove_target(self, boxname: str):
        self.manager.remove_target(boxname)
        self.manager.dump_data()
    
    def set_recurring(self, boxname: str, monthly: int, target: int):
        self.manager.set_recurring(boxname, monthly, target)
        self.manager.dump_data()
    
    def remove_recurring(self, boxname: str):
        self.manager.remove_recurring(boxname)
        self.manager.dump_data()

    def new_loan(self, amount: int, due: str):
        self.manager.new_loan(amount, due)
        self.manager.dump_data()

    def create_db(self, db_dir: str):
        BudgetManagerApi.create_db(db_dir)
    
    
    # Stubs for missing parent methods
    def export_json(self):
        raise NotImplementedError("export_json is not implemented in LocalBudgetManagerClient.")

    def import_json(self, data):
        raise NotImplementedError("import_json is not implemented in LocalBudgetManagerClient.")

    def to_json(self):
        raise NotImplementedError("to_json is not implemented in LocalBudgetManagerClient.")

    def from_json(self, db_dir, data):
        raise NotImplementedError("from_json is not implemented in LocalBudgetManagerClient.")

    def remove_target(self, boxname: str):
        raise NotImplementedError("remove_target is not implemented in LocalBudgetManagerClient.")
