
import os
import math
from pathlib import Path
from datetime import datetime, timedelta
from collections import OrderedDict
from dataclasses import dataclass

@dataclass
class PeriodicDeposit:
	amount: int
	target: int

def extract_lines(raw):
	lines = raw.split('\n')
	lines = [l.split('#')[0] for l in lines] # remove comments
	lines = [l.strip() for l in lines]
	lines = [l for l in lines if l] # remove empty lines
	return lines

class AmountPartition(object):
	def __init__(self, db_dir):
		self.db_dir = Path(db_dir)
		self.partition_path = self.db_dir / 'partition'
		self.goals_path = self.db_dir / 'goals'
		self.periodic_path = self.db_dir / 'periodic'

		# Initialize data structurs- will get values at setup()
		self.partition = OrderedDict()
		self.goals = OrderedDict()
		self.periodic = OrderedDict()

		self.setup()

		# Used in multiple functions
		self.now = datetime.now()

	def setup(self):
		if self.partition or self.goals or self.periodic:
			raise Exception('Setup has already been run before')

		if not(self.partition_path.exists()): # Initialize new partition
			with self.partition_path.open('w') as fh:
				fh.close()
			self.new_box('free')
			self.new_box('credit')
			self.dump_data()
		else: # Create new parition
			self.read_partition()
			self.read_goals()
			self.read_periodic()

	def read_partition(self):
		raw = self.partition_path.read_text()
		lines = extract_lines(raw)
		for line in lines:
			boxname, size = line.split()
			self.partition[boxname] = int(size)

	def read_goals(self):
		if not(self.goals_path.exists()):
			return

		raw = self.goals_path.read_text()
		lines = extract_lines(raw)
		for line in lines:
			boxname, goal, due = line.split()
			goal = int(goal)
			due = datetime.strptime(due, '%Y-%m')
			self.goals[boxname] = {'goal': goal, 'due': due}

	def read_periodic(self):
		if not(self.periodic_path.exists()):
			return

		raw = self.periodic_path.read_text()
		lines = extract_lines(raw)
		for line in lines:
			try:
				boxname, p, target = line.split()
			except ValueError: # Backward compatibility
				if len(line.split()) == 2:
					boxname, p = line.split()
					target = 0
				else:
					raise
			self.periodic[boxname] = PeriodicDeposit(int(p), int(target))

	def pprint(self):
		print("Partition:")
		print("==========")
		print("\n".join(["{:<20} {}".format(boxname, self.partition[boxname]) for boxname in self.partition]))
		print()
		print("Total: ", self.get_total())
		print()
		print("Goals:")
		print("=======")
		after_deposit = self.now.day >= 10
		print("\n".join(["{:<20} {:<10} {:<15} ({} monthly)".format(\
				boxname, \
				self.goals[boxname]['goal'], \
				self.goals[boxname]['due'].strftime('%Y-%m'), \
				self.goal_monthly_deposit(boxname, after_deposit), \
				) 
				for boxname in self.goals]))
		print()
		print("Periodic deposits:")
		print("==================")
		print("\n".join(["{:<20} {:<10} {:<15} ({} months left)".format(\
				boxname, \
				self.periodic[boxname].amount, \
				self.periodic[boxname].target, \
				self._periodic_months_left(boxname) if
					self.periodic[boxname].target != 0 else '∞', \
				)
				for boxname in self.periodic]))


	def dump_data(self):
		t = self.db_dir / (self.partition_path.name + '.new')
		with t.open('w') as fh:
			for boxname in self.partition:
				line = "{:<20} {}\n".format(boxname, self.partition[boxname])
				fh.write(line)
		t.replace(self.partition_path)

		if self.goals:
			t = self.db_dir / (self.goals_path.name + '.new')
			with t.open('w') as fh:
				for boxname in self.goals:
					line = "{:<20} {:<15} {}\n".format(\
							boxname, \
							self.goals[boxname]['goal'], \
							self.goals[boxname]['due'].strftime('%Y-%m') \
							)
					fh.write(line)
			t.replace(self.goals_path)

		if self.periodic:
			t = self.db_dir / (self.periodic_path.name + '.new')
			with t.open('w') as fh:
				for boxname in self.periodic:
					line = "{:<20} {:<10} {}\n".format(\
							boxname, \
							self.periodic[boxname].amount, \
							self.periodic[boxname].target, \
							)
					fh.write(line)
			t.replace(self.periodic_path)

	def get_total(self):
		amounts = [self.partition[boxname] for boxname in self.partition]
		return sum(amounts)

	def update_total(self, amount_change, monthly_update=True):
		self.partition['free'] += amount_change
		if monthly_update:
			self.partition['free'] += self.partition['credit']
			self.partition['credit'] = 0

	def spend(self, boxname, amount=0, credit=False):
		""" Unlock amount in box.
			credit == True means that the effect will take place in monthly update amount
			In this case, amount will be moved (unlocked) from box to speical box: credit
		"""
		if not(boxname in self.partition):
			raise KeyError(f"Key '{boxname}' is missing from partition (defined at '{self.partition_path}')")
		if not(amount):
			amount = self.partition[boxname]

		if amount > self.partition[boxname]:
			raise ValueError(f'Box values must be greater or equal to 0 (max reduction {self.partition[boxname]})')

		self.partition[boxname] -= amount # reduce amount from box
		if credit:
			self.partition['credit'] += amount

	def increase_box(self, boxname, amount):
		if not(boxname in self.partition):
			raise KeyError(f"Key '{boxname}' is missing from database ('{self.partition_path}')")
		if amount > self.partition['free']:
			raise ValueError(f"Trying to add amount larger than aviable at 'free' (free={self.partition['free']})")

		self.partition['free'] -= amount
		self.partition[boxname] += amount
	
	def box_to_box(self, from_box, to_box, amount):
		for boxname in [from_box, to_box]:
			if not(boxname in self.partition):
				raise KeyError(f"Key '{boxname}' is missing from database ('{self.partition_path}')")

		if amount > self.partition[from_box]:
			raise ValueError(f'Amount in source box not sufficiant (existing amount: {self.partition[from_box]})')

		self.partition[from_box] -= amount
		self.partition[to_box] += amount


	def new_box(self, boxname):
		""" Creates new box named <boxname>
		"""
		if boxname in self.partition:
			raise KeyError(f"Key '{boxname}' is already in database ('{self.partition_path}')")
		self.partition[boxname] = 0

	def remove_box(self, boxname):
		""" Remove box named <boxname>, put amount in 'free'
		"""
		if not(boxname in self.partition):
			raise KeyError(f"Key '{boxname}' is missing from database ('{self.partition_path}')")
		self.spend(boxname)
		del(self.partition[boxname])

		if boxname in self.goals:
			del(self.goals[boxname])

		if boxname in self.periodic:
			del(self.periodic[boxname])
	
	def new_loan(self, amount, due):
		""" Self loan- add negative sum box, add goal set to 0 to due date
		"""
		boxname = 'self-loan'
		if not(boxname in self.partition):
			self.new_box(boxname)

		self.partition[boxname] -= amount
		self.partition['free'] += amount
		self.set_goal(boxname, 0, due)
	
	#### goal methods
	def set_goal(self, boxname, goal, due):
		if not(boxname in self.partition):
			raise KeyError(f"Key '{boxname}' is missing from database ('{self.db_dir}')")
		due = datetime.strptime(due, '%Y-%m')
		self.goals[boxname] = {'goal': goal, 'due': due}

	def remove_goal(self, boxname):
		""" Remove 'boxname' from goals
		"""
		if not(boxname in self.goals):
			raise KeyError(f"Key '{boxname}' is missing from goals ('{self.goals_path}')")
		del(self.goals[boxname])
	
	def goal_monthly_deposit(self, boxname, after_monthly_deposit):
		goal = self.goals[boxname]['goal']
		due = self.goals[boxname]['due']
		curr_amount = self.partition[boxname]
		diff = due - self.now
		months_left = math.ceil(diff.days / 30)
		if after_monthly_deposit:
			months_left -= 1
		if months_left > 0:
			monthly = (goal - curr_amount) / months_left
		else: # months_left == 0
			monthly = goal - curr_amount
		monthly = int(monthly)
		if monthly < 0: # Goal is already reached
			monthly = 0
		return monthly
	
	#### peiodic methods
	def set_periodic(self, boxname, periodic_amount, target=0):
		if not(boxname in self.partition):
			raise KeyError(f"Key '{boxname}' is missing from database ('{self.db_dir}')")
		self.periodic[boxname] = PeriodicDeposit(periodic_amount, target)

	def remove_periodic(self, boxname):
		""" Remove 'boxname' from periodic deposits
		"""
		if not(boxname in self.periodic):
			raise KeyError(f"Key '{boxname}' is missing from periodic deposits ('{self.periodic_path}')")
		del(self.periodic[boxname])
	
	def _periodic_months_left(self, boxname):
		missing = self.periodic[boxname].target - self.partition[boxname]
		left = missing / self.periodic[boxname].amount
		left = math.ceil(left)
		return left


	#### Suggestion methods
	def suggest_deposits(self, skip='', additional_suggestion=False):
		""" Makes a suggestion for possible deposit that reflects the goals and periodic
		amounts that was set by user. Following suggestion assures reaching the goals on
		time.

		Params:
		skip (string):
			comma seperated boxnames that you want to avoid from putting into generated
			suggestion
		additional_suggestion (bool):
			'False' if this is the suggestion is meant to be used for the regular monthly
			deposit (for example, on the salary pay day). If called with 'True' this means
			that this suggestion is yet another one that comes after the regular deposit.
			This is important because the monthly deposit per goal needs to know how many
			months are left to reach the goal- this number should reflect the number of
			deposits left. Therefore if the regular deposit has taken place already, then
			there is one less deposit left so we need to take this into account on the
			claculations

		Return value: dictionary that maps boxname to amount that needs to be put in box.
		This dictionary can be fed into the method "apply_suggestion" if there is
		sufficient amount availabel in "free" and "credit"
		"""
		suggestion = {}
		skip = skip.split(',')
		for boxname in self.goals:
			if boxname in skip:
				continue
			box_suggestion = self.goal_monthly_deposit(boxname, additional_suggestion)
			if box_suggestion == 0: # Goal is already reached
				continue
			suggestion[boxname] = box_suggestion

		for boxname in self.periodic:
			if boxname in suggestion:
				raise KeyError(f"Key '{boxname}' appears in 'periodic' as well as in 'goals'")
			if boxname in skip:
				continue
			should_periodic = \
					self.periodic[boxname].target == 0 or \
					self.partition[boxname] < self.periodic[boxname].target
			if not(should_periodic):
				continue

			# Calculate how much should be added in this deposit
			if self.periodic[boxname].target == 0:
				suggestion[boxname] = self.periodic[boxname].amount
			elif (self.partition[boxname] + self.periodic[boxname].amount) < self.periodic[boxname].target:
				suggestion[boxname] = self.periodic[boxname].amount
			else: # Missing part is less than usual amount
				suggestion[boxname] = self.periodic[boxname].target - self.partition[boxname]
		return suggestion

	def apply_suggestion(self, suggestion):
		suggestion_sum = sum([suggestion[boxname] for boxname in suggestion])
		if suggestion_sum > self.partition['free']:
			missing = suggestion_sum - self.partition['free']
			raise ValueError(f"Cannot apply suggestion- missing {missing} in 'free'")
		for boxname in suggestion:
			if boxname not in self.partition:
				raise KeyError(f"Key '{boxname}' is missing from database ('{self.partition_path}')")
			self.increase_box(boxname, suggestion[boxname])
	
	# Suggestion for locking money
	def locked_amount(self, days_to_lock):
		today = datetime.now()
		touples = []
		for x in self.goals:
		    amount_got = self.partition[x]
		    due_date = self.goals[x]['due']
		    delta = due_date - today
		    days_left = delta.days
		    touples.append((amount_got, days_left))

		sorted_touples = sorted(touples, key=lambda x: x[1])
		locked_amount = 0
		for amount_got, days_left in sorted_touples:
			if days_left >= days_to_lock:
				locked_amount += amount_got
		return locked_amount


if __name__ == "__main__": ## DEBUG
	homedir = os.environ['HOME']
	DB = f"{homedir}/git/finance/partition-bp"
	fp = AmountPartition(DB)
	#print(fp.get_total())
	print(fp.locked_amount(1))
