import tempfile, sys, shutil, os, subprocess, gobject, signal

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
	w = None
	progress_bar = None
	print "Extracting..."
	try:
		import pygtk; pygtk.require('2.0')
		import gtk
		if gtk.gdk.get_display() is None:
			raise Exception("Failed to open display")
		w = gtk.Dialog(title = "Zero Install")

		w.set_resizable(False)
		w.set_has_separator(False)
		w.vbox.set_border_width(4)
		hbox = gtk.HBox(False, 12)
		hbox.set_border_width(5)
		image = gtk.image_new_from_stock(gtk.STOCK_DIALOG_INFO, gtk.ICON_SIZE_DIALOG)
		image.set_alignment(0.5, 0.5)

		message_vbox = gtk.VBox(False, 12)
		message_vbox.pack_start(gtk.Label('The software is being unpacked. Please wait...'), True, True)
		message_vbox.set_border_width(12)

		progress_bar = gtk.ProgressBar()
		message_vbox.add(progress_bar)

		actions_vbox = gtk.VBox(False, 4)
		label = gtk.Label('Actions:')
		label.set_alignment(0, 0.5)
		add_to_menu_option = gtk.CheckButton('Add to menu')
		add_to_menu_option.set_active(True)
		run_option = gtk.CheckButton('Run program')
		run_option.set_active(True)
		actions_vbox.pack_start(label, False, True, 0)
		actions_vbox.pack_start(add_to_menu_option, False, True, 0)
		actions_vbox.pack_start(run_option, False, True, 0)

		def update_sensitive(option):
			w.set_response_sensitive(gtk.RESPONSE_OK,
				add_to_menu_option.get_active() or run_option.get_active())
		add_to_menu_option.connect('toggled', update_sensitive)
		run_option.connect('toggled', update_sensitive)

		notebook = gtk.Notebook()
		notebook.set_show_tabs(False)
		notebook.set_show_border(False)
		notebook.append_page(message_vbox, None)
		notebook.append_page(actions_vbox, None)

		hbox.pack_start(image, False, False, 0)
		hbox.pack_start(notebook, True, True)
		w.vbox.pack_start(hbox, False, False, 0)
		cancel_button = w.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
		cancel_button.unset_flags(gtk.CAN_DEFAULT)
		ok_button = w.add_button(gtk.STOCK_OK, gtk.RESPONSE_OK)
		w.set_response_sensitive(gtk.RESPONSE_OK, False)
		w.set_position(gtk.WIN_POS_MOUSE)
		w.set_title('Zero Install')
		w.set_default_size(400, 300)
		w.show()
		w.window.set_cursor(get_busy_pointer())
		gtk.gdk.flush()
		w.vbox.show_all()
		def response(w, resp):
			print >>sys.stderr, "Cancelled at user's request"
			os.kill(child.pid, signal.SIGTERM)
			child.wait()
			sys.exit(1)
		response_handler = w.connect('response', response)
	except Exception, ex:
		print "GTK not available; will use console install instead (%s)" % str(ex)
	self_stream = file(sys.argv[1], 'rb')
	archive_offset = int(sys.argv[2])
	self_stream.seek(archive_offset)
	archive_size = os.path.getsize(sys.argv[1]) - archive_offset
	old_umask = os.umask(077)
	child = subprocess.Popen('bunzip2|tar xf -', shell = True, stdin = subprocess.PIPE, cwd = tmp)
	sent = 0
	mainloop = gobject.MainLoop(gobject.main_context_default())

	def pipe_ready(src, cond):
		global sent
		data = self_stream.read(4096)
		if not data:
			mainloop.quit()
			child.stdin.close()
			return False
		sent += len(data)
		if progress_bar:
			progress_bar.set_fraction(float(sent) / archive_size)
		child.stdin.write(data)
		return True
	gobject.io_add_watch(child.stdin, gobject.IO_OUT | gobject.IO_HUP, pipe_ready)

	mainloop.run()

	child.wait()
	if child.returncode:
		raise Exception("Failed to unpack archive (code %d)" % child.returncode)
	self_stream.close()

	# Stop Python adding .pyc files
	for root, dirs, files in os.walk(os.path.join(tmp, 'zeroinstall')):
		print root
		os.chmod(root, 0500)

	sys.path.insert(0, tmp)
	sys.argv[0] = os.path.join(tmp, 'install.py')

	print "Installing..."
	import install
	toplevel_uris = install.do_install()

	if w:
		notebook.next_page()
		w.disconnect(response_handler)
		w.window.set_cursor(None)
		w.set_response_sensitive(gtk.RESPONSE_OK, True)
		ok_button.grab_focus()
		resp = w.run()

		w.destroy()
		gtk.gdk.flush()

		if resp != gtk.RESPONSE_OK:
			raise Exception("Cancelled at user's request")

		if add_to_menu_option.get_active():
			install.add_to_menu(toplevel_uris)
finally:
	print "Removing temporary files..."
	for root, dirs, files in os.walk(os.path.join(tmp, 'zeroinstall')):
		os.chmod(root, 0700)
	shutil.rmtree(tmp)

if w is None or run_option.get_active():
	print "Running..."
	install.run(toplevel_uris[0])
