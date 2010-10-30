import os, subprocess, shutil
from logging import info, warn

from zeroinstall import SafeException
from zeroinstall.injector import model, namespaces, gpg, iface_cache
from zeroinstall.support import basedir, find_in_path
from zeroinstall.zerostore import manifest

def escape_slashes(path):
	return path.replace('/', '#')

# From 0mirror
def get_feed_path(feed):
	if '#' in feed:
		raise SafeException("Invalid URL '%s'" % feed)
	scheme, rest = feed.split('://', 1)
	domain, rest = rest.split('/', 1)
	assert scheme in ('http', 'https', 'ftp')	# Just to check for mal-formed lines; add more as needed
	for x in [scheme, domain, rest]:
		if not x or x.startswith(','):
			raise SafeException("Invalid URL '%s'" % feed)
	return os.path.join('feeds', scheme, domain, escape_slashes(rest))

def get_gpg():
	return find_in_path('gpg') or find_in_path('gpg2')

def export_key(fingerprint, key_dir):
	key_path = os.path.join(key_dir, fingerprint[-16:] + '.gpg')
	child = subprocess.Popen([get_gpg(), '-a', '--export', fingerprint], stdout = subprocess.PIPE)
	keydata, unused = child.communicate()
	stream = file(key_path, 'w')
	stream.write(keydata)
	stream.close()
	info("Exported key %s", fingerprint)

class NoLocalVersions:
	def __init__(self, allow_package):
		self.allow_package = allow_package

	def meets_restriction(self, impl):
		if isinstance(impl, model.ZeroInstallImplementation):
			i = impl.id
			return not (i.startswith('/') or i.startswith('.'))
		# Accept package implementations to not deny ones that depend on it.
		# Package implementations will be excluded from produced bundle later.
		if impl.id.startswith('package:'):
			return self.allow_package
		return False

no_local = NoLocalVersions(True)
no_local_or_package = NoLocalVersions(False)

class NoLocalRestrictions(dict):
	def __init__(self, uris):
		self.uris = uris

	# This restriction applies to all interfaces, so ignore key
	def get(self, key, default):
		if key.uri in self.uris:
			return [no_local_or_package]
		else:
			return [no_local]

def export_feeds(export_dir, feeds, keys_used):
	"""Copy each feed (and icon) in feeds from the cache to export_dir.
	Add all signing key fingerprints to keys_used."""
	for feed in feeds:
		if feed.startswith('/'):
			info("Skipping local feed %s", feed)
			continue
		if feed.startswith('distribution:'):
			info("Skipping distribution feed %s", feed)
			continue
		print "Exporting feed", feed
		# Store feed
		cached = basedir.load_first_cache(namespaces.config_site,
						  'interfaces',
						  model.escape(feed))
		if cached:
			feed_dir = os.path.join(export_dir, get_feed_path(feed))
			feed_dst = os.path.join(feed_dir, 'latest.xml')
			if not os.path.isdir(feed_dir):
				os.makedirs(feed_dir)
			shutil.copyfile(cached, feed_dst)
			info("Exported feed %s", feed)

			icon_path = iface_cache.iface_cache.get_icon_path(iface_cache.iface_cache.get_interface(feed))
			if icon_path:
				icon_dst = os.path.join(feed_dir, 'icon.png')
				shutil.copyfile(icon_path, icon_dst)

			# Get the keys
			stream = file(cached)
			unused, sigs = gpg.check_stream(stream)
			stream.close()
			for x in sigs:
				if isinstance(x, gpg.ValidSig):
					keys_used.add(x.fingerprint)
				else:
					warn("Signature problem: %s" % x)
		else:
			warn("Feed not cached: %s", feed)

def get_implementation_path(impl):
	if impl.id.startswith('/'):
		return impl.id
	stores = iface_cache.iface_cache.stores
	if hasattr(stores, 'lookup_any'):
		# 0launch >= 0.45
		return stores.lookup_any(impl.digests)
	return stores.lookup(impl.id)

# impls is a map {digest: Implementation}. Create an exported item called
# "digest" with the cached implemention (even if we cached it under a different
# digest).
def export_impls(export_dir, impls):
	implementations = os.path.join(export_dir, 'implementations')
	for digest, impl in impls.iteritems():
		print "Exporting implementation %s (%s %s)" % (impl, impl.feed.get_name(), impl.get_version())
		# Store implementation
		src = get_implementation_path(impl)
		dst = os.path.join(implementations, digest)
		shutil.copytree(src, dst, symlinks = True)

		# Regenerate the manifest, because it might be for a different algorithm
		os.chmod(dst, 0755)
		os.unlink(os.path.join(dst, '.manifest'))
		alg_name, required_value = digest.split('=', 1)
		alg = manifest.algorithms[alg_name]
		actual = manifest.add_manifest_file(dst, alg).hexdigest()
		assert actual == required_value, "Expected digest '%s', but found '%s'" % (required_value, actual)

		for root, dirs, files in os.walk(dst):
			os.chmod(root, 0755)
		os.unlink(os.path.join(dst, '.manifest'))
		info("Exported implementation %s", impl)
