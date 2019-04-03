
import math
from pathlib import Path
from datetime import datetime
from collections import OrderedDict

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
			raise FileNotFoundError("DB 'partition' file missing (searched '{}')".format(\
					self.partition_path))
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
			box, size = line.split()
			self.partition[box] = int(size)

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
			boxname, p = line.split()
			self.periodic[boxname] = int(p)

	def pprint(self):
		self.pretty_print()

	def pretty_print(self):
		print("\n".join(["{:<20} {}".format(box, self.partition[box]) for box in self.partition]))

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
					line = "{:<20} {}\n".format(\
							boxname, \
							self.periodic[boxname], \
							)
					fh.write(line)
			t.replace(self.periodic_path)

	def get_total(self):
		amounts = [self.partition[boxname] for boxname in self.partition]
		return sum(amounts)

	def deposit(self, amount):
		""" Same as increase_total() """
		self.increase_total(amount)

	def increase_total(self, amount):
		self.partition['free'] += amount

	def withdraw(self, amount=0):
		""" Same as reduce_total() """
		self.reduce_total(amount)

	def reduce_total(self, amount=0):
		if not(amount):
			self.partition['free'] = 0
		else:
			if amount > self.partition['free']:
				raise ValueError("'free' box must be greater or equal to 0 (max reduction: {})".format(self.partition['free']))
			self.partition['free'] -= amount

	def reduce_box(self, box, amount=0):
		""" Withdraw some or all amount of box. Move it to 'free'
		    If need to remove completely, use reset_free()
		"""
		if not(box in self.partition):
			raise KeyError("Key '{}' is missing from partition (defined at '{}')".format(box, self.data_fpath))
		if not(amount):
			amount = self.partition[box]

		if amount > self.partition[box]:
			raise ValueError('Box values must be greater or equal to 0 (max reduction {})'.format(self.partition[box]))
		self.partition[box] -= amount
		self.partition['free'] += amount

	def increase_box(self, box, amount):
		if not(box in self.partition):
			raise KeyError("Key '{}' is missing from database ('{}')".format(box, self.data_fpath))
		if amount > self.partition['free']:
			raise ValueError("Trying to add amount larger than aviable at 'free' (free={})".format(self.partition['free']))

		self.partition['free'] -= amount
		self.partition[box] += amount

	def new_box(self, boxname):
		""" Creates new box named <boxname>
		"""
		if boxname in self.partition:
			raise KeyError("Key '{}' is already in database ('{}')".format(boxname, self.data_fpath))
		self.partition[boxname] = 0

	def remove_box(self, boxname):
		""" Remove box named <boxname>, put amount in 'free'
		"""
		if not(boxname in self.partition):
			raise KeyError("Key '{}' is missing from database ('{}')".format(boxname, self.data_fpath))
		self.reduce_box(boxname)
		del(self.partition[boxname])

		if boxname in self.goals:
			del(self.goals[boxname])

		if boxname in self.periodic:
			del(self.periodic[boxname])
	
	def set_goal(self, boxname, goal, due):
		if not(boxname in self.partition):
			raise KeyError("Key '{}' is missing from database ('{}')".format(boxname, self.db_dir))
		self.goals[boxname] = {'goal': goal, 'due': due}

	def set_periodic(self, boxname, periodic_amount):
		if not(boxname in self.partition):
			raise KeyError("Key '{}' is missing from database ('{}')".format(boxname, self.db_dir))
		self.periodic[boxname] = periodic_amount

	def suggest_deposits(self, postpone=None):
		suggestion = {}
		now = datetime.now()
		for boxname in self.goals:
			if postpone and boxname in postpone:
				continue
			goal = self.goals[boxname]['goal']
			due = self.goals[boxname]['due']
			curr_amount = self.partition[boxname]
			diff = due - now
			months_left = math.ceil(diff.days / 30)
			box_suggestion = (goal - curr_amount) / months_left
			box_suggestion = int(box_suggestion)
			suggestion[boxname] = box_suggestion

		for boxname in self.periodic:
			if boxname in suggestion:
				raise KeyError("Key '{}' appears in 'periodic' as well as in 'goals'".format(\
						boxname))
			suggestion[boxname] = self.periodic[boxname]
		return suggestion

	def apply_suggestion(self, suggestion):
		suggestion_sum = sum([suggestion[box] for box in suggestion])
		if suggestion_sum > self.partition['free']:
			missing = suggestion_sum - self.partition['free']
			raise ValueError("Cannot apply suggestion- missing {} in 'free'".format(\
					missing))
		for boxname in suggestion:
			if boxname not in self.partition:
				raise KeyError("Key '{}' is missing from database ('{}')".format(
					boxname, self.data_fpath))
			self.increase_box(boxname, suggestion[boxname])

if __name__ == "__main__": ## DEBUG
	DB = "/home/odagan/git/finance/partition-data"
	fp = AmountPartition(DB)
	print(fp.get_total())
