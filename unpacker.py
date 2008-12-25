import tempfile, tarfile, sys, shutil, os
tmp = tempfile.mkdtemp(prefix = '0export-')
try:
	self_stream = file(sys.argv[1], 'rb')
	self_stream.seek(int(sys.argv[2]))
	ts = tarfile.open(sys.argv[1], 'r|bz2', self_stream)

	umask = os.umask(0)
	os.umask(umask)
	items = []
	for tarinfo in ts:
		tarinfo.mode = (tarinfo.mode | 0644) & ~umask
		ts.extract(tarinfo, tmp)
		if tarinfo.isdir():
			items.append(tarinfo)
	for tarinfo in items:
		path = os.path.join(tmp, tarinfo.name)
		os.utime(path, (tarinfo.mtime, tarinfo.mtime))

	ts.close()
	self_stream.close()
	sys.path.insert(0, tmp)
	sys.argv[0] = os.path.join(tmp, 'install.py')
	import install
finally:
	shutil.rmtree(tmp)
