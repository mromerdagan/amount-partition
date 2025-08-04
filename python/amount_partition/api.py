import os
import math
from pathlib import Path
from datetime import datetime, timedelta
from collections import OrderedDict
from .parsing import parse_balance_line, parse_target_line, parse_periodic_line, extract_lines
from .models import Target, PeriodicDeposit

DEPOSIT_DAY = 10  # Day of month after which deposit is considered done
DAYS_IN_MONTH = 30  # Used for monthly calculations

class BudgetManagerApi(object):

	def __init__(self, db_dir: str) -> None:
		"""Initialize AmountPartition with a database directory."""
		self.db_dir = Path(db_dir)
		self.partition_path = self.db_dir / 'partition'
		self.goals_path = self.db_dir / 'goals'
		self.periodic_path = self.db_dir / 'periodic'

		# Initialize data structures - will get values at setup()
		self.balances = OrderedDict()
		self.targets = OrderedDict()
		self.recurring = OrderedDict()

		self.setup()

		# Used in multiple functions
		self.now = datetime.now()

	def setup(self) -> None:
		"""Set up partition, goals, and periodic data from files or initialize new ones."""
		if self.balances or self.targets or self.recurring:
			raise RuntimeError('Setup has already been run before. The balances, targets, or recurring data structures are not empty. This likely indicates a logic error or repeated initialization.')

		if not(self.partition_path.exists()): # Initialize new balances
			with self.partition_path.open('w') as fh:
				fh.close()
			self.new_box('free')
			self.new_box('credit-spent')
			self.dump_data()
		else: # Load existing partition
			try:
				self._read_all_data()
			except Exception as e:
				raise RuntimeError(f"Failed to read partition data from {self.db_dir}: {e}") from e
	

	@classmethod
	def create_db(cls, location: str) -> 'BudgetManagerApi':
		"""
		Create a new database at the given location. Raises an error if a DB already exists there.
		Returns the BudgetManagerApi instance for the new DB.
		"""
		db_dir = Path(location)
		partition_path = db_dir / 'partition'
		if partition_path.exists():
			raise FileExistsError(f"A database already exists at {partition_path}")
		db_dir.mkdir(parents=True, exist_ok=True)
		instance = cls(location)
		return instance

	def to_json(self) -> dict:
		"""
		Serialize the current state to a JSON-serializable dict with keys: partition, goals, periodic.
		"""
		# partition: {boxname: amount}
		partition = dict(self.balances)

		# goals: {boxname: {"goal": int, "due": "YYYY-MM"}}
		goals = {
			k: {"goal": v.goal, "due": v.due.strftime("%Y-%m")}
			for k, v in self.targets.items()
		}

		# periodic: {boxname: {"amount": int, "target": int}}
		periodic = {
			k: {"amount": v.amount, "target": v.target}
			for k, v in self.recurring.items()
		}

		return {"partition": partition, "goals": goals, "periodic": periodic}

	@classmethod
	def from_json(cls, db_dir: str, data: dict) -> 'BudgetManagerApi':
		"""
		Create a BudgetManagerApi instance from a JSON dict (as produced by to_json).
		Overwrites any existing data in the db_dir.
		"""
		try:
			instance = cls.create_db(db_dir)
		except FileExistsError:
			instance = cls(db_dir)
   
		# partition
		instance.balances.clear()
		for boxname, amount in data.get("partition", {}).items():
			instance.balances[boxname] = amount
   
		# goals
		instance.targets.clear()
		for boxname, goal_data in data.get("goals", {}).items():
			due = goal_data["due"]
			instance.set_target(boxname, goal_data["goal"], due)
   
		# periodic
		instance.recurring.clear()
		for boxname, periodic_data in data.get("periodic", {}).items():
			instance.set_recurring(boxname, periodic_data["amount"], periodic_data["target"])
		instance.dump_data()
		return instance

	def _read_partition(self) -> None:
		"""Read balances data from file into self.balances."""
		raw = self.partition_path.read_text()
		lines = extract_lines(raw)
		for line in lines:
			try:
				boxname, amount = parse_balance_line(line)
				self.balances[boxname] = amount
			except ValueError as e:
				raise ValueError(f"Malformed line in partition file: '{line}'. Expected format: '<boxname> <size>'") from e

	def _read_goals(self) -> None:
		"""Read targets data from file into self.targets."""
		if not(self.goals_path.exists()):
			return

		raw = self.goals_path.read_text()
		lines = extract_lines(raw)
		for line in lines:
			try:
				boxname, target = parse_target_line(line)
				self.targets[boxname] = target
			except ValueError as e:
				raise ValueError(f"Malformed line in goals file: '{line}'. Expected format: '<boxname> <goal> <due YYYY-MM>'") from e

	def _read_periodic(self) -> None:
		"""Read recurring deposit data from file into self.recurring."""
		if not(self.periodic_path.exists()):
			return

		raw = self.periodic_path.read_text()
		lines = extract_lines(raw)
		for line in lines:
			try:
				boxname, periodic = parse_periodic_line(line)
				self.recurring[boxname] = periodic
			except ValueError as e:
				raise ValueError(f"Malformed line in periodic file: '{line}'. Expected format: '<boxname> <amount> <target>' or '<boxname> <amount>'") from e

	def _read_all_data(self) -> None:
		"""Read all data files (partition, goals, periodic) into their respective structures."""
		self._read_partition()
		self._read_goals()
		self._read_periodic()

	def dump_data(self) -> None:
		"""Write current partition, goals, and periodic data to files."""
		t = self.db_dir / (self.partition_path.name + '.new')
		with t.open('w') as fh:
			for target in self.balances:
				line = "{:<20} {}\n".format(target, self.balances[target])
				fh.write(line)
		t.replace(self.partition_path)

		if self.targets:
			t = self.db_dir / (self.goals_path.name + '.new')
			with t.open('w') as fh:
				for target in self.targets:
					line = "{:<20} {:<15} {}\n".format(\
							target, \
							self.targets[target].goal, \
							self.targets[target].due.strftime('%Y-%m') \
							)
					fh.write(line)
			t.replace(self.goals_path)

		if self.recurring:
			t = self.db_dir / (self.periodic_path.name + '.new')
			with t.open('w') as fh:
				for target in self.recurring:
					line = "{:<20} {:<10} {}\n".format(\
							target, \
							self.recurring[target].amount, \
							self.recurring[target].target, \
							)
					fh.write(line)
			t.replace(self.periodic_path)
   
	def list_balances(self) -> list[str]:
		"""Return a list of balance names."""
		return list(self.balances.keys())

	def get_total(self) -> int:
		"""Return the total sum of all balances."""
		amounts = [self.balances[boxname] for boxname in self.balances]
		return sum(amounts)

	def get_targets(self) -> dict[str, Target]:
		"""Return a dictionary of Target objects for each balance with a target."""
		return {k: Target(goal=v.goal, due=v.due) for k, v in self.targets.items()}

	def deposit(self, amount: int, merge_with_credit: bool = True) -> None:
		"""Deposit an amount into 'free'. Optionally merge 'credit-spent'."""
		self.balances['free'] += amount
		if merge_with_credit:
			self.balances['free'] += self.balances['credit-spent']
			self.balances['credit-spent'] = 0

	def withdraw(self, amount: int = 0) -> None:
		"""Withdraw an amount from 'free'. If amount is 0, empty 'free'."""
		if not(amount):
			self.balances['free'] = 0
		else:
			if amount > self.balances['free']:
				raise ValueError("'free' box must be greater or equal to 0 (max reduction: {})".format(self.balances['free']))
			self.balances['free'] -= amount

	def spend(self, boxname: str, amount: int = 0, use_credit: bool = False) -> None:
		"""Spend an amount from a balance. If use_credit, add to 'credit-spent'."""
		if not(boxname in self.balances):
			raise KeyError(f"Key '{boxname}' is missing from balances (defined at '{self.partition_path}')")
		if not(amount):
			amount = self.balances[boxname]

		if amount > self.balances[boxname]:
			raise ValueError(f'Balance values must be greater or equal to 0 (max reduction {self.balances[boxname]})')

		self.balances[boxname] -= amount # reduce amount from balance
		if use_credit:
			self.balances['credit-spent'] += amount

	def add_to_balance(self, boxname: str, amount: int) -> None:
		"""Increase a balance by amount, decreasing 'free' by the same amount."""
		if not(boxname in self.balances):
			raise KeyError(f"Key '{boxname}' is missing from database ('{self.partition_path}')")
		if amount > self.balances['free']:
			raise ValueError(f"Trying to add amount larger than available at 'free' (free={self.balances['free']})")

		self.balances['free'] -= amount
		self.balances[boxname] += amount
	
	def transfer_between_balances(self, from_box: str, to_box: str, amount: int) -> None:
		"""Transfer amount from one balance to another."""
		for boxname in [from_box, to_box]:
			if not(boxname in self.balances):
				raise KeyError(f"Key '{boxname}' is missing from database ('{self.partition_path}')")

		if amount > self.balances[from_box]:
			raise ValueError(f'Amount in source balance not sufficient (existing amount: {self.balances[from_box]})')

		self.balances[from_box] -= amount
		self.balances[to_box] += amount


	def new_box(self, boxname: str) -> None:
		"""Create a new balance with the given name and zero value."""
		if boxname in self.balances:
			raise KeyError(f"Key '{boxname}' is already in database ('{self.partition_path}')")
		self.balances[boxname] = 0

	def remove_box(self, boxname: str) -> None:
		"""Remove a balance and transfer its amount to 'free'. Also remove related targets and recurring entries."""
		if not(boxname in self.balances):
			raise KeyError(f"Key '{boxname}' is missing from database ('{self.partition_path}')")
		self.spend(boxname)
		del(self.balances[boxname])

		if boxname in self.targets:
			del(self.targets[boxname])

		if boxname in self.recurring:
			del(self.recurring[boxname])
	
	def new_loan(self, amount: int, due: str) -> None:
		"""Create a self-loan balance with a negative amount and a target to repay by due date."""
		boxname = 'self-loan'
		if not(boxname in self.balances):
			self.new_box(boxname)

		self.balances[boxname] -= amount
		self.balances['free'] += amount
		self.set_target(boxname, 0, due)
	
	#### goal methods
	def set_target(self, boxname: str, goal: int, due: str) -> None:
		"""Set a target amount and due date for a balance."""
		if not(boxname in self.balances):
			raise KeyError(f"Key '{boxname}' is missing from database ('{self.db_dir}')")
		due = datetime.strptime(due, '%Y-%m')
		self.targets[boxname] = Target(goal=goal, due=due)

	def remove_target(self, boxname: str) -> None:
		"""Remove a target for the given balance."""
		if not(boxname in self.targets):
			raise KeyError(f"Key '{boxname}' is missing from targets ('{self.goals_path}')")
		del(self.targets[boxname])
	
	def target_monthly_deposit(self, boxname: str, after_monthly_deposit: bool) -> int:
		"""Calculate the required monthly deposit to reach a target by its due date."""
		target = self.targets[boxname]
		goal = target.goal
		due = target.due
		curr_amount = self.balances[boxname]
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
		if not(boxname in self.balances):
			raise KeyError(f"Key '{boxname}' is missing from database ('{self.db_dir}')")
		self.recurring[boxname] = PeriodicDeposit(periodic_amount, target)

	def remove_recurring(self, boxname: str) -> None:
		"""Remove a recurring deposit for the given balance."""
		if not(boxname in self.recurring):
			raise KeyError(f"Key '{boxname}' is missing from recurring deposits ('{self.periodic_path}')")
		del(self.recurring[boxname])
	
	def _periodic_months_left(self, boxname: str) -> int:
		"""Return the number of months left to reach the recurring target for a balance."""
		missing = self.recurring[boxname].target - self.balances[boxname]
		left = missing / self.recurring[boxname].amount
		left = math.ceil(left)
		return left


	#### Suggestion methods
	def suggest_deposits(self, skip: str = '', additional_suggestion: bool = False) -> dict[str, int]:
		"""Suggest deposit amounts for each balance to meet targets and recurring deposits.

		Params:
		skip (string):
			comma separated balance names that you want to avoid from putting into generated
			suggestion
		additional_suggestion (bool):
			'False' if this is the suggestion is meant to be used for the regular monthly
			deposit (for example, on the salary pay day). If called with 'True' this means
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
		for boxname in self.targets:
			if boxname in skip:
				continue
			box_suggestion = self.target_monthly_deposit(boxname, additional_suggestion)
			if box_suggestion == 0: # Target is already reached
				continue
			suggestion[boxname] = box_suggestion

		for boxname in self.recurring:
			if boxname in suggestion:
				raise KeyError(f"Key '{boxname}' appears in 'recurring' as well as in 'targets'")
			if boxname in skip:
				continue
			should_recurring = \
					self.recurring[boxname].target == 0 or \
					self.balances[boxname] < self.recurring[boxname].target
			if not(should_recurring):
				continue

			# Calculate how much should be added in this deposit
			if self.recurring[boxname].target == 0:
				suggestion[boxname] = self.recurring[boxname].amount
			elif (self.balances[boxname] + self.recurring[boxname].amount) < self.recurring[boxname].target:
				suggestion[boxname] = self.recurring[boxname].amount
			else: # Missing part is less than usual amount
				suggestion[boxname] = self.recurring[boxname].target - self.balances[boxname]
		return suggestion

	def apply_suggestion(self, suggestion: dict[str, int]) -> None:
		"""Apply a deposit suggestion to the balances, updating their values."""
		suggestion_sum = sum([suggestion[boxname] for boxname in suggestion])
		if suggestion_sum > self.balances['free']:
			missing = suggestion_sum - self.balances['free']
			raise ValueError(f"Cannot apply suggestion- missing {missing} in 'free'")
		for boxname in suggestion:
			if boxname not in self.balances:
				raise KeyError(f"Key '{boxname}' is missing from database ('{self.partition_path}')")
			self.add_to_balance(boxname, suggestion[boxname])
	
	# Reserved funds for future targets
	def reserved_amount(self, days_to_lock: int) -> int:
		"""
		Return the total amount in balances that are reserved for targets with due dates at least `days_to_lock` days in the future.

		This represents the sum of all funds that are committed to future targets (goals) and cannot be considered available for other uses (such as short-term deposits or spending) for at least the given number of days. It helps you understand how much of your money is 'locked' for future obligations and how much is truly available for flexible use.
		"""
		today = datetime.now()
		tuples = []
		for x in self.targets:
			amount_got = self.balances[x]
			due_date = self.targets[x].due
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
	homedir = os.environ['HOME']
	DB = f"{homedir}/git/finance/partition-bp"
	fp = BudgetManagerApi(DB)
