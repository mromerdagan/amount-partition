from pathlib import Path
from collections import OrderedDict

class AmountPartition(object):
	def __init__(self, db_dir):
		self.db_dir = Path(db_dir)
		self.partition_path = self.db_dir / 'partition'

		if not(self.partition_path.exists()):
			raise FileNotFoundError("DB 'partition' file missing (searched '{}')".format(\
					self.partition_path))
		self.setup()

	def setup(self):
		self.read_partition()

	def read_partition(self):
		raw = self.partition_path.read_text()
		lines = raw.split('\n')
		lines = [l.split('#')[0] for l in lines] # remove comments
		lines = [l.strip() for l in lines]
		lines = [l for l in lines if l] # remove empty lines
		self.partition = OrderedDict()
		for line in lines:
			box, size = line.split()
			self.partition[box] = int(size)

	def pprint(self):
		self.pretty_print()

	def pretty_print(self):
		print("\n".join(["{:<20} {}".format(box, self.partition[box]) for box in self.partition]))

	def dump_data(self):
		t = self.db_dir / (self.partition_path.name + '.new')
		with t.open('w') as fh:
			for box in self.partition:
				line = "{:<20} {}\n".format(box, self.partition[box])
				fh.write(line)
		t.replace(self.partition_path)

	def get_total(self):
		amounts = [self.partition[boxname] for boxname in self.partition]
		return sum(amounts)

	def deposit(self, amount):
		""" Same as increase_total() """
		self.increase_total(amount)

	def increase_total(self, amount):
		self.partition['free'] += amount

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
			raise ValueError("Key '{}' is already in database ('{}')".format(boxname, self.data_fpath))
		self.partition[boxname] = 0

	def remove_box(self, boxname):
		""" Remove box named <boxname>, put amount in 'free'
		"""
		if not(boxname in self.partition):
			raise ValueError("Key '{}' is missing from database ('{}')".format(boxname, self.data_fpath))
		self.reduce_box(boxname)
		del(self.partition[boxname])

if __name__ == "__main__":
	DB = "/home/odagan/git/finance/partition-data"
	fp = AmountPartition(DB)
	print(fp.get_total())
