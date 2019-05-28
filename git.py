import os
import subprocess
import re
import logging
import fnmatch

logger = logging.getLogger(__name__)

def git_cmd(args, multiline=False, supress_stderr=False):
	fh = open(os.devnull, 'w') if supress_stderr else None
	args = 'git ' + args
	p = subprocess.Popen(args.split(), stdout=subprocess.PIPE, stderr=fh)
	details = p.stdout.read()
	details = details.decode('utf-8', 'replace').strip()
	if multiline:
		details = details.split('\n') # Get output as lines
	if fh:
		fh.close()
	return details

def get_config_key(key, default):
	if not(hasattr(get_config_key, 'config')):
		raw_config = git_cmd('config --list', multiline=True)
		get_config_key.config = {
			key:val for key, val in [line.split('=', maxsplit=1) for line in raw_config]
		}
	return get_config_key.config.get(key, default)

def get_tags():
	tags = git_cmd('tag', multiline=True)
	return tags

