#! /usr/bin/python3

from distutils.core import setup

setup(name='amount_partition',
	version='1.0',
	url='https://github.com/mromerdagan/amount-partition',
	maintainer='Omer Dagan',
	maintainer_email='mr.omer.dagan@gmail.com',
	packages=["amount_partition"],
	package_dir={"amount_partition": "python/amount_partition"},
)
