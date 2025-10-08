import os
import math
import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import OrderedDict
from typing import Dict
from amount_partition.parsing import dump_balances_file, dump_targets_file, dump_recurring_file ,parse_balances_file, parse_targets_file, parse_recurring_file
from amount_partition.models import Balance, FreeBalance, CreditBalance, Target, PeriodicDeposit, VirtualBalance, BalanceFactory


class BudgetManagerApi(object):

	def __init__(self, balances=None, targets=None, recurring=None):
		self._balances = balances or OrderedDict({"free": FreeBalance("free", 0), "credit-spent": CreditBalance("credit-spent", 0)})
		self._targets = targets or OrderedDict()
		self._recurring = recurring or OrderedDict()
		self.now = datetime.now()
  
	@property
	def total(self) -> VirtualBalance:
		"""Return the virtual 'total' balance."""
		total_amount = sum(balance.amount for balance in self._balances.values())
		return VirtualBalance(total_amount)

	@property
	def balances(self) -> OrderedDict:
		"""Return balances including virtual boxes like 'total'."""
		# Start with the actual balances
		result = self._balances.copy()
		
		# Add virtual box: total
		result['total'] = self.total

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
		balances = OrderedDict({"free": FreeBalance(0), "credit-spent": CreditBalance(0)})
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

		balances = OrderedDict({name: BalanceFactory.from_json(d) for name, d in data.get("partition", {}).items()})
		targets = OrderedDict({name: Target.from_json(d) for name, d in data.get("goals", {}).items()})
		recurring = OrderedDict({name: PeriodicDeposit.from_json(d) for name, d in data.get("periodic", {}).items()})

		return cls(balances, targets, recurring)

	def to_json(self) -> dict:
		"""
		Serialize the current state to a JSON-serializable dict with keys: partition, goals, periodic.
		"""
		# partition: {boxname: amount}
		partition = {balance_name: balance.to_json() for balance_name, balance in self._balances.items()}

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

	def get_targets(self) -> dict[str, Target]:
		"""Return a dictionary of Target objects for each balance with a target."""
		return {k: Target(goal=v.goal, due=v.due) for k, v in self._targets.items()}

	def get_recurring(self) -> dict[str, PeriodicDeposit]:
		"""Return a dictionary of PeriodicDeposit objects for each balance with a recurring deposit."""
		return {k: PeriodicDeposit(amount=v.amount, target=v.target) for k, v in self._recurring.items()}

	def deposit(self, amount: int, monthly: bool = True) -> None:
		"""Deposit an amount into 'free'. Optionally merge 'credit-spent'."""
		self._balances['free'].amount += amount
		if monthly:
			self._balances['free'].amount += self._balances['credit-spent'].amount
			self._balances['credit-spent'].amount = 0

	def withdraw(self, amount: int = 0) -> None:
		"""Withdraw an amount from 'free'. If amount is 0, empty 'free'."""
		if not(amount):
			self._balances['free'].amount = 0
		else:
			if amount > self._balances['free'].amount:
				raise ValueError("'free' box must be greater or equal to 0 (max reduction: {})".format(self._balances['free'].amount))
			self._balances['free'].amount -= amount

	def spend(self, boxname: str, amount: int = 0, use_credit: bool = True) -> None:
		"""Spend an amount from a balance. By default uses credit (adds to 'credit-spent')."""
		if not(boxname in self._balances):
			raise KeyError(f"Key '{boxname}' is missing from balances")
		if not(amount):
			amount = self._balances[boxname].amount

		if amount > self._balances[boxname].amount:
			raise ValueError(f'Balance values must be greater or equal to 0 (max reduction {self._balances[boxname].amount})')

		self._balances[boxname].amount -= amount # reduce amount from balance
		if use_credit:
			self._balances['credit-spent'].amount += amount

	def add_to_balance(self, boxname: str, amount: int) -> None:
		"""Increase a balance by amount, decreasing 'free' by the same amount."""
		if not(boxname in self._balances):
			raise KeyError(f"Key '{boxname}' is missing from database")
		if amount > self._balances['free'].amount:
			raise ValueError(f"Trying to add amount larger than available at 'free' (free={self._balances['free'].amount})")

		self._balances['free'].amount -= amount
		self._balances[boxname].amount += amount

	def transfer_between_balances(self, from_box: str, to_box: str, amount: int) -> None:
		"""Transfer amount from one balance to another."""
		for boxname in [from_box, to_box]:
			if not(boxname in self._balances):
				raise KeyError(f"Key '{boxname}' is missing from database")

		if amount > self._balances[from_box].amount:
			raise ValueError(f'Amount in source balance not sufficient (existing amount: {self._balances[from_box].amount})')

		self._balances[from_box].amount -= amount
		self._balances[to_box].amount += amount


	def new_box(self, boxname: str) -> None:
		"""Create a new balance with the given name and zero value."""
		if boxname in self._balances:
			raise KeyError(f"Key '{boxname}' is already in database")
		self._balances[boxname] = Balance(0)

	def remove_box(self, boxname: str) -> None:
		"""Remove a balance and transfer its amount to 'free'. Also remove related targets and recurring entries."""
		if not(boxname in self._balances):
			raise KeyError(f"Key '{boxname}' is missing from database")
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

		self._balances[boxname].amount -= amount
		self._balances['free'].amount += amount
		self.set_target(boxname, 0, due)
	
	####  goal methods
	def set_target(self, boxname: str, goal: int, due: str) -> None:
		"""Set a target amount and due date for a balance."""
		if not(boxname in self._balances):
			raise KeyError(f"Key '{boxname}' is missing from database ('{self.db_dir}')")
		# Make sure target isn't already a recurring deposit
		if boxname in self._recurring:
			raise ValueError(f"Target for '{boxname}' cannot be set because it is already a recurring deposit")
		due = datetime.strptime(due, '%Y-%m')
		self._targets[boxname] = Target(goal=goal, due=due)

	def remove_target(self, boxname: str) -> None:
		"""Remove a target for the given balance."""
		if not(boxname in self._targets):
			raise KeyError(f"Key '{boxname}' is missing from targets ('{self.targets_path}')")
		del(self._targets[boxname])
	
	#### Recurring payments related methods
	def set_recurring(self, boxname: str, periodic_amount: int, target: int = 0) -> None:
		"""Set a recurring deposit for a balance, with an optional target amount."""
		if not(boxname in self._balances):
			raise KeyError(f"Key '{boxname}' is missing from database ('{self.db_dir}')")
		# Make sure recurring isn't already a target
		if boxname in self._targets:
			raise ValueError(f"Recurring deposit for '{boxname}' cannot be set because it is already a target")
		self._recurring[boxname] = PeriodicDeposit(periodic_amount, target)

	def remove_recurring(self, boxname: str) -> None:
		"""Remove a recurring deposit for the given balance."""
		if not(boxname in self._recurring):
			raise KeyError(f"Key '{boxname}' is missing from recurring deposits ('{self.recurring_path}')")
		del(self._recurring[boxname])

	#### Deposits plan methods
	@staticmethod
	def _scale_deposit_plan(plan: dict[str, int], target_amount: int) -> dict[str, int]:
		"""
		Scale integer amounts proportionally so that the new integer amounts sum to target_amount.
		Uses the Largest Remainder (Hamilton) method:
		  1) Compute exact scaled value ai' = ai * s where s = target_amount / sum(ai)
		  2) Take floors fi = floor(ai')
		  3) Distribute the remaining R = target_amount - sum(fi) by +1 to the R items with
		"""
		if target_amount < 0:
			raise ValueError("target_amount must be >= 0")
		if not plan:
			return {}
		if any(v < 0 for v in plan.values()):
			raise ValueError("Deposit plan contains negative amounts")

		total = sum(plan.values())
		if total == 0:
			# Nothing to scale; return zeros matching the number of keys if target_amount is 0,
			# or spread +1s deterministically if target_amount > 0 (rare edge). Here we return zeros.
			return {k: 0 for k in plan}

		scale = target_amount / total

		# First pass: floors and fractional parts
		floors: dict[str, int] = {}
		remainders: list[tuple[float, int, str]] = []  # (remainder, -orig_amount, key) for deterministic sorting
		for key, orig in plan.items():
			exact = orig * scale
			f = int(exact // 1)  # floor
			r = exact - f
			floors[key] = f
			# tie-breaker: larger original amount first, then lexicographic key
			remainders.append((r, -orig, key))

		# How many +1's we need to distribute
		R = target_amount - sum(floors.values())
		if R <= 0:
			# we're done (can happen if target_amount == 0)
			return floors

		# Sort by remainder desc, then by larger original amount, then by key asc for determinism
		remainders.sort(key=lambda t: (-t[0], t[1], t[2]))

		result = dict(floors)
		for i in range(R):
			_, _, key = remainders[i]
			result[key] += 1

		return result
 
	def plan_deposits(self, skip: str = '', is_monthly: bool = True, amount_to_use: int = 0) -> dict[str, int]:
		"""Suggest deposit amounts for each balance to meet targets and recurring deposits.

		Params:
		skip (string):
			comma separated balance names that you want to avoid from putting into generated
			deposit_plan
		is_monthly (bool):
			'True' if this is the deposit_plan is meant to be used for the regular monthly
			deposit (for example, on the salary pay day). If called with 'False' this means
			that this deposit_plan is yet another one that comes after the regular deposit.
			This is important because the monthly deposit per target needs to know how many
			months are left to reach the target- this number should reflect the number of
			deposits left. Therefore if the regular deposit has taken place already, then
			there is one less deposit left so we need to take this into account on the 
			calculations
		amount_to_use (int):
    		If > 0, linearly scale the suggested amounts so their sum equals `amount_to_use`,
    		using the Largest Remainder method (sum is exact; proportions preserved as closely as possible).

		Return value: dictionary that maps balance name to amount that needs to be put in balance.
		This dictionary can be fed into the method "apply_deposit_plan" if there is
		sufficient amount available in "free" and "credit-spent"
		"""
		deposit_plan = {}
		skip = skip.split(',')
		for boxname, target in self._targets.items():
			if boxname in skip:
				continue
			curr_box_balance = self._balances.get(boxname, Balance(0)).amount
			box_suggestion = target.monthly_payment(balance=curr_box_balance, curr_month_payed=not is_monthly)
			if box_suggestion == 0: # Target is already reached
				continue
			deposit_plan[boxname] = box_suggestion

		for boxname in self._recurring:
			if boxname in deposit_plan:
				raise KeyError(f"Key '{boxname}' appears in 'recurring' as well as in 'targets'")
			if boxname in skip:
				continue
			should_recurring = \
					self._recurring[boxname].target == 0 or \
					self._balances[boxname].amount < self._recurring[boxname].target
			if not(should_recurring):
				continue

			# Calculate how much should be added in this deposit
			if self._recurring[boxname].target == 0:
				deposit_plan[boxname] = self._recurring[boxname].amount
			elif (self._balances[boxname].amount + self._recurring[boxname].amount) < self._recurring[boxname].target:
				deposit_plan[boxname] = self._recurring[boxname].amount
			else: # Missing part is less than usual amount
				deposit_plan[boxname] = self._recurring[boxname].target - self._balances[boxname].amount
    
		
		# Linear scaling to a target total using Largest Remainder method
		if amount_to_use > 0 and deposit_plan:
			current_total = sum(deposit_plan.values())
			if current_total > 0:
				deposit_plan = self._scale_deposit_plan(deposit_plan, amount_to_use)
		
		return deposit_plan

	def _apply_deposit_plan(self, deposit_plan: dict[str, int]) -> None:
		"""Apply a deposit plan to the balances, updating their values."""
		plan_sum = sum([deposit_plan[boxname] for boxname in deposit_plan])
		if plan_sum > self._balances['free'].amount:
			missing = plan_sum - self._balances['free'].amount
			raise ValueError(f"Cannot apply deposit plan- missing {missing} in 'free'")
		for boxname in deposit_plan:
			if boxname not in self._balances:
				raise KeyError(f"Key '{boxname}' is missing from database")
			self.add_to_balance(boxname, deposit_plan[boxname])

	def plan_and_apply(self, skip: str, is_monthly: bool, amount_to_use: int) -> Dict[str, int]:
		deposit_plan = self.plan_deposits(skip=skip, is_monthly=is_monthly, amount_to_use=amount_to_use)
		self._apply_deposit_plan(deposit_plan)
		return deposit_plan

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
