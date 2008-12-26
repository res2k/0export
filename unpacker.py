import tempfile, sys, shutil, os, subprocess

def get_busy_pointer():
	# See http://mail.gnome.org/archives/gtk-list/2007-May/msg00100.html
	bit_data = "\
\x00\x00\x00\x00\x00\x00\x00\x00\x04\x00\x00\x00\
\x0c\x00\x00\x00\x1c\x00\x00\x00\x3c\x00\x00\x00\
\x7c\x00\x00\x00\xfc\x00\x00\x00\xfc\x01\x00\x00\
\xfc\x3b\x00\x00\x7c\x38\x00\x00\x6c\x54\x00\x00\
\xc4\xdc\x00\x00\xc0\x44\x00\x00\x80\x39\x00\x00\
\x80\x39\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\
\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\
\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\
\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\
\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\
\x00\x00\x00\x00\x00\x00\x00\x00"
	try:
		pix = gtk.gdk.bitmap_create_from_data(None, bit_data, 32, 32)
		color = gtk.gdk.Color()
		return gtk.gdk.Cursor(pix, pix, color, color, 2, 2)
	except:
		#old bug http://bugzilla.gnome.org/show_bug.cgi?id=103616
		return gtk.gdk.Cursor(gtk.gdk.WATCH)

tmp = tempfile.mkdtemp(prefix = '0export-')
try:
	print "Extracting..."
	try:
		import pygtk; pygtk.require('2.0')
		import gtk
		w = gtk.Window()
		w.set_position(gtk.WIN_POS_MOUSE)
		w.set_title('Unpacking... please wait...')
		w.set_default_size(400, 300)
		w.show()
		w.window.set_cursor(get_busy_pointer())
		gtk.gdk.flush()
		have_gui = True
	except Exception, ex:
		print "GTK not available; will use console install instead (%s)" % str(ex)
		have_gui = False
	self_stream = file(sys.argv[1], 'rb')
	self_stream.seek(int(sys.argv[2]))
	old_umask = os.umask(077)
	child = subprocess.Popen('bunzip2|tar xf -', shell = True, stdin = subprocess.PIPE, cwd = tmp)
	while True:
		data = self_stream.read(4096)
		if not data: break
		child.stdin.write(data)
	child.stdin.close()
	child.wait()
	if child.returncode:
		raise Exception("Failed to unpack archive (code %d)" % child.returncode)
	self_stream.close()
	sys.path.insert(0, tmp)
	sys.argv[0] = os.path.join(tmp, 'install.py')
	print "Running..."
	import install
finally:
	shutil.rmtree(tmp)
