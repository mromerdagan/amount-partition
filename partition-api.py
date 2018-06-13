#!/usr/bin/python

import shutil
from collections import OrderedDict

DATA_FNAME = "/home/odagan/git/finance/partition-data/data"

class FinPartition(object):
	def __init__(self, data_fpath):
		self.data_fpath = data_fpath
		self.data = self.read_data(data_fpath)

	@staticmethod
	def read_data(fname):
		with open(fname) as fh:
			raw = fh.readlines()
		raw = map(lambda l: l.split('#')[0], raw) # remove comments
		raw = map(str.strip, raw)
		raw = filter(bool, raw) # remove empty lines
		data = OrderedDict()
		for line in raw:
			goal, amount = line.split()
			data[goal] = int(amount)
		return data

	def dump_data(self, fname=None):
		if not(fname):
			fname = self.data_fpath
		t = fname + '.new'
		with open(t, 'w') as fh:
			for goal in self.data:
				line = "{:<20} {}\n".format(goal, self.data[goal])
				fh.write(line)

		shutil.move(t, fname)

	def get_total(self):
		amounts = [amount for _, amount in self.data.items()]
		return sum(amounts)

	def withdraw_goal(self, goal, amount=0):
		""" Withdraw some or all amount of goal. Move it to 'free'
		    If need to remove completely, use reset_free()
		"""
		if not(goal in self.data):
			raise KeyError("Key '{}' is missing from database ('{}')".format(goal, self.data_fpath))

		if not(amount):
			amount = self.data[goal]
		self.data[goal] -= amount
		self.data['free'] += amount

	def add_to_goal(self, goal, amount):
		if not(goal in self.data):
			raise KeyError("Key '{}' is missing from database ('{}')".format(goal, self.data_fpath))
		if amount > self.data['free']:
			raise Exception("Trying to add amount larger than aviable at 'free'	(free={})".format(self.data['free']))

		self.data['free'] -= amount
		self.data[goal] += amount

	def deposit(self, amount):
		self.data['free'] += amount

	def reset_free(self):
		self.data['free'] = 0

if __name__ == "__main__":
	fp = FinPartition(DATA_FNAME)
	print(fp.get_total())
