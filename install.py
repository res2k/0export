#!/usr/bin/env python
# This script is part of 0export
# Copyright (C) 2008, Thomas Leonard
# See http://0install.net for details.

# This file goes inside the generated setup.sh archive
# It runs or installs the program

import os, sys, subprocess
from zeroinstall.injector import gpg, trust, qdom, iface_cache, policy, handler

mydir = os.path.dirname(os.path.abspath(sys.argv[0]))
feeds_dir = os.path.join(mydir, 'feeds')

if not os.path.isdir(feeds_dir):
	print >>sys.stderr, "Directory %s not found." % feeds_dir
	print >>sys.stderr, "This script should be run from an unpacked setup.sh archive."
	print >>sys.stderr, "(are you trying to install 0export? you're in the wrong place!)"
	sys.exit(1)

def check_call(*args, **kwargs):
	exitstatus = subprocess.call(*args, **kwargs)
	if exitstatus != 0:
		raise SafeException("Command failed with exit code %d:\n%s" % (exitstatus, ' '.join(args)))

# Step 1. Import GPG keys

key_dir = os.path.join(mydir, 'keys')
for key in os.listdir(key_dir):
	check_call(['gpg', '--import', os.path.join(key_dir, key)])

# Step 2. Import feeds and trust their signing keys
for root, dirs, files in os.walk(os.path.join(mydir, 'feeds')):
	if 'latest.xml' in files:
		feed_path = os.path.join(root, 'latest.xml')

		# Get URI
		feed_stream = file(feed_path)
		doc = qdom.parse(feed_stream)
		uri = doc.getAttribute('uri')
		assert uri, "Missing 'uri' attribute on root element in '%s'" % feed_path
		domain = trust.domain_from_url(uri)

		feed_stream.seek(0)
		stream, sigs = gpg.check_stream(feed_stream)
		for s in sigs:
			if not trust.trust_db.is_trusted(s.fingerprint, domain):
				print "Adding key %s to trusted list for %s" % (s.fingerprint, domain)
				trust.trust_db.trust_key(s.fingerprint, domain)
		oldest_sig = min([s.get_timestamp() for s in sigs])
		iface = iface_cache.iface_cache.get_interface(uri)
		try:
			iface_cache.iface_cache.update_interface_from_network(iface, stream.read(), oldest_sig)
		except iface_cache.ReplayAttack:
			# OK, the user has a newer copy already
			pass
		if feed_stream != stream:
			feed_stream.close()
		stream.close()

# Step 3. Solve to find out which implementations we actually need

h = handler.Handler()
for uri in file(os.path.join(mydir, 'toplevel_uris')):
	# Shouldn't need to download anything, but we might not have all feeds
	p = policy.Policy(uri, h)
	download_feeds = p.solve_with_downloads()
	h.wait_for_blocker(download_feeds)
	assert p.ready
	stores = iface_cache.iface_cache.stores
	for iface, impl in p.get_uncached_implementations():
		print "Need to import", impl
		impl_src = os.path.join(mydir, 'implementations', impl.id)
		if os.path.isdir(impl_src):
			stores.add_dir_to_cache(impl.id, impl_src)
		else:
			print >>sys.stderr, "Required impl %s not present" % impl
	check_call(['0launch', uri])
