import tempfile, sys, shutil, os, subprocess, gobject, tarfile

INSTALLER_MODE = @INSTALLER_MODE@

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
	installer = None
	print "Extracting bootstrap data..."
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
		actions_vbox.pack_start(label, False, True, 0)

		if subprocess.call('which xdg-desktop-menu',
				shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT):
			add_to_menu_option = gtk.CheckButton('(no xdg-desktop-menu command;\n'
				'to add menu items, install xdg-utils first)')
			actions_vbox.pack_start(add_to_menu_option, False, True, 0)
			add_to_menu_option.set_active(False)
			add_to_menu_option.set_sensitive(False)
		else:
			add_to_menu_option = gtk.CheckButton('Add to menu')
			actions_vbox.pack_start(add_to_menu_option, False, True, 0)
			add_to_menu_option.set_active(True)

		run_option = gtk.CheckButton('Run program')
		run_option.set_active(True)
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
			if installer:
				installer.abort()
			sys.exit(1)
		response_handler = w.connect('response', response)
	except Exception, ex:
		print "GTK not available; will use console install instead (%s)" % str(ex)
	self_stream = file(sys.argv[1], 'rb')
	archive_offset = int(sys.argv[2])
	self_stream.seek(archive_offset)
	old_umask = os.umask(077)
	mainloop = gobject.MainLoop(gobject.main_context_default())
	archive = tarfile.open(name=self_stream.name, mode='r|',
            fileobj=self_stream)

	# Extract the bootstrap data (interfaces, 0install itself)
	bootstrap_stream = None
	for tarmember in archive:
		if tarmember.name == 'bootstrap.tar.bz2':
			bootstrap_stream = archive.extractfile(tarmember)
			break
	else:
		raise Exception("No bootstrap data in archive (broken?)")

	bootstrap_tar = tarfile.open(name=bootstrap_stream.name, mode='r|bz2',
            fileobj=bootstrap_stream)
	umask = os.umask(0)
	os.umask(umask)
	items = []
	for tarinfo in bootstrap_tar:
		tarinfo.mode = (tarinfo.mode | 0644) & ~umask
		bootstrap_tar.extract(tarinfo, tmp)
		if tarinfo.isdir():
			items.append(tarinfo)
	for tarinfo in items:
		path = os.path.join(tmp, tarinfo.name)
		os.utime(path, (tarinfo.mtime, tarinfo.mtime))
	bootstrap_tar.close()
	bootstrap_stream.close()
	archive.close()

	# Stop Python adding .pyc files
	for root, dirs, files in os.walk(os.path.join(tmp, 'zeroinstall')):
		os.chmod(root, 0500)

	sys.path.insert(0, tmp)
	sys.argv[0] = os.path.join(tmp, 'install.py')

	print "Installing..."
	import install
	installer = install.Installer()
	toplevel_uris = installer.do_install(self_stream, progress_bar, archive_offset)
	self_stream.close()

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
	install.run(toplevel_uris[0], not INSTALLER_MODE and ['--offline'] or [])
elif INSTALLER_MODE:
	print "Downloading..."
	install.run(toplevel_uris[0], ['--download-only'])
