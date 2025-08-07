from collections import OrderedDict
import json
import requests
from amount_partition.api import BudgetManagerApi
from amount_partition.client.budget_manager_client import BudgetManagerClient
from amount_partition.models import Target, PeriodicDeposit
from amount_partition.schemas import TargetResponse, PeriodicDepositResponse

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
        return OrderedDict({balance_name: d["amount"] for balance_name, d in response.json().items()})
    
    def get_targets(self):
        response = requests.get(f"{self.api_url}/targets", params={"db_dir": self.db_path})
        response.raise_for_status()
        return {
            target_name: Target.from_target_response(TargetResponse(**target_response))
            for target_name, target_response in response.json().items()
        }
    
    def get_recurring(self):
        response = requests.get(f"{self.api_url}/recurring", params={"db_dir": self.db_path})
        response.raise_for_status()
        return {
            name: PeriodicDeposit.from_periodic_deposit_response(PeriodicDepositResponse(**periodic_response))
            for name, periodic_response in response.json().items()
        }
    
    def deposit(self, amount: int, merge_with_credit: bool = False):
        data = {
            "amount": amount,
            "merge_with_credit": merge_with_credit
        }
        response = requests.post(f"{self.api_url}/deposit", json=data, params={"db_dir": self.db_path})
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
    
    def spend(self, boxname: str, amount: int = 0, use_credit: bool = False):
        data = {"boxname": boxname, "amount": amount, "use_credit": use_credit}
        response = requests.post(f"{self.api_url}/spend", json=data, params={"db_dir": self.db_path})
        response.raise_for_status()
        return response.json()
    
    def transfer_between_balances(self, from_box: str, to_box: str, amount: int):
        data = {"from_box": from_box, "to_box": to_box, "amount": amount}
        response = requests.post(f"{self.api_url}/transfer_between_balances", json=data, params={"db_dir": self.db_path})
        response.raise_for_status()
        return response.json()

    def new_box(self, boxname: str):
        data = {"boxname": boxname}
        response = requests.post(f"{self.api_url}/new_box", json=data, params={"db_dir": self.db_path})
        
        if response.status_code != 200:
            try:
                error_message = response.json().get("detail", "Unknown error")
            except Exception:
                error_message = response.text
            raise RuntimeError(error_message)
        
        return response.json()

    def remove_box(self, boxname: str):
        data = {"boxname": boxname}
        response = requests.post(f"{self.api_url}/remove_box", json=data, params={"db_dir": self.db_path})
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
    
    def remove_target(self, name: str):
        data = {"name": name}
        response = requests.post(f"{self.api_url}/remove_target", json=data, params={"db_dir": self.db_path})
        response.raise_for_status()
        return response.json()
    
    def set_recurring(self, boxname: str, monthly: int, target: int):
        data = {
            "boxname": boxname,
            "monthly": monthly,
            "target": target
        }
        response = requests.post(f"{self.api_url}/set_recurring", json=data, params={"db_dir": self.db_path})
        response.raise_for_status()
        return response.json()
    
    def remove_recurring(self, boxname: str):
        data = {"boxname": boxname}
        response = requests.post(f"{self.api_url}/remove_recurring", json=data, params={"db_dir": self.db_path})
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
    
    def export_json(self):
        params = {"db_dir": self.db_path}
        response = requests.get(f"{self.api_url}/export_json", params=params)
        response.raise_for_status()
        return response.json()
        return {"status": "exported", "file": to_file}

    def import_json(self, data: dict):
        response = requests.post(f"{self.api_url}/import_json", json=data, params={"db_dir": self.db_path})
        response.raise_for_status()
        return response.json()
    
if __name__ == "__main__":
    import json
    api_url = "http://127.0.0.1:8002"
    db_path = "/tmp/partition-bp/"
    client = RemoteBudgetManagerClient(api_url, db_path)
    json_file = "/tmp/export.json"
    with open(json_file, 'r') as f:
        data = json.load(f)
    client.import_json(data)
    print(client.get_balances())