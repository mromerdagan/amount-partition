from collections import OrderedDict
import requests
from amount_partition.api import BudgetManagerApi
from amount_partition.client.budget_manager_client import BudgetManagerClient
from amount_partition.models import Target
from amount_partition.schemas import TargetResponse

class RemoteBudgetManagerClient(BudgetManagerClient):

    def __init__(self, rest_api_url: str, db_path: str):
        self.api_url = rest_api_url
        self.db_path = db_path
    
    def list_balances(self):
        response = requests.get(f"{self.api_url}/list_balances", params={"db_dir": self.db_path})
        response.raise_for_status()
        return response.json()

    def get_balances(self):
        response = requests.get(f"{self.api_url}/balances", params={"db_dir": self.db_path})
        response.raise_for_status()
        return OrderedDict({d["name"]: d["amount"] for d in response.json()})
    
    def get_targets(self):
        response = requests.get(f"{self.api_url}/targets", params={"db_dir": self.db_path})
        response.raise_for_status()
        return {
            target_name: Target.from_target_response(TargetResponse(**target_response))
            for target_name, target_response in response.json().items()
        }
    
    def get_recurring(self):
        raise NotImplementedError("Remote recurring payments not implemented yet")
    
    def deposit(self, amount: int, merge_with_credit: bool = False):
        data = {
            "amount": amount,
            "merge_with_credit": merge_with_credit
        }
        response = requests.post(f"{self.api_url}/deposit", json=data, params={"db_dir": self.db_path})
        response.raise_for_status()
        return response.json()
    
    def set_target(self, boxname: str, goal: int, due: str):
        data = {
            "boxname": boxname,
            "goal": goal,
            "due": due
        }
        response = requests.post(f"{self.api_url}/set_target", json=data, params={"db_dir": self.db_path})
        response.raise_for_status()
        return response.json()
    
    def withdraw(self, amount: int = 0):
        data = {"amount": amount}
        response = requests.post(f"{self.api_url}/withdraw", json=data, params={"db_dir": self.db_path})
        response.raise_for_status()
        return response.json()
    
    
    def add_to_balance(self, boxname: str, amount: int):
        data = {
            "boxname": boxname,
            "amount": amount
        }
        response = requests.post(f"{self.api_url}/add_to_balance", json=data, params={"db_dir": self.db_path})
        response.raise_for_status()
        return response.json()

    def new_box(self, boxname: str):
        data = {"boxname": boxname}
        response = requests.post(f"{self.api_url}/new_box", json=data, params={"db_dir": self.db_path})
        response.raise_for_status()
        return response.json()

    def remove_box(self, boxname: str):
        data = {"boxname": boxname}
        response = requests.post(f"{self.api_url}/remove_box", json=data, params={"db_dir": self.db_path})
        response.raise_for_status()
        return response.json()
    
    def transfer_between_balances(self, from_box: str, to_box: str, amount: int):
        data = {"from_box": from_box, "to_box": to_box, "amount": amount}
        response = requests.post(f"{self.api_url}/transfer_between_balances", json=data, params={"db_dir": self.db_path})
        response.raise_for_status()
        return response.json()

    def new_loan(self, amount: int, due: str):
        data = {
            "amount": amount,
            "due": due
        }
        response = requests.post(f"{self.api_url}/new_loan", json=data, params={"db_dir": self.db_path})
        response.raise_for_status()
        return response.json()

    def create_db(self, db_dir: str):
        data = {"location": db_dir}
        response = requests.post(f"{self.api_url}/create_db", json=data)
        response.raise_for_status()
        return response.json()
    
    def spend(self, boxname: str, amount: int = 0, use_credit: bool = False):
        data = {"boxname": boxname, "amount": amount, "use_credit": use_credit}
        response = requests.post(f"{self.api_url}/spend", json=data, params={"db_dir": self.db_path})
        response.raise_for_status()
        return response.json()