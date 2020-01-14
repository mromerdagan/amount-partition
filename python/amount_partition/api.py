
import os
import math
from pathlib import Path
from datetime import datetime
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

		if not(self.partition_path.exists()):
			raise FileNotFoundError(\
					f"DB 'partition' file missing (searched '{self.partition_path}')")
		self.setup()

	def setup(self):
		self.read_partition()
		self.read_goals()
		self.read_periodic()

	def read_partition(self):
		raw = self.partition_path.read_text()
		lines = extract_lines(raw)
		self.partition = OrderedDict()
		for line in lines:
			boxname, size = line.split()
			self.partition[boxname] = int(size)

	def read_goals(self):
		self.goals = OrderedDict()
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
		self.periodic = OrderedDict()
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
		print("\n".join(["{:<20} {:<10} {}".format(\
				boxname, \
				self.goals[boxname]['goal'], \
				self.goals[boxname]['due'].strftime('%Y-%m'), \
				) 
				for boxname in self.goals]))
		print()
		print("Periodic deposits:")
		print("==================")
		print("\n".join(["{:<20} {:<10} {}".format(\
				boxname, \
				self.periodic[boxname].amount, \
				self.periodic[boxname].target) \
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

	def deposit(self, amount):
		self.partition['free'] += amount

	def withdraw(self, amount=0):
		if not(amount):
			self.partition['free'] = 0
		else:
			if amount > self.partition['free']:
				raise ValueError("'free' box must be greater or equal to 0 (max reduction: {})".format(self.partition['free']))
			self.partition['free'] -= amount

	def reduce_box(self, boxname, amount=0):
		""" Withdraw some or all amount of box. Move it to 'free'
		    If need to remove completely, use reset_free()
		"""
		if not(boxname in self.partition):
			raise KeyError(f"Key '{boxname}' is missing from partition (defined at '{self.partition_path}')")
		if not(amount):
			amount = self.partition[boxname]

		if amount > self.partition[boxname]:
			raise ValueError(f'Box values must be greater or equal to 0 (max reduction {self.partition[boxname]})')
		self.partition[boxname] -= amount
		self.partition['free'] += amount

	def increase_box(self, boxname, amount):
		if not(boxname in self.partition):
			raise KeyError(f"Key '{boxname}' is missing from database ('{self.partition_path}')")
		if amount > self.partition['free']:
			raise ValueError(f"Trying to add amount larger than aviable at 'free' (free={self.partition['free']})")

		self.partition['free'] -= amount
		self.partition[boxname] += amount

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
		self.reduce_box(boxname)
		del(self.partition[boxname])

		if boxname in self.goals:
			del(self.goals[boxname])

		if boxname in self.periodic:
			del(self.periodic[boxname])
	
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

	#### Suggestion methods
	def suggest_deposits(self, skip=''):
		suggestion = {}
		now = datetime.now()
		skip = skip.split(',')
		for boxname in self.goals:
			if boxname in skip:
				continue
			goal = self.goals[boxname]['goal']
			due = self.goals[boxname]['due']
			curr_amount = self.partition[boxname]
			diff = due - now
			months_left = math.ceil(diff.days / 30)
			if months_left > 0:
				box_suggestion = (goal - curr_amount) / months_left
			else: # months_left == 0
				box_suggestion = goal - curr_amount
			box_suggestion = int(box_suggestion)
			if box_suggestion <= 0: # Goal is already reached
				continue
			suggestion[boxname] = box_suggestion

		for boxname in self.periodic:
			if boxname in suggestion:
				raise KeyError(f"Key '{boxname}' appears in 'periodic' as well as in 'goals'")
			if boxname in skip:
				continue
			should_periodic = \
					self.periodic[boxname].target == 0 or \
					self.partition[boxname] <= self.periodic[boxname].target
			if not(should_periodic):
				continue
			suggestion[boxname] = self.periodic[boxname].amount
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

if __name__ == "__main__": ## DEBUG
	homedir = os.environ['HOME']
	DB = f"{homedir}/git/finance/partition-data"
	fp = AmountPartition(DB)
	print(fp.get_total())
