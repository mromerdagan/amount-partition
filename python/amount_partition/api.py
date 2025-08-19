import os
import math
import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import OrderedDict
from amount_partition.parsing import dump_balances_file, dump_targets_file, dump_recurring_file ,parse_balances_file, parse_targets_file, parse_recurring_file
from amount_partition.models import Target, PeriodicDeposit

DEPOSIT_DAY = 10  # Day of month after which deposit is considered done
DAYS_IN_MONTH = 30  # Used for monthly calculations

class BudgetManagerApi(object):

	def __init__(self, balances=None, targets=None, recurring=None):
		self._balances = balances or OrderedDict({"free": 0, "credit-spent": 0})
		self._targets = targets or OrderedDict()
		self._recurring = recurring or OrderedDict()
		self.now = datetime.now()

	@property
	def balances(self) -> OrderedDict:
		"""Return balances including virtual boxes like 'total'."""
		# Start with the actual balances
		result = self._balances.copy()
		
		# Add virtual box: total
		total = sum(self._balances.values())
		result['total'] = total
		
		return result

	@classmethod
	def from_storage(cls, db_dir: str) -> 'BudgetManagerApi':
		"""
		Create a BudgetManagerApi instance from the database directory.
		Reads balances, targets, and recurring deposits from files.
		"""
		db_dir = Path(db_dir)
		balances_path = db_dir / 'partition'
		targets_path = db_dir / 'goals'
		recurring_path = db_dir / 'periodic'
  
		if not balances_path.exists():
			raise FileNotFoundError(f"Balances file not found at {balances_path}")

		try:
			balances = parse_balances_file(balances_path)
			targets = parse_targets_file(targets_path)
			recurring = parse_recurring_file(recurring_path)
		except FileNotFoundError as e:
			raise RuntimeError(f"Error reading files in {db_dir}: {e}")
		return cls(balances, targets, recurring)
	

	@staticmethod
	def create_db(db_path: str) -> None:
		"""
		Create a new database at the given location. Raises an error if a DB already exists there.
		"""
		db_path = Path(db_path)
		balances_path = db_path / 'partition'
		if balances_path.exists():
			raise FileExistsError(f"A database already exists at {balances_path}")

		db_path.mkdir(parents=True, exist_ok=True)
		balances = OrderedDict({"free": 0, "credit-spent": 0})
		targets = OrderedDict()
		recurring = OrderedDict()
		BudgetManagerApi.dump_data_static(db_path, balances, targets, recurring)

	@classmethod
	def from_json(cls, json_data_or_path) -> 'BudgetManagerApi':
		if isinstance(json_data_or_path, str) or isinstance(json_data_or_path, Path):
			with open(json_data_or_path) as f:
				data = json.load(f)
		else:
			data = json_data_or_path

		balances = OrderedDict(data.get("partition", {}))
		targets = OrderedDict({name: Target.from_json(d) for name, d in data.get("goals", {}).items()})
		recurring = OrderedDict({name: PeriodicDeposit.from_json(d) for name, d in data.get("periodic", {}).items()})

		return cls(balances, targets, recurring)

	def to_json(self) -> dict:
		"""
		Serialize the current state to a JSON-serializable dict with keys: partition, goals, periodic.
		"""
		# partition: {boxname: amount}
		partition = dict(self._balances)

		# goals: {boxname: {"goal": int, "due": "YYYY-MM"}}
		goals = {target_name: target.to_json() for target_name, target in self._targets.items()}

		# periodic: {boxname: {"amount": int, "target": int}}
		periodic = {recurring_name: recurring.to_json() for recurring_name, recurring in self._recurring.items()}

		return {"partition": partition, "goals": goals, "periodic": periodic}

	def dump_data(self, db_dir: str) -> None:
		"""
		Write the current state to files in the database directory.
		"""
		db_path = Path(db_dir)
		self.dump_data_static(db_path, self._balances, self._targets, self._recurring)


	@staticmethod
	def dump_data_static(db_dir: str, balances, targets, recurring) -> None:
		"""Write partition, goals, and periodic data to files."""
		db_path = Path(db_dir)
		if not db_path.exists():
			db_path.mkdir(parents=True, exist_ok=True)

		# Write balances
		t = db_path / 'partition.tmp'
		dump_balances_file(t, balances)
		t.replace(db_path / 'partition')

		# Write targets
		t = db_path / 'goals.tmp'
		dump_targets_file(t, targets)
		t.replace(db_path / 'goals')

		# Write recurring deposits
		t = db_path / 'periodic.tmp'
		dump_recurring_file(t, recurring)
		t.replace(db_path / 'periodic')
   
	def list_balances(self) -> list[str]:
		"""Return a list of balance names."""
		return list(self._balances.keys())

	def get_total(self) -> int:
		# TODO: remove this method
		"""Return the total sum of all balances."""
		amounts = [self._balances[boxname] for boxname in self._balances]
		return sum(amounts)

	def get_targets(self) -> dict[str, Target]:
		"""Return a dictionary of Target objects for each balance with a target."""
		return {k: Target(goal=v.goal, due=v.due) for k, v in self._targets.items()}

	def get_recurring(self) -> dict[str, PeriodicDeposit]:
		"""Return a dictionary of PeriodicDeposit objects for each balance with a recurring deposit."""
		return {k: PeriodicDeposit(amount=v.amount, target=v.target) for k, v in self._recurring.items()}

	def deposit(self, amount: int, merge_with_credit: bool = True) -> None:
		"""Deposit an amount into 'free'. Optionally merge 'credit-spent'."""
		self._balances['free'] += amount
		if merge_with_credit:
			self._balances['free'] += self._balances['credit-spent']
			self._balances['credit-spent'] = 0

	def withdraw(self, amount: int = 0) -> None:
		"""Withdraw an amount from 'free'. If amount is 0, empty 'free'."""
		if not(amount):
			self._balances['free'] = 0
		else:
			if amount > self._balances['free']:
				raise ValueError("'free' box must be greater or equal to 0 (max reduction: {})".format(self._balances['free']))
			self._balances['free'] -= amount

	def spend(self, boxname: str, amount: int = 0, use_credit: bool = False) -> None:
		"""Spend an amount from a balance. If use_credit, add to 'credit-spent'."""
		if not(boxname in self._balances):
			raise KeyError(f"Key '{boxname}' is missing from balances")
		if not(amount):
			amount = self._balances[boxname]

		if amount > self._balances[boxname]:
			raise ValueError(f'Balance values must be greater or equal to 0 (max reduction {self._balances[boxname]})')

		self._balances[boxname] -= amount # reduce amount from balance
		if use_credit:
			self._balances['credit-spent'] += amount

	def add_to_balance(self, boxname: str, amount: int) -> None:
		"""Increase a balance by amount, decreasing 'free' by the same amount."""
		if not(boxname in self._balances):
			raise KeyError(f"Key '{boxname}' is missing from database")
		if amount > self._balances['free']:
			raise ValueError(f"Trying to add amount larger than available at 'free' (free={self._balances['free']})")

		self._balances['free'] -= amount
		self._balances[boxname] += amount
	
	def transfer_between_balances(self, from_box: str, to_box: str, amount: int) -> None:
		"""Transfer amount from one balance to another."""
		for boxname in [from_box, to_box]:
			if not(boxname in self._balances):
				raise KeyError(f"Key '{boxname}' is missing from database")

		if amount > self._balances[from_box]:
			raise ValueError(f'Amount in source balance not sufficient (existing amount: {self._balances[from_box]})')

		self._balances[from_box] -= amount
		self._balances[to_box] += amount


	def new_box(self, boxname: str) -> None:
		"""Create a new balance with the given name and zero value."""
		if boxname in self._balances:
			raise KeyError(f"Key '{boxname}' is already in database")
		self._balances[boxname] = 0

	def remove_box(self, boxname: str) -> None:
		"""Remove a balance and transfer its amount to 'free'. Also remove related targets and recurring entries."""
		if not(boxname in self._balances):
			raise KeyError(f"Key '{boxname}' is missing from database")
		self.spend(boxname)
		del(self._balances[boxname])

		if boxname in self._targets:
			del(self._targets[boxname])

		if boxname in self._recurring:
			del(self._recurring[boxname])
	
	def new_loan(self, amount: int, due: str) -> None:
		"""Create a self-loan balance with a negative amount and a target to repay by due date."""
		boxname = 'self-loan'
		if not(boxname in self._balances):
			self.new_box(boxname)
   
		# Validate amount is positive
		if amount <= 0:
			raise ValueError("Loan amount must be positive")

		# Validate due is in YYYY-MM format
		try:
			due_date = datetime.strptime(due, '%Y-%m')
		except ValueError:
			raise ValueError("Due date must be in YYYY-MM format")

		# Validate due is in the future
		if due_date <= self.now:
			raise ValueError("Due date must be in the future")

		self._balances[boxname] -= amount
		self._balances['free'] += amount
		self.set_target(boxname, 0, due)
	
	####  goal methods
	def set_target(self, boxname: str, goal: int, due: str) -> None:
		"""Set a target amount and due date for a balance."""
		if not(boxname in self._balances):
			raise KeyError(f"Key '{boxname}' is missing from database ('{self.db_dir}')")
		due = datetime.strptime(due, '%Y-%m')
		self._targets[boxname] = Target(goal=goal, due=due)

	def remove_target(self, boxname: str) -> None:
		"""Remove a target for the given balance."""
		if not(boxname in self._targets):
			raise KeyError(f"Key '{boxname}' is missing from targets ('{self.targets_path}')")
		del(self._targets[boxname])
	
	def target_monthly_deposit(self, boxname: str, after_monthly_deposit: bool) -> int:
		# TODO: Replace this function with Target method
		"""Calculate the required monthly deposit to reach a target by its due date."""
		target = self._targets[boxname]
		goal = target.goal
		due = target.due
		curr_amount = self._balances[boxname]
		diff = due - self.now
		months_left = math.ceil(diff.days / DAYS_IN_MONTH)
		if after_monthly_deposit:
			months_left -= 1
		if months_left > 0:
			monthly = (goal - curr_amount) / months_left
		else: # months_left == 0
			monthly = goal - curr_amount
		monthly = int(monthly)
		if monthly < 0: # Target is already reached
			monthly = 0
		return monthly
	
	#### Recurring payments related methods
	def set_recurring(self, boxname: str, periodic_amount: int, target: int = 0) -> None:
		"""Set a recurring deposit for a balance, with an optional target amount."""
		if not(boxname in self._balances):
			raise KeyError(f"Key '{boxname}' is missing from database ('{self.db_dir}')")
		self._recurring[boxname] = PeriodicDeposit(periodic_amount, target)

	def remove_recurring(self, boxname: str) -> None:
		"""Remove a recurring deposit for the given balance."""
		if not(boxname in self._recurring):
			raise KeyError(f"Key '{boxname}' is missing from recurring deposits ('{self.recurring_path}')")
		del(self._recurring[boxname])
	
	def _periodic_months_left(self, boxname: str) -> int:
		# TODO: implement in PeriodicDeposit as a method
		"""Return the number of months left to reach the recurring target for a balance."""
		missing = self._recurring[boxname].target - self._balances[boxname]
		left = missing / self._recurring[boxname].amount
		left = math.ceil(left)
		return left


	#### Suggestion methods
	def suggest_deposits(self, skip: str = '', is_monthly: bool = True) -> dict[str, int]:
		"""Suggest deposit amounts for each balance to meet targets and recurring deposits.

		Params:
		skip (string):
			comma separated balance names that you want to avoid from putting into generated
			suggestion
		is_monthly (bool):
			'True' if this is the suggestion is meant to be used for the regular monthly
			deposit (for example, on the salary pay day). If called with 'False' this means
			that this suggestion is yet another one that comes after the regular deposit.
			This is important because the monthly deposit per target needs to know how many
			months are left to reach the target- this number should reflect the number of
			deposits left. Therefore if the regular deposit has taken place already, then
			there is one less deposit left so we need to take this into account on the
		calculations

		Return value: dictionary that maps balance name to amount that needs to be put in balance.
		This dictionary can be fed into the method "apply_suggestion" if there is
		sufficient amount available in "free" and "credit-spent"
		"""
		suggestion = {}
		skip = skip.split(',')
		for boxname in self._targets:
			if boxname in skip:
				continue
			box_suggestion = self.target_monthly_deposit(boxname, not is_monthly)
			if box_suggestion == 0: # Target is already reached
				continue
			suggestion[boxname] = box_suggestion

		for boxname in self._recurring:
			if boxname in suggestion:
				raise KeyError(f"Key '{boxname}' appears in 'recurring' as well as in 'targets'")
			if boxname in skip:
				continue
			should_recurring = \
					self._recurring[boxname].target == 0 or \
					self._balances[boxname] < self._recurring[boxname].target
			if not(should_recurring):
				continue

			# Calculate how much should be added in this deposit
			if self._recurring[boxname].target == 0:
				suggestion[boxname] = self._recurring[boxname].amount
			elif (self._balances[boxname] + self._recurring[boxname].amount) < self._recurring[boxname].target:
				suggestion[boxname] = self._recurring[boxname].amount
			else: # Missing part is less than usual amount
				suggestion[boxname] = self._recurring[boxname].target - self._balances[boxname]
		return suggestion

	def apply_suggestion(self, suggestion: dict[str, int]) -> None:
		"""Apply a deposit suggestion to the balances, updating their values."""
		suggestion_sum = sum([suggestion[boxname] for boxname in suggestion])
		if suggestion_sum > self._balances['free']:
			missing = suggestion_sum - self._balances['free']
			raise ValueError(f"Cannot apply suggestion- missing {missing} in 'free'")
		for boxname in suggestion:
			if boxname not in self._balances:
				raise KeyError(f"Key '{boxname}' is missing from database")
			self.add_to_balance(boxname, suggestion[boxname])
	
	# Reserved funds for future targets
	def reserved_amount(self, days_to_lock: int) -> int:
		"""
		Return the total amount in balances that are reserved for targets with due dates at least `days_to_lock` days in the future.

		This represents the sum of all funds that are committed to future targets (goals) and cannot be considered available for other uses (such as short-term deposits or spending) for at least the given number of days. It helps you understand how much of your money is 'locked' for future obligations and how much is truly available for flexible use.
		"""
		today = datetime.now()
		tuples = []
		for x in self._targets:
			amount_got = self._balances[x]
			due_date = self._targets[x].due
			delta = due_date - today
			days_left = delta.days
			tuples.append((amount_got, days_left))

		sorted_tuples = sorted(tuples, key=lambda x: x[1])
		reserved_amount = 0
		for amount_got, days_left in sorted_tuples:
			if days_left >= days_to_lock:
				reserved_amount += amount_got
		return reserved_amount


if __name__ == "__main__": ## DEBUG
	# homedir = os.environ['HOME']
	# DB = f"{homedir}/git/finance/partition-bp"
	# fp = BudgetManagerApi.from_storage(DB)
	fp = BudgetManagerApi()
	