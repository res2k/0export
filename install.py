# This script is part of 0export
# Copyright (C) 2008, Thomas Leonard
# See http://0install.net for details.

# This file goes inside the generated setup.sh archive
# It runs or installs the program

import os, sys, subprocess
import shutil

mydir = os.path.dirname(os.path.abspath(sys.argv[0]))
zidir = os.path.join(mydir, 'zeroinstall')
sys.path.insert(0, zidir)
feeds_dir = os.path.join(mydir, 'feeds')
pypath = os.environ.get('PYTHONPATH')
if pypath:
	pypath = ':' + pypath
else:
	pypath = ''
os.environ['PYTHONPATH'] = zidir + pypath

from zeroinstall.injector import gpg, trust, qdom, iface_cache, policy, handler, model, namespaces
from zeroinstall.support import basedir
from zeroinstall import SafeException, zerostore
from zeroinstall.gtkui import xdgutils

import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

if not os.path.isdir(feeds_dir):
	print >>sys.stderr, "Directory %s not found." % feeds_dir
	print >>sys.stderr, "This script should be run from an unpacked setup.sh archive."
	print >>sys.stderr, "(are you trying to install 0export? you're in the wrong place!)"
	sys.exit(1)

def check_call(*args, **kwargs):
	exitstatus = subprocess.call(*args, **kwargs)
	if exitstatus != 0:
		raise SafeException("Command failed with exit code %d:\n%s" % (exitstatus, ' '.join(args[0])))

def do_install():
	# Step 1. Import GPG keys

	# Maybe GPG has never been run before. Let it initialse, or we'll get an error code
	# from the first import... (ignore return value here)
	subprocess.call(['gpg', '--check-trustdb'])

	key_dir = os.path.join(mydir, 'keys')
	for key in os.listdir(key_dir):
		check_call(['gpg', '--import', os.path.join(key_dir, key)])

	# Step 2. Import feeds and trust their signing keys
	for root, dirs, files in os.walk(os.path.join(mydir, 'feeds')):
		if 'latest.xml' in files:
			feed_path = os.path.join(root, 'latest.xml')
			icon_path = os.path.join(root, 'icon.png')

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

			if os.path.exists(icon_path):
				icons_cache = basedir.save_cache_path(namespaces.config_site, 'interface_icons')
				icon_file = os.path.join(icons_cache, model.escape(uri))
				if not os.path.exists(icon_file):
					shutil.copyfile(icon_path, icon_file)

	# Step 3. Solve to find out which implementations we actually need

	setup_store = zerostore.Store(os.path.join(mydir, 'implementations'))
	stores = iface_cache.iface_cache.stores

	h = handler.Handler()
	toplevel_uris = [uri.strip() for uri in file(os.path.join(mydir, 'toplevel_uris'))]
	for uri in toplevel_uris:
		# This is so the solver treats versions in the setup archive as 'cached',
		# meaning that it will prefer using them to doing a download
		stores.stores.append(setup_store)

		# Shouldn't need to download anything, but we might not have all feeds
		p = policy.Policy(uri, h)
		p.network_use = model.network_minimal
		download_feeds = p.solve_with_downloads()
		h.wait_for_blocker(download_feeds)
		assert p.ready

		# Add anything chosen from the setup store to the main store
		stores.stores.remove(setup_store)
		for iface, impl in p.get_uncached_implementations():
			print "Need to import", impl
			impl_src = os.path.join(mydir, 'implementations', impl.id)

			if os.path.isdir(impl_src):
				stores.add_dir_to_cache(impl.id, impl_src)
			else:
				print >>sys.stderr, "Required impl %s not present" % impl
	return toplevel_uris

def add_to_menu(uris):
	for uri in uris:
		iface = iface_cache.iface_cache.get_interface(uri)
		icon_path = iface_cache.iface_cache.get_icon_path(iface)

		feed_category = ''
		for meta in iface.get_metadata(namespaces.XMLNS_IFACE, 'category'):
			c = meta.content
			if '\n' in c:
				raise Exception("Invalid category '%s'" % c)
			feed_category = c
			break

		xdgutils.add_to_menu(iface, icon_path, feed_category)

def run(uri):
	print "Running program..."
	check_call([os.path.join(mydir, 'zeroinstall', '0launch'), '--offline', uri])
