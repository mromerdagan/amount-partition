from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from amount_partition.models import Balance, Target, PeriodicDeposit

class BudgetManagerClient(ABC):
    
    @abstractmethod
    def list_balances(self) -> List[str]:
        """List all balance names."""
        pass
    
    @abstractmethod
    def get_balances(self) -> Dict[str, Balance]:
        """Retrieve all balances as domain objects."""
        pass
    
    @abstractmethod
    def get_targets(self) -> Dict[str, Target]:
        """Retrieve all targets."""
        pass
    
    @abstractmethod
    def get_recurring(self) -> Dict[str, PeriodicDeposit]:
        """Retrieve all recurring payments."""
        pass

    @abstractmethod
    def deposit(self, amount: int, monthly: bool = False) -> Dict[str, int]:
        """Deposit an amount into the 'free' balance. Returns {"free": <amount>}."""
        pass

    @abstractmethod
    def withdraw(self, amount: int = 0) -> Dict[str, int]:
        """Withdraw an amount from the 'free' balance or all if amount is 0. Returns {"free": <amount>}."""
        pass

    @abstractmethod
    def add_to_balance(self, boxname: str, amount: int) -> Dict[str, int]:
        """Add an amount to a specific balance. Returns {"balance": <amount>, "free": <amount>}."""
        pass

    @abstractmethod
    def spend(self, boxname: str, amount: Optional[int] = None, use_credit: bool = True) -> Dict[str, int]:
        """Spend from a specific balance; None/0 means spend all. Returns {"balance": <amount>, "credit-spent": <amount>}."""
        pass

    @abstractmethod
    def transfer_between_balances(self, from_box: str, to_box: str, amount: int) -> Dict[str, int]:
        """Transfer amount from one balance to another. Returns {"from_box": <amount>, "to_box": <amount>}."""
        pass

    @abstractmethod
    def set_target(self, boxname: str, goal: int, due: str) -> Dict[str, str]:
        """Set a target for a specific balance. Returns {"status": "ok"}."""
        pass
    
    @abstractmethod
    def remove_target(self, name: str) -> Dict[str, str]:
        """Remove a target by its name. Returns {"status": "ok"}."""
        pass
    
    @abstractmethod
    def set_recurring(self, boxname: str, monthly: int, target: int) -> Dict[str, str]:
        """Set a recurring deposit for a specific balance. Returns {"status": "ok"}."""
        pass
    
    @abstractmethod
    def remove_recurring(self, boxname: str) -> Dict[str, str]:
        """Remove a recurring deposit for a specific balance. Returns {"status": "ok"}."""
        pass

    @abstractmethod
    def new_box(self, boxname: str) -> Dict[str, str]:
        """Create a new balance with the given name. Returns {"status": "ok"}."""
        pass

    @abstractmethod
    def remove_box(self, boxname: str) -> Dict[str, str]:
        """Remove a balance and transfer its amount to 'free'. Returns {"status": "ok"}."""
        pass

    @abstractmethod
    def rename_box(self, old_name: str, new_name: str) -> Dict[str, str]:
        """Rename a balance, preserving amount and related target/recurring. Returns {"status": "ok"}."""
        pass

    @abstractmethod
    def new_loan(self, amount: int, due: str) -> Dict[str, str]:
        """Create a self-loan with a negative amount and a target to repay by due date. Returns {"status": "ok"}."""
        pass

    @abstractmethod
    def create_db(self, db_dir: str) -> Dict[str, str]:
        """Create a new database at the given location. Returns {"status": "created", "location": ...}."""
        pass
    
    @abstractmethod
    def export_json(self) -> Dict:
        """Export the current state as a JSON object."""
        pass
    
    @abstractmethod
    def import_json(self, data: dict) -> Dict[str, str]:
        """Import data from a JSON object. Returns {"status": "imported", "db_dir": ...}."""
        pass
    
    @abstractmethod
    def plan_deposits(self, skip: str, is_monthly: bool, amount_to_use: int) -> Dict[str, int]:
        """Plan deposits for the given amount. Returns plan dict box -> amount."""
        pass
    
    @abstractmethod
    def plan_and_apply(self, skip: str, is_monthly: bool, amount_to_use: int) -> Dict[str, int]:
        """Plan and apply deposits for the given amount. Returns plan dict box -> amount."""
        pass
    
    @abstractmethod
    def new_instalment(self, instalment_name: str, from_balance: str, num_instalments: int, monthly_payment: int) -> Dict[str, str]:
        """Create a new instalment balance. Returns {"status": "ok"}."""
        pass
