#!/usr/bin/env python
# This script is part of 0export
# Copyright (C) 2008, Thomas Leonard
# See http://0install.net for details.
import os, sys

mydir = os.path.dirname(os.path.abspath(sys.argv[0]))
feeds_dir = os.path.join(mydir, 'feeds')

if not os.path.isdir(feeds_dir):
	print >>sys.stderr, "Directory %s not found." % feeds_dir
	print >>sys.stderr, "This script should be run from an unpacked setup.sh archive."
	print >>sys.stderr, "(are you trying to install 0export? you're in the wrong place!)"
	sys.exit(1)
