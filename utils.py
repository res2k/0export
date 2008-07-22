import os, subprocess, shutil
from logging import info

from zeroinstall import SafeException
from zeroinstall.injector import model, namespaces, gpg
from zeroinstall.support import basedir
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

def export_key(fingerprint, key_dir):
	key_path = os.path.join(key_dir, fingerprint[-16:] + '.gpg')
	child = subprocess.Popen(['gpg', '-a', '--export', fingerprint], stdout = subprocess.PIPE)
	keydata, unused = child.communicate()
	stream = file(key_path, 'w')
	stream.write(keydata)
	stream.close()
	info("Exported key %s", fingerprint)

class NoLocalVersions:
	def meets_restriction(self, impl):
		if isinstance(impl, model.ZeroInstallImplementation):
			i = impl.id
			return not (i.startswith('/') or i.startswith('.'))
		# Should package impls be OK?
		return False

no_local = NoLocalVersions()

class NoLocalRestrictions(dict):
	# This restriction applies to all interfaces, so ignore key
	def get(self, key, default):
		return [no_local]

def export_feeds(export_dir, feeds, keys_used):
	"""Copy each feed in feeds from the cache to export_dir.
	Add all signing key fingerprints to keys_used."""
	for feed in feeds:
		if feed.startswith('/'):
			info("Skipping local feed %s", feed)
			continue
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

def export_impls(export_dir, policy, impls):
	implementations = os.path.join(export_dir, 'implementations')
	for impl in impls:
		# Store implementation
		src = policy.get_implementation_path(impl)
		dst = os.path.join(implementations, impl.id)
		shutil.copytree(src, dst)
		manifest.verify(dst, impl.id)
		for root, dirs, files in os.walk(dst):
			os.chmod(root, 0755)
		os.unlink(os.path.join(dst, '.manifest'))
		info("Exported implementation %s (%s %s)", impl.id, impl.feed.get_name(), impl.get_version())
