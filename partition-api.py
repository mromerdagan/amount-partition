#!/usr/bin/python

import shutil
from collections import OrderedDict


class AmountPartition(object):
	def __init__(self, data_fpath):
		self.data_fpath = data_fpath
		self.partition = self.read_data(data_fpath)

	@staticmethod
	def read_data(fname):
		with open(fname) as fh:
			raw = fh.readlines()
		raw = map(lambda l: l.split('#')[0], raw) # remove comments
		raw = map(str.strip, raw)
		raw = filter(bool, raw) # remove empty lines
		partition = OrderedDict()
		for line in raw:
			box, size = line.split()
			partition[box] = int(size)
		return partition

	def pretty_print(self):
		print("\n".join(["{:<20} {}".format(box, self.partition[box]) for box in self.partition]))

	def dump_data(self, fname=None):
		if not(fname):
			fname = self.data_fpath
		t = fname + '.new'
		with open(t, 'w') as fh:
			for box in self.partition:
				line = "{:<20} {}\n".format(box, self.partition[box])
				fh.write(line)

		shutil.move(t, fname)

	def get_total(self):
		amounts = [amount for _, amount in self.partition.items()]
		return sum(amounts)

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

if __name__ == "__main__":
	DATA_FNAME = "/home/odagan/git/finance/partition-data/data"
	fp = AmountPartition(DATA_FNAME)
	print(fp.get_total())
