#    Back In Time
#    Copyright (C) 2008 Oprea Dan
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with this program; if not, write to the Free Software Foundation, Inc.,
#    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.


import os
import os.path
import sys
import pygtk
pygtk.require("2.0")
import gtk
import gnomevfs
import gobject
import gtk.glade
import datetime
import gettext

import config
import gnomeclipboardtools 
import gnomemessagebox


_=gettext.gettext


class SnapshotsDialog:
	def __init__( self, snapshots, glade, path, snapshots_list, current_snapshot_id, icon_name ):
		self.snapshots = snapshots
		self.config = snapshots.config
		self.glade = glade

		self.path = path
		self.snapshots_list = snapshots_list
		self.current_snapshot_id = current_snapshot_id
		self.icon_name = icon_name

		self.dialog = self.glade.get_widget( 'SnapshotsDialog' )

		signals = { 
			'on_list_snapshots_cursor_changed' : self.on_list_snapshots_cursor_changed,
			'on_list_snapshots_row_activated' : self.on_list_snapshots_row_activated,
			'on_list_snapshots_popup_menu' : self.on_list_snapshots_popup_menu,
			'on_list_snapshots_button_press_event': self.on_list_snapshots_button_press_event,
			'on_list_snapshots_drag_data_get': self.on_list_snapshots_drag_data_get,
			'on_btnDiffWith_clicked' : self.on_btnDiffWith_clicked,
			'on_btnCopySnapshot_clicked' : self.on_btnCopySnapshot_clicked,
			'on_btnRestoreSnapshot_clicked' : self.on_btnRestoreSnapshot_clicked
			}

		self.glade.signal_autoconnect( signals )
		
		#path
		self.editPath = self.glade.get_widget( 'editPath' )

		#diff
		self.edit_diff_cmd = self.glade.get_widget( 'editDiffCmd' )
		self.edit_diff_cmd_params = self.glade.get_widget( 'editDiffCmdParams' )

		diff_cmd = self.config.get_str_value( 'gnome.diff.cmd', 'meld' )
		diff_cmd_params = self.config.get_str_value( 'gnome.diff.param', '%1 %2' )

		self.edit_diff_cmd.set_text( diff_cmd )
		self.edit_diff_cmd_params.set_text( diff_cmd_params )

		#setup backup folders
		self.list_snapshots = self.glade.get_widget( 'list_snapshots' )
		self.list_snapshots.drag_source_set( gtk.gdk.BUTTON1_MASK | gtk.gdk.BUTTON3_MASK, gtk.target_list_add_uri_targets(), gtk.gdk.ACTION_COPY )

		init_all = self.list_snapshots.get_model() is None

		if initAll:
			text_renderer = gtk.CellRendererText()
			column = gtk.TreeViewColumn( _('Snapshots') )
			column.pack_end( text_renderer, True )
			column.add_attribute( text_renderer, 'markup', 0 )
			column.set_sort_column_id( 0 )
			self.list_snapshots.append_column( column )

			#display name, snapshot_id
			self.store_snapshots = gtk.ListStore( str, str )
			self.list_snapshots.set_model( self.store_snapshots )
		else:
			self.store_snapshots = self.list_snapshots.get_model()

		self.store_snapshots.set_sort_column_id( 0, gtk.SORT_DESCENDING )

		#setup diff with combo
		self.combo_diff_with = self.glade.get_widget( 'comboDiffWith' )
		if initAll:
			text_renderer = gtk.CellRendererText()
			self.combo_diff_with.pack_start( text_renderer, True )
			self.combo_diff_with.add_attribute( text_renderer, 'text', 0 )
			self.combo_diff_with.set_model( self.store_snapshots ) #use the same store

		#update snapshots
		self.update_snapshots()

	def update_toolbar( self ):
		if len( self.store_snapshots ) <= 0:
			self.glade.get_widget( 'btnCopySnapshot' ).set_sensitive( False )
			self.glade.get_widget( 'btnRestoreSnapshot' ).set_sensitive( False )
		else:
			self.glade.get_widget( 'btnCopySnapshot' ).set_sensitive( True )

			iter = self.list_snapshots.get_selection().get_selected()[1]
			if iter is None:
				self.glade.get_widget( 'btnRestoreSnapshot' ).set_sensitive( False )
			else:
				path = self.store_snapshots.get_value( iter, 1 )
				self.glade.get_widget( 'btnRestoreSnapshot' ).set_sensitive( len( path ) > 1 )

	def on_btnRestoreSnapshot_clicked( self, button ):
		iter = self.list_snapshots.get_selection().get_selected()[1]
		if not iter is None:
			self.glade.get_widget('btnRestoreSnapshot').set_sensitive( False )
			gobject.timeout_add( 100, self.restore_ )

	def restore_( self ):
		iter = self.list_snapshots.get_selection().get_selected()[1]
		if not iter is None:
			self.backup.restore( self.store_snapshots.get_value( iter, 1 ), self.path )

		self.glade.get_widget( 'btnRestoreSnapshot' ).set_sensitive( True )
		return False

	def on_btnCopySnapshot_clicked( self, button ):
		iter = self.list_snapshots.get_selection().get_selected()[1]
		if not iter is None:
			path = self.store_snapshots.get_value( iter, 2 )
			gnomeclipboardtools.clipboard_copy_path( path )
 
	def on_list_snapshots_drag_data_get( self, widget, drag_context, selection_data, info, timestamp, user_param1 = None ):
		iter = self.list_snapshots.get_selection().get_selected()[1]
		if not iter is None:
			path = self.store_snapshots.get_value( iter, 2 )
			path = gnomevfs.escape_path_string(path)
			selection_data.set_uris( [ 'file://' + path ] )

	def on_list_snapshots_cursor_changed( self, list ):
		self.updateToolbar()

	def on_list_snapshots_button_press_event( self, list, event ):
		if event.button != 3:
			return

		if len( self.store_snapshots ) <= 0:
			return

		path = self.list_snapshots.get_path_at_pos( int( event.x ), int( event.y ) )
		if path is None:
			return
		path = path[0]
	
		self.list_snapshots.get_selection().select_path( path )
		self.updateToolbar()
		self.showPopupMenu( self.list_snapshots, event.button, event.time )

	def on_list_snapshots_popup_menu( self, list ):
		self.showPopupMenu( list, 1, gtk.get_current_event_time() )

	def show_popup_menu( self, list, button, time ):
		iter = list.get_selection().get_selected()[1]
		if iter is None:
			return

		#print "popup-menu"
		self.popup_menu = gtk.Menu()

		menuItem = gtk.ImageMenuItem( 'backintime.open' )
		menuItem.set_image( gtk.image_new_from_icon_name( self.icon_name, gtk.ICON_SIZE_MENU ) )
		menuItem.connect( 'activate', self.on_list_snapshots_open_item )
		self.popupMenu.append( menuItem )

		self.popupMenu.append( gtk.SeparatorMenuItem() )

		menuItem = gtk.ImageMenuItem( 'backintime.copy' )
		menuItem.set_image( gtk.image_new_from_stock( gtk.STOCK_COPY, gtk.ICON_SIZE_MENU ) )
		menuItem.connect( 'activate', self.on_list_snapshots_copy_item )
		self.popupMenu.append( menuItem )

		menuItem = gtk.ImageMenuItem( gtk.STOCK_JUMP_TO )
		menuItem.connect( 'activate', self.on_list_snapshots_jumpto_item )
		self.popupMenu.append( menuItem )

		path = self.store_snapshots.get_value( iter, 1 )
		if len( path ) > 1:
			menuItem = gtk.ImageMenuItem( 'backintime.restore' )
			menuItem.set_image( gtk.image_new_from_stock( gtk.STOCK_UNDELETE, gtk.ICON_SIZE_MENU ) )
			menuItem.connect( 'activate', self.on_list_snapshots_restore_item )
			self.popupMenu.append( menuItem )

		self.popupMenu.append( gtk.SeparatorMenuItem() )

		menuItem = gtk.ImageMenuItem( 'backintime.diff' )
		#menuItem.set_image( gtk.image_new_from_stock( gtk.STOCK_COPY, gtk.ICON_SIZE_MENU ) )
		menuItem.connect( 'activate', self.on_list_snapshots_diff_item )
		self.popupMenu.append( menuItem )

		self.popupMenu.show_all()
		self.popupMenu.popup( None, None, None, button, time )

	def on_list_snapshots_diff_item( self, widget, data = None ):
		self.on_btnDiffWith_clicked( self.glade.get_widget( 'btnDiffWith' ) )

	def on_list_snapshots_jumpto_item( self, widget, data = None ):
		self.dialog.response( gtk.RESPONSE_OK )

	def on_list_snapshots_open_item( self, widget, data = None ):
		self.open_item()

	def on_list_snapshots_restore_item( self, widget, data = None ):
		self.on_btnRestoreSnapshot_clicked( self.glade.get_widget( 'btnRestoreSnapshot' ) )

	def on_list_snapshots_copy_item( self, widget, data = None ):
		self.on_btnCopySnapshot_clicked( self.glade.get_widget( 'btnCopySnapshot' ) )

	def getCmdOutput( self, cmd ):
		retVal = ''

		try:
			pipe = os.popen( cmd )
			retVal = pipe.read().strip()
			pipe.close() 
		except:
			return ''

		return retVal

	def checkCmd( self, cmd ):
		cmd = cmd.strip()

		if len( cmd ) < 1:
			return False

		if os.path.isfile( cmd ):
			return True

		cmd = self.getCmdOutput( "which \"%s\"" % cmd )

		if len( cmd ) < 1:
			return False

		if os.path.isfile( cmd ):
			return True

		return False

	def on_btnDiffWith_clicked( self, button ):
		if len( self.store_snapshots ) < 1:
			return

		#get path from the list
		iter = self.list_snapshots.get_selection().get_selected()[1]
		if iter is None:
			return
		path1 = self.store_snapshots.get_value( iter, 2 )

		#get path from the combo
		path2 = self.store_snapshots.get_value( self.comboDiffWith.get_active_iter(), 2 )

		#check if the 2 paths are different
		if path1 == path2:
			messagebox.show_error( self.dialog, self.config, _("You can't compare a snapshot to itself") )
			return

		diffCmd = self.editDiffCmd.get_text()
		diffCmdParams = self.editDiffCmdParams.get_text()

		if not self.checkCmd( diffCmd ):
			messagebox.show_error( self.dialog, self.config, _("Command not found: %s") % diffCmd )
			return

		params = diffCmdParams
		params = params.replace( '%1', "\"%s\"" % path1 )
		params = params.replace( '%2', "\"%s\"" % path2 )

		cmd = diffCmd + ' ' + params + ' &'
		os.system( cmd  )

		#check if the command changed
		oldDiffCmd, oldDiffCmdParams = self.config.diffCmd()
		if diffCmd != oldDiffCmd or diffCmdParams != oldDiffCmdParams:
			self.config.setDiffCmd( diffCmd, diffCmdParams )
			self.config.save()

	def update_snapshots( self ):
		self.editPath.set_text( self.path )

		#fill snapshots
		self.store_snapshots.clear()
	
		path = os.path.join( self.current_snapshot, self.path[ 1 : ] )	
		isdir = os.path.isdir( path )

		counter = 0
		indexComboDiffWith = 0
		
		#add now
		path = self.path
		if os.path.exists( path ):
			if os.path.isdir( path ) == isdir:
				self.store_snapshots.append( [ self.config.snapshotDisplayName( '/' ), '/', path ] )
				if '/' == self.current_snapshot:
					indexComboDiffWith = counter
				counter += 1
				
		#add snapshots
		for snapshot in self.snapshots:
			snapshot_path = self.config.snapshotPath( snapshot )
			path = self.config.snapshotPathTo( snapshot, self.path )
			if os.path.exists( path ):
				if os.path.isdir( path ) == isdir:
					self.store_snapshots.append( [ self.config.snapshotDisplayName( snapshot ), snapshot_path, path ] )
					if snapshot_path == self.current_snapshot:
						indexComboDiffWith = counter
					counter += 1

		#select first item
		if len( self.store_snapshots ) > 0:
			iter = self.store_snapshots.get_iter_first()
			if not iter is None:
				self.list_snapshots.get_selection().select_iter( iter )
			self.comboDiffWith.set_active( indexComboDiffWith )
	
			self.glade.get_widget( 'btnDiffWith' ).set_sensitive( True )
			self.comboDiffWith.set_sensitive( True )
		else:
			self.glade.get_widget( 'btnDiffWith' ).set_sensitive( False )
			self.comboDiffWith.set_sensitive( False )

		self.updateToolbar()

	def on_list_snapshots_row_activated( self, list, path, column ):
		self.open_item()

	def open_item( self ):
		iter = self.list_snapshots.get_selection().get_selected()[1]
		if iter is None:
			return
		path = self.store_snapshots.get_value( iter, 2 )
		cmd = "gnome-open \"%s\" &" % path
		os.system( cmd )

	def run( self ):
		snapshot_id = None
		while True:
			ret_val = self.dialog.run()
			
			if gtk.RESPONSE_OK == ret_val: #go to
				iter = self.list_snapshots.get_selection().get_selected()[1]
				if not iter is None:
					snapshot_id = self.store_snapshots.get_value( iter, 1 )
				break
			else:
				#cancel, close ...
				break

		self.dialog.hide()
		return snapshot_id
