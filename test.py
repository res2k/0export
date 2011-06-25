#!/usr/bin/env python
import sys, tempfile, os, shutil, tempfile, subprocess
from StringIO import StringIO
import unittest

zeroinstall_dir = os.environ.get('0EXPORT_ZEROINSTALL', None)
if zeroinstall_dir:
	sys.path.insert(1, zeroinstall_dir)

from zeroinstall.support import ro_rmtree

my_dir = os.path.dirname(os.path.abspath(__file__))

export_bin = os.path.join(my_dir, '0export')

PUBLISH_URI = 'http://0install.net/2006/interfaces/0publish'

class TestCompile(unittest.TestCase):
	def setUp(self):
		os.chdir('/')
		self.tmpdir = tempfile.mkdtemp(prefix = '0export-test-')

		# tmpdir is used as $HOME when running the bundle...
		config_dir = os.path.join(self.tmpdir, '.config', '0install.net', 'injector')
		os.makedirs(config_dir)
		stream = open(os.path.join(config_dir, 'global'), 'w')
		stream.write('[global]\n'
				'freshness = -1\n'
				'help_with_testing = False\n'
				'network_use = off-line\n')
		stream.close()

	def tearDown(self):
		ro_rmtree(self.tmpdir)

	def testSimple(self):
		setup_sh = os.path.join(self.tmpdir, 'setup.sh')
		print export_bin
		subprocess.check_call([export_bin, setup_sh, PUBLISH_URI])

		env = {
			'HOME': self.tmpdir,
			'http_proxy' : 'localhost:1111' 	# Detect accidental network access
		}

		child = subprocess.Popen([setup_sh, '--help'], env = env, stdout = subprocess.PIPE)
		cout, unused = child.communicate()
		assert child.wait() == 0
		assert 'Run self-extracting installer' in cout

		child = subprocess.Popen([setup_sh, '--', '--help'], env = env, stdout = subprocess.PIPE)
		cout, unused = child.communicate()
		assert child.wait() == 0
		assert '--xmlsign' in cout

suite = unittest.makeSuite(TestCompile)
if __name__ == '__main__':
	unittest.main()
