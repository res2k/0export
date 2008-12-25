import tempfile, sys, shutil, os, subprocess
tmp = tempfile.mkdtemp(prefix = '0export-')
try:
	print "Extracting..."
	self_stream = file(sys.argv[1], 'rb')
	self_stream.seek(int(sys.argv[2]))
	old_umask = os.umask(077)
	if subprocess.call('bunzip2|tar xf -', shell = True, stdin = self_stream, cwd = tmp):
		raise Exception("Failed to unpack archive")
	self_stream.close()
	sys.path.insert(0, tmp)
	sys.argv[0] = os.path.join(tmp, 'install.py')
	print "Running..."
	import install
finally:
	shutil.rmtree(tmp)
