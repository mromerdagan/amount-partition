from abc import ABC, abstractmethod
from typing import List, Dict
from amount_partition.models import Target, PeriodicDeposit

class BudgetManagerClient(ABC):
    
    @abstractmethod
    def list_balances(self) -> List[str]:
        """List all balance names."""
        pass
    
    @abstractmethod
    def get_balances(self) -> Dict[str, int]:
        """Retrieve all balance names."""
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
    def deposit(self, amount: int, merge_with_credit: bool = False):
        """Deposit an amount into the 'free' balance."""
        pass

    @abstractmethod
    def withdraw(self, amount: int = None):
        """Withdraw an amount from the 'free' balance or all if no amount is specified."""
        pass

    @abstractmethod
    def spend(self, boxname: str, amount: int = None, use_credit: bool = False):
        """Spend from a specific balance or all if no amount is specified."""
        pass

    @abstractmethod
    def add_to_balance(self, boxname: str, amount: int):
        """Add an amount to a specific balance."""
        pass

    @abstractmethod
    def set_target(self, boxname: str, goal: int, due: str):
        """Set a target for a specific balance."""
        pass

    @abstractmethod
    def new_box(self, boxname: str):
        """Create a new balance with the given name."""
        pass

    @abstractmethod
    def remove_box(self, boxname: str):
        """Remove a balance and transfer its amount to 'free'."""
        pass

    @abstractmethod
    def transfer_between_balances(self, from_box: str, to_box: str, amount: int):
        """Transfer amount from one balance to another."""
        pass

    @abstractmethod
    def new_loan(self, amount: int, due: str):
        """Create a self-loan with a negative amount and a target to repay by due date."""
        pass

    @abstractmethod
    def create_db(self, db_dir: str):
        """Create a new database at the given location."""
        pass