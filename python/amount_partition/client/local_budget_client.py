from amount_partition.api import BudgetManagerApi
from amount_partition.client.budget_manager_client import BudgetManagerClient

class LocalBudgetManagerClient(BudgetManagerClient):
    
    def __init__(self, db_dir: str = '.'):
        self.manager = BudgetManagerApi(db_dir)
        
    def list_balances(self):
        return self.manager.list_balances()

    def get_balances(self):
        return self.manager.balances

    def deposit(self, amount: int, merge_with_credit: bool = False):
        self.manager.deposit(amount, merge_with_credit=merge_with_credit)
        self.manager.dump_data()

    def withdraw(self, amount: int = 0):
        self.manager.withdraw(amount)
        self.manager.dump_data()

    def spend(self, boxname: str, amount: int = None, use_credit: bool = False):
        if amount is None:
            self.manager.spend(boxname, use_credit=use_credit)
        else:
            self.manager.spend(boxname, amount, use_credit=use_credit)
        self.manager.dump_data()

    def add_to_balance(self, boxname: str, amount: int):
        self.manager.add_to_balance(boxname, amount)
        self.manager.dump_data()

    def set_target(self, boxname: str, goal: int, due: str):
        self.manager.set_target(boxname, goal, due)
        self.manager.dump_data()

    def new_box(self, boxname: str):
        self.manager.new_box(boxname)
        self.manager.dump_data()

    def remove_box(self, boxname: str):
        self.manager.remove_box(boxname)
        self.manager.dump_data()

    def new_loan(self, amount: int, due: str):
        self.manager.new_loan(amount, due)
        self.manager.dump_data()

    def create_db(self, db_dir: str):
        BudgetManagerApi.create_db(db_dir)
    
