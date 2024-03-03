#This file is licensed under the Do What the Fuck You Want To Public License aka WTFPL

import os
import typing

import qtpy

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG

import math

from collections import defaultdict

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusProfiling
from hydrus.core import HydrusTime

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import QtInit

isValid = QtInit.isValid

def registerEventType():
    
    if QtInit.WE_ARE_PYSIDE:
        
        return QC.QEvent.Type( QC.QEvent.registerEventType() )
        
    else:
        
        return QC.QEvent.registerEventType()
        
    

class HBoxLayout( QW.QHBoxLayout ):
    
    def __init__( self, margin = 2, spacing = 2 ):
        
        QW.QHBoxLayout.__init__( self )
        
        self.setMargin( margin )
        self.setSpacing( spacing )
        
    
    def setMargin( self, val ):
        
        self.setContentsMargins( val, val, val, val )
        
    

class VBoxLayout( QW.QVBoxLayout ):

    def __init__( self, margin = 2, spacing = 2 ):
        
        QW.QVBoxLayout.__init__( self )
        
        self.setMargin( margin )
        self.setSpacing( spacing )
        

    def setMargin( self, val ):
        
        self.setContentsMargins( val, val, val, val )
        
    
class LabelledSlider( QW.QWidget ):
    
    def __init__( self, parent = None ):
        
        QW.QWidget.__init__( self, parent )
        
        self.setLayout( VBoxLayout( spacing = 2 ) )
        
        top_layout = HBoxLayout( spacing = 2 )
        
        self._min_label = QW.QLabel()
        self._max_label = QW.QLabel()
        self._value_label = QW.QLabel()
        self._slider = QW.QSlider()
        self._slider.setOrientation( QC.Qt.Horizontal )
        self._slider.setTickInterval( 1 )
        self._slider.setTickPosition( QW.QSlider.TicksBothSides )
        
        top_layout.addWidget( self._min_label )
        top_layout.addWidget( self._slider )
        top_layout.addWidget( self._max_label )
        
        self.layout().addLayout( top_layout )
        self.layout().addWidget( self._value_label )
        self._value_label.setAlignment( QC.Qt.AlignVCenter | QC.Qt.AlignHCenter )
        self.layout().setAlignment( self._value_label, QC.Qt.AlignHCenter )
        
        self._slider.valueChanged.connect( self._UpdateLabels )
        
        self._UpdateLabels()
        
    def _UpdateLabels( self ):
        
        self._min_label.setText( str( self._slider.minimum() ) )
        self._max_label.setText( str( self._slider.maximum() ) )
        self._value_label.setText( str( self._slider.value() ) )
        
    def GetValue( self ):
        
        return self._slider.value()
    
    def SetRange( self, min, max ):
        
        self._slider.setRange( min, max )
        
        self._UpdateLabels()
        
    def SetValue( self, value ):
        
        self._slider.setValue( value )
        
        self._UpdateLabels()
        

def SplitterVisibleCount( splitter ):
    
    count = 0
    
    for i in range( splitter.count() ):
        
        if splitter.widget( i ).isVisibleTo( splitter ): count += 1
        
    return count


class DirPickerCtrl( QW.QWidget ):

    dirPickerChanged = QC.Signal()
    
    def __init__( self, parent ):
        
        QW.QWidget.__init__( self, parent )
        
        layout = HBoxLayout( spacing = 2 )
        
        self._path_edit = QW.QLineEdit( self )
        
        self._button = QW.QPushButton( 'browse', self )
        
        self._button.clicked.connect( self._Browse )
        
        self._path_edit.textEdited.connect( self._TextEdited )
        
        layout.addWidget( self._path_edit )
        layout.addWidget( self._button )
        
        self.setLayout( layout )
        
    
    def SetPath( self, path ):
        
        self._path_edit.setText( path )
        
    
    def GetPath( self ):
        
        return self._path_edit.text()
        
    
    def _Browse( self ):
        
        existing_path = self._path_edit.text()
        
        kwargs = {}
        
        if CG.client_controller.new_options.GetBoolean( 'use_qt_file_dialogs' ):
            
            # careful here, QW.QFileDialog.Options doesn't exist on PyQt6
            kwargs[ 'options' ] = QW.QFileDialog.Option.DontUseNativeDialog
            
        
        path = QW.QFileDialog.getExistingDirectory( self, '', existing_path, **kwargs )
        
        if path == '':
            
            return
            
        
        path = os.path.normpath( path )
        
        self._path_edit.setText( path )
        
        if os.path.exists( path ):
            
            self.dirPickerChanged.emit()
            
        
    
    def _TextEdited( self, text ):
        
        if os.path.exists( text ):
            
            self.dirPickerChanged.emit()
            
        

class FilePickerCtrl( QW.QWidget ):
    
    filePickerChanged = QC.Signal()

    def __init__( self, parent = None, wildcard = None, starting_directory = None ):
        
        QW.QWidget.__init__( self, parent )

        layout = HBoxLayout( spacing = 2 )

        self._path_edit = QW.QLineEdit( self )

        self._button = QW.QPushButton( 'browse', self )

        self._button.clicked.connect( self._Browse )

        self._path_edit.textEdited.connect( self._TextEdited )

        layout.addWidget( self._path_edit )
        layout.addWidget( self._button )

        self.setLayout( layout )
        
        self._save_mode = False
        
        self._wildcard = wildcard
        
        self._starting_directory = starting_directory
        

    def SetPath( self, path ):
        
        self._path_edit.setText( path )
        

    def GetPath( self ):
        
        return self._path_edit.text()
        
    
    def SetSaveMode( self, save_mode ):
        
        self._save_mode = save_mode
        

    def _Browse( self ):
        
        existing_path = self._path_edit.text()
        
        if existing_path == '' and self._starting_directory is not None:
            
            existing_path = self._starting_directory
            
        
        kwargs = {}
        
        if CG.client_controller.new_options.GetBoolean( 'use_qt_file_dialogs' ):
            
            # careful here, QW.QFileDialog.Options doesn't exist on PyQt6
            kwargs[ 'options' ] = QW.QFileDialog.Option.DontUseNativeDialog
            
        
        if self._save_mode:
            
            if self._wildcard:
                
                path = QW.QFileDialog.getSaveFileName( self, '', existing_path, filter = self._wildcard, selectedFilter = self._wildcard, **kwargs )[0]
                
            else:
                
                path = QW.QFileDialog.getSaveFileName( self, '', existing_path, **kwargs )[0]
                
            
        else:
            
            if self._wildcard:
                
                path = QW.QFileDialog.getOpenFileName( self, '', existing_path, filter = self._wildcard, selectedFilter = self._wildcard, **kwargs )[0]
                
            else:
                
                path = QW.QFileDialog.getOpenFileName( self, '', existing_path, **kwargs )[0]
                
            
        
        if path == '':
            
            return
            
        
        path = os.path.normpath( path )
        
        self._path_edit.setText( path )
        
        if self._save_mode or os.path.exists( path ):
            
            self.filePickerChanged.emit()
            
        

    def _TextEdited( self, text ):
        
        if self._save_mode or os.path.exists( text ):
            
            self.filePickerChanged.emit()
            
        

class TabBar( QW.QTabBar ):
    
    tabDoubleLeftClicked = QC.Signal( int )
    tabMiddleClicked = QC.Signal( int )
    
    tabSpaceDoubleLeftClicked = QC.Signal()
    tabSpaceDoubleMiddleClicked = QC.Signal()
    
    def __init__( self, parent = None ):
        
        QW.QTabBar.__init__( self, parent )
        
        if HC.PLATFORM_MACOS:
            
            self.setDocumentMode( True )
            
        
        self.setMouseTracking( True )
        self.setAcceptDrops( True )
        self._supplementary_drop_target = None
        
        self._last_clicked_tab_index = -1
        self._last_clicked_global_pos = None
        self._last_clicked_timestamp_ms = 0
        
    
    def AddSupplementaryTabBarDropTarget( self, drop_target ):
        
        self._supplementary_drop_target = drop_target
        
    
    def clearLastClickedTabInfo( self ):
        
        self._last_clicked_tab_index = -1
        
        self._last_clicked_global_pos = None
        
        self._last_clicked_timestamp_ms = 0
        
    
    def event( self, event ):
        
        return QW.QTabBar.event( self, event )
        
    
    def mouseMoveEvent( self, e ):
        
        e.ignore()
        
    
    def mousePressEvent( self, event ):
        
        index = self.tabAt( event.position().toPoint() )
        
        if event.button() == QC.Qt.LeftButton:
            
            self._last_clicked_tab_index = index
            
            self._last_clicked_global_pos = event.globalPosition().toPoint()
            
            self._last_clicked_timestamp_ms = HydrusTime.GetNowMS()
            
        
        QW.QTabBar.mousePressEvent( self, event )
        
    
    def mouseReleaseEvent( self, event ):
        
        index = self.tabAt( event.position().toPoint() )
        
        if event.button() == QC.Qt.MiddleButton:
            
            if index != -1:
                
                self.tabMiddleClicked.emit( index )
                
                return
                
            
        
        QW.QTabBar.mouseReleaseEvent( self, event )
        
    
    def mouseDoubleClickEvent( self, event ):
        
        index = self.tabAt( event.position().toPoint() )
        
        if event.button() == QC.Qt.LeftButton:
            
            if index == -1:
                
                self.tabSpaceDoubleLeftClicked.emit()
                
            else:
                
                self.tabDoubleLeftClicked.emit( index )
                
            
            return
            
        elif event.button() == QC.Qt.MiddleButton:
            
            if index == -1:
                
                self.tabSpaceDoubleMiddleClicked.emit()
                
            else:
                
                self.tabMiddleClicked.emit( index )
                
            
            return
            
        
        QW.QTabBar.mouseDoubleClickEvent( self, event )
        
    
    def dragEnterEvent(self, event):

        if 'application/hydrus-tab' in event.mimeData().formats():
            
            event.ignore()
            
        else:
            
            event.accept()
            
        
    
    def dragMoveEvent( self, event ):
        
        if 'application/hydrus-tab' not in event.mimeData().formats():
            
            tab_index = self.tabAt( event.position().toPoint() )
            
            if tab_index != -1:
                
                shift_down = event.modifiers() & QC.Qt.ShiftModifier
                
                if shift_down:
                    
                    do_navigate = CG.client_controller.new_options.GetBoolean( 'page_drag_change_tab_with_shift' )
                    
                else:
                    
                    do_navigate = CG.client_controller.new_options.GetBoolean( 'page_drag_change_tab_normally' )
                    
                
                if do_navigate:
                    
                    self.parentWidget().setCurrentIndex( tab_index )
                    
                
            
        else:
            
            event.ignore()
            
        
    
    def lastClickedTabInfo( self ):
        
        return ( self._last_clicked_tab_index, self._last_clicked_global_pos, self._last_clicked_timestamp_ms )
        
    
    def dropEvent( self, event ):
        
        if self._supplementary_drop_target:
            
            self._supplementary_drop_target.eventFilter( self, event )
            
        else:
            
            event.ignore()
            
        
    
    def wheelEvent( self, event ):
        
        try:
            
            if CG.client_controller.new_options.GetBoolean( 'wheel_scrolls_tab_bar' ):
                
                children = self.children()
                
                if len( children ) >= 2:
                    
                    scroll_left = children[0]
                    scroll_right = children[1]
                    
                    if event.angleDelta().y() > 0:
                        
                        b = scroll_left
                        
                    else:
                        
                        b = scroll_right
                        
                    
                    if isinstance( b, QW.QAbstractButton ):
                        
                        b.click()
                        
                    
                
                event.accept()
                
                return
                
            
        except:
            
            pass
            
        
        QW.QTabBar.wheelEvent( self, event )
        
    

# A heavily extended/tweaked version of https://forum.qt.io/topic/67542/drag-tabs-between-qtabwidgets/
class TabWidgetWithDnD( QW.QTabWidget ):
    
    pageDragAndDropped = QC.Signal( QW.QWidget, QW.QWidget )
    
    def __init__( self, parent = None ):
        
        QW.QTabWidget.__init__( self, parent )
        
        self.setTabBar( TabBar( self ) )
        
        self.setAcceptDrops( True )
        
        self._tab_bar = self.tabBar()
        
        self._supplementary_drop_target = None
        
    
    def _LayoutPagesHelper( self ):
        
        current_index = self.currentIndex()

        for i in range( self.count() ):

            self.setCurrentIndex( i )

            if isinstance( self.widget( i ), TabWidgetWithDnD ):
                
                self.widget( i )._LayoutPagesHelper()
                
            
        
        self.setCurrentIndex( current_index )
        
    
    def LayoutPages( self ):
        
        # hydev adds: I no longer call this, as I moved splitter setting to a thing called per page when page is first visibly shown
        # leaving it here for now in case I need it again
        
        # Momentarily switch to each page, then back, forcing a layout update.
        # If this is not done, the splitters on the hidden pages won't resize their widgets properly when we restore
        # splitter sizes after this, since they would never became visible.
        # We first have to climb up the widget hierarchy and go down recursively from the root tab widget,
        # since it's not enough to make a page visible if its a nested page: all of its ancestor pages have to be visible too.
        # This shouldn't be visible to users since we switch back immediately.
        # There is probably a proper way to do this...

        highest_ancestor_of_same_type = self

        parent = self.parentWidget()

        while parent is not None:

            if isinstance( parent, TabWidgetWithDnD ):
                
                highest_ancestor_of_same_type = parent
                

            parent = parent.parentWidget()
            
        
        highest_ancestor_of_same_type._LayoutPagesHelper() # This does the actual recursive descent and making pages visible
        
    
    # This is a hack that adds an additional drop target to the tab bar. The added drop target will get drop events from the tab bar.
    # Used to make the case of files/media droppend onto tabs work.
    def AddSupplementaryTabBarDropTarget( self, drop_target ):
        
        self._supplementary_drop_target = drop_target
        self.tabBar().AddSupplementaryTabBarDropTarget( drop_target )
        
    
    def mouseMoveEvent( self, e ):
        
        mouse_is_over_actual_page = self.currentWidget() and self.currentWidget().rect().contains( self.currentWidget().mapFromGlobal( self.mapToGlobal( e.position().toPoint() ) ) )
        
        if mouse_is_over_actual_page or CG.client_controller.new_options.GetBoolean( 'disable_page_tab_dnd' ):
            
            QW.QTabWidget.mouseMoveEvent( self, e )
            
            return
            
        
        if e.buttons() != QC.Qt.LeftButton:
            
            return
            
        
        my_mouse_pos = e.position().toPoint()
        global_mouse_pos = self.mapToGlobal( my_mouse_pos )
        tab_bar_mouse_pos = self._tab_bar.mapFromGlobal( global_mouse_pos )
        
        if not self._tab_bar.rect().contains( tab_bar_mouse_pos ):
            
            return
            
        
        if not isinstance( self._tab_bar, TabBar ):
            
            return
            
        
        ( clicked_tab_index, clicked_global_pos, clicked_timestamp_ms ) = self._tab_bar.lastClickedTabInfo()
        
        if clicked_tab_index == -1:
            
            return
            
        
        # I used to do manhattanlength stuff, but tbh this works better
        # delta_pos = e.globalPosition().toPoint() - clicked_global_pos
        
        if not HydrusTime.TimeHasPassedMS( clicked_timestamp_ms + 100 ):
            
            # don't start a drag until decent movement
            
            return
            
        
        tab_rect = self._tab_bar.tabRect( clicked_tab_index )
        
        pixmap = QG.QPixmap( tab_rect.size() )
        self._tab_bar.render( pixmap, QC.QPoint(), QG.QRegion( tab_rect ) )
        
        mimeData = QC.QMimeData()
        
        mimeData.setData( 'application/hydrus-tab', b'' )
        
        drag = QG.QDrag( self._tab_bar )
        
        drag.setMimeData( mimeData )
        
        drag.setPixmap( pixmap )
        
        cursor = QG.QCursor( QC.Qt.OpenHandCursor )
        
        drag.setHotSpot( QC.QPoint( 0, 0 ) )
        
        # this puts the tab pixmap exactly where we picked it up, but it looks bad
        # drag.setHotSpot( tab_bar_mouse_pos - tab_rect.topLeft() )
        
        drag.setDragCursor( cursor.pixmap(), QC.Qt.MoveAction )
        
        drag.exec_( QC.Qt.MoveAction )
        

    def dragEnterEvent( self, e: QG.QDragEnterEvent ):
        
        if self.currentWidget() and self.currentWidget().rect().contains( self.currentWidget().mapFromGlobal( self.mapToGlobal( e.position().toPoint() ) ) ):
            
            return QW.QTabWidget.dragEnterEvent( self, e )
            
        
        if 'application/hydrus-tab' in e.mimeData().formats():
            
            e.accept()
            
        else:
            
            e.ignore()
            
        
    
    def dragMoveEvent( self, event: QG.QDragMoveEvent ):
        
        #if self.currentWidget() and self.currentWidget().rect().contains( self.currentWidget().mapFromGlobal( self.mapToGlobal( event.position().toPoint() ) ) ): return QW.QTabWidget.dragMoveEvent( self, event )
        
        screen_pos = self.mapToGlobal( event.position().toPoint() )
        
        tab_pos = self._tab_bar.mapFromGlobal( screen_pos )
        
        tab_index = self._tab_bar.tabAt( tab_pos )
        
        if tab_index != -1:
            
            shift_down = event.modifiers() & QC.Qt.ShiftModifier
            
            if shift_down:
                
                do_navigate = CG.client_controller.new_options.GetBoolean( 'page_drag_change_tab_with_shift' )
                
            else:
                
                do_navigate = CG.client_controller.new_options.GetBoolean( 'page_drag_change_tab_normally' )
                
            
            if do_navigate:
                
                self.setCurrentIndex( tab_index )
                
            
        
        if 'application/hydrus-tab' not in event.mimeData().formats():
            
            event.reject()
            

        #return QW.QTabWidget.dragMoveEvent( self, event )
        

    def dragLeaveEvent( self, e: QG.QDragLeaveEvent ):
        
        #if self.currentWidget() and self.currentWidget().rect().contains( self.currentWidget().mapFromGlobal( self.mapToGlobal( e.position().toPoint() ) ) ): return QW.QTabWidget.dragLeaveEvent( self, e )
        
        e.accept()
        

    def addTab(self, widget, *args, **kwargs ):
        
        if isinstance( widget, TabWidgetWithDnD ):
            
            widget.AddSupplementaryTabBarDropTarget( self._supplementary_drop_target )
            
        
        QW.QTabWidget.addTab( self, widget, *args, **kwargs )
        
    
    def insertTab(self, index, widget, *args, **kwargs):

        if isinstance( widget, TabWidgetWithDnD ):
            
            widget.AddSupplementaryTabBarDropTarget( self._supplementary_drop_target )
            

        QW.QTabWidget.insertTab( self, index, widget, *args, **kwargs )
        
    
    def dropEvent( self, e: QG.QDropEvent ):
        
        if self.currentWidget() and self.currentWidget().rect().contains( self.currentWidget().mapFromGlobal( self.mapToGlobal( e.position().toPoint() ) ) ):
            
            return QW.QTabWidget.dropEvent( self, e )
            
        
        if 'application/hydrus-tab' not in e.mimeData().formats(): #Page dnd has no associated mime data
            
            e.ignore()
            
            return
            
        
        w = self
        
        source_tab_bar = e.source()
        
        if not isinstance( source_tab_bar, TabBar ):
            
            return
            
        
        ( source_page_index, source_page_click_global_pos, source_page_clicked_timestamp_ms ) = source_tab_bar.lastClickedTabInfo()
        
        source_tab_bar.clearLastClickedTabInfo()
        
        source_notebook = source_tab_bar.parentWidget()
        source_page = source_notebook.widget( source_page_index )
        source_name = source_tab_bar.tabText( source_page_index )
        
        while w is not None:
            
            if source_page == w:
                
                # you cannot drop a page of pages inside itself
                
                return
                
            
            w = w.parentWidget()
            

        e.setDropAction( QC.Qt.MoveAction )
        
        e.accept()
        
        counter = self.count()
        
        screen_pos = self.mapToGlobal( e.position().toPoint() )
        
        tab_pos = self.tabBar().mapFromGlobal( screen_pos )
        
        dropped_on_tab_index = self.tabBar().tabAt( tab_pos )
        
        if source_notebook == self and dropped_on_tab_index == source_page_index:
            
            return # if we drop on ourself, make no action, even on the right edge
            
        
        dropped_on_left_edge = False
        dropped_on_right_edge = False
        
        if dropped_on_tab_index != -1:
            
            EDGE_PADDING = 15
            
            tab_rect = self.tabBar().tabRect( dropped_on_tab_index )
            
            edge_size = QC.QSize( EDGE_PADDING, tab_rect.height() )
            
            left_edge_rect = QC.QRect( tab_rect.topLeft(), edge_size )
            right_edge_rect = QC.QRect( tab_rect.topRight() - QC.QPoint( EDGE_PADDING, 0 ), edge_size )
            
            drop_pos = e.position().toPoint()
            
            dropped_on_left_edge = left_edge_rect.contains( drop_pos )
            dropped_on_right_edge = right_edge_rect.contains( drop_pos )
            
        
        if counter == 0:
            
            self.addTab( source_page, source_name )
            
        else:
            
            if dropped_on_tab_index == -1:
                
                insert_index = counter
                
            else:
                
                insert_index = dropped_on_tab_index
                
                if dropped_on_right_edge:
                    
                    insert_index += 1
                    
                
                if self == source_notebook:
                    
                    if insert_index == source_page_index + 1 and not dropped_on_left_edge:
                        
                        pass # in this special case, moving it confidently one to the right, we will disobey the normal rules and indeed move one to the right, rather than no-op
                        
                    elif insert_index > source_page_index:
                        
                        # we are inserting to our right, which needs a shift since we will be removing ourselves from the list
                        
                        insert_index -= 1
                        
                    
                
            
            if source_notebook == self and insert_index == source_page_index:
                
                return # if we mean to insert on ourself, make no action
                
            
            self.insertTab( insert_index, source_page, source_name )

            shift_down = e.modifiers() & QC.Qt.ShiftModifier
            
            follow_dropped_page = not shift_down

            new_options = CG.client_controller.new_options
            
            if shift_down:
                
                follow_dropped_page = new_options.GetBoolean( 'page_drop_chase_with_shift' )
                
            else:
                
                follow_dropped_page = new_options.GetBoolean( 'page_drop_chase_normally' )
                
            
            if follow_dropped_page:
                
                self.setCurrentIndex( self.indexOf( source_page ) )
                
            else:
                
                if source_page_index > 1:
                    
                    neighbour_page = source_notebook.widget( source_page_index - 1 )
                    
                    page_key = neighbour_page.GetPageKey()
                    
                else:
                    
                    page_key = source_notebook.GetPageKey()
                    
                
                CallAfter( CG.client_controller.gui.ShowPage, page_key )
                
            
        
        self.pageDragAndDropped.emit( source_page, source_tab_bar )
        
    
def DeleteAllNotebookPages( notebook ):
    
    while notebook.count() > 0:
        
        tab = notebook.widget( 0 )
        
        notebook.removeTab( 0 )
        
        tab.deleteLater()
        
    
def SplitVertically( splitter: QW.QSplitter, w1, w2, hpos ):

    splitter.setOrientation( QC.Qt.Horizontal )

    if w1.parentWidget() != splitter:
        
        splitter.addWidget( w1 )

    w1.setVisible( True )

    if w2.parentWidget() != splitter:
        
        splitter.addWidget( w2 )

    w2.setVisible( True )

    total_sum = sum( splitter.sizes() )

    if hpos < 0:

        splitter.setSizes( [ total_sum + hpos, -hpos ] )

    elif hpos > 0:
        
        splitter.setSizes( [ hpos, total_sum - hpos ] )


def SplitHorizontally( splitter: QW.QSplitter, w1, w2, vpos ):
    
    splitter.setOrientation( QC.Qt.Vertical )
    
    if w1.parentWidget() != splitter:
        
        splitter.addWidget( w1 )
        
    w1.setVisible( True )
        
    if w2.parentWidget() != splitter:
        
        splitter.addWidget( w2 )

    w2.setVisible( True )
    
    total_sum = sum( splitter.sizes() )
    
    if vpos < 0:
        
        splitter.setSizes( [ total_sum + vpos, -vpos ] )
        
    elif vpos > 0:
        
        splitter.setSizes( [ vpos, total_sum - vpos ] )

class GridLayout( QW.QGridLayout ):
    
    def __init__( self, cols = 1, spacing = 2 ):
        
        QW.QGridLayout.__init__( self )
        
        self._col_count = cols
        self.setMargin( 2 )
        self.setSpacing( spacing )
        
        self.next_row = 0
        self.next_col = 0
        
    
    def GetFixedColumnCount( self ):
        
        return self._col_count
        
    
    def setMargin( self, val ):
        
        self.setContentsMargins( val, val, val, val )
        
    
def AddToLayout( layout, item, flag = None, alignment = None ):

    if isinstance( layout, GridLayout ):
        
        row = layout.next_row
        
        col = layout.next_col
        
        try:
            
            if isinstance( item, QW.QLayout ):
                
                layout.addLayout( item, row, col )
                
            elif isinstance( item, QW.QWidget ):
                
                layout.addWidget( item, row, col )
                
            elif isinstance( item, tuple ):
                
                spacer = QW.QPushButton()#QW.QSpacerItem( 0, 0, QW.QSizePolicy.Expanding, QW.QSizePolicy.Fixed )
                layout.addWidget( spacer, row, col )
                spacer.setVisible(False)
                
                return
                
            
        finally:
            
            if col == layout.GetFixedColumnCount() - 1:
                
                layout.next_row += 1
                layout.next_col = 0
                
            else:
                
                layout.next_col += 1
                
            
        
    else:
        
        if isinstance( item, QW.QLayout ):
            
            layout.addLayout( item )
            
            if alignment is not None:
                
                layout.setAlignment( item, alignment )
                
            
        elif isinstance( item, QW.QWidget ):
            
            layout.addWidget( item )
            
            if alignment is not None:
                
                layout.setAlignment( item, alignment )
                
            
        elif isinstance( item, tuple ):
            
            layout.addStretch( 1 )
            
            return
            
        
    
    zero_border = False
    
    if flag is None or flag == CC.FLAGS_NONE:
        
        pass
        
    elif flag in ( CC.FLAGS_CENTER, CC.FLAGS_ON_LEFT, CC.FLAGS_ON_RIGHT, CC.FLAGS_CENTER_PERPENDICULAR, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH ):
        
        if flag == CC.FLAGS_CENTER:
            
            alignment = QC.Qt.AlignVCenter | QC.Qt.AlignHCenter
            
        if flag == CC.FLAGS_ON_LEFT:
            
            alignment = QC.Qt.AlignLeft | QC.Qt.AlignVCenter
            
        elif flag == CC.FLAGS_ON_RIGHT:
            
            alignment = QC.Qt.AlignRight | QC.Qt.AlignVCenter
            
        elif flag in ( CC.FLAGS_CENTER_PERPENDICULAR, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH ):
            
            if isinstance( layout, QW.QHBoxLayout ):
                
                alignment = QC.Qt.AlignVCenter
                
            else:
                
                alignment = QC.Qt.AlignHCenter
                
            
        
        layout.setAlignment( item, alignment )
        
        if flag == CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH:
            
            if isinstance( layout, QW.QVBoxLayout ) or isinstance( layout, QW.QHBoxLayout ):
                
                layout.setStretchFactor( item, 5 )
                
            
        
        if isinstance( item, QW.QLayout ):
            
            zero_border = True
            
        
    elif flag in ( CC.FLAGS_EXPAND_PERPENDICULAR, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR ):
        
        if flag == CC.FLAGS_EXPAND_SIZER_PERPENDICULAR:
            
            zero_border = True
            
        
        if isinstance( item, QW.QWidget ):
            
            if isinstance( layout, QW.QHBoxLayout ):
                
                h_policy = QW.QSizePolicy.Fixed
                v_policy = QW.QSizePolicy.Expanding
                
            else:
                
                h_policy = QW.QSizePolicy.Expanding
                v_policy = QW.QSizePolicy.Fixed
                
            
            item.setSizePolicy( h_policy, v_policy )
            
        
    elif flag in ( CC.FLAGS_EXPAND_BOTH_WAYS, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS, CC.FLAGS_EXPAND_BOTH_WAYS_POLITE, CC.FLAGS_EXPAND_BOTH_WAYS_SHY ):
        
        if flag == CC.FLAGS_EXPAND_SIZER_BOTH_WAYS:
            
            zero_border = True
            
        
        if isinstance( item, QW.QWidget ):
            
            item.setSizePolicy( QW.QSizePolicy.Expanding, QW.QSizePolicy.Expanding )
            
        
        if isinstance( layout, QW.QVBoxLayout ) or isinstance( layout, QW.QHBoxLayout ):
            
            if flag in ( CC.FLAGS_EXPAND_BOTH_WAYS, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS ):
                
                stretch_factor = 50
                
            elif flag == CC.FLAGS_EXPAND_BOTH_WAYS_POLITE:
                
                stretch_factor = 30
                
            elif flag == CC.FLAGS_EXPAND_BOTH_WAYS_SHY:
                
                stretch_factor = 10
                
            
            layout.setStretchFactor( item, stretch_factor )
            
        
    
    if zero_border:
        
        margin = 0
        
        if isinstance( item, QW.QFrame ):
            
            margin = item.frameWidth()
            
        
        item.setContentsMargins( margin, margin, margin, margin )
        
    

def ScrollAreaVisibleRect( scroll_area ):
    
    if not scroll_area.widget(): return QC.QRect( 0, 0, 0, 0 )
    
    rect = scroll_area.widget().visibleRegion().boundingRect()

    # Do not allow it to be smaller than the scroll area's viewport size:
    
    if rect.width() < scroll_area.viewport().width():
        
        rect.setWidth( scroll_area.viewport().width() )

    if rect.height() < scroll_area.viewport().height():
        
        rect.setHeight( scroll_area.viewport().height() )
        
    
    return rect
    

def AdjustOpacity( image: QG.QImage, opacity_factor ):
    
    new_image = QG.QImage( image.width(), image.height(), QG.QImage.Format_RGBA8888 )
    
    new_image.setDevicePixelRatio( image.devicePixelRatio() )
    
    new_image.fill( QC.Qt.transparent )
    
    painter = QG.QPainter( new_image )
    
    painter.setOpacity( opacity_factor )
    
    painter.drawImage( 0, 0, image )
    
    return new_image
    

def ToKeySequence( modifiers, key ):
    
    if QtInit.WE_ARE_QT5:
        
        if isinstance( modifiers, QC.Qt.KeyboardModifiers ):
            
            seq_str = ''
            
            for modifier in [ QC.Qt.ShiftModifier, QC.Qt.ControlModifier, QC.Qt.AltModifier, QC.Qt.MetaModifier, QC.Qt.KeypadModifier, QC.Qt.GroupSwitchModifier ]:
                
                if modifiers & modifier: seq_str += QG.QKeySequence( modifier ).toString()
                
            
            seq_str += QG.QKeySequence( key ).toString()
            
            return QG.QKeySequence( seq_str )
            
        else:
            
            return QG.QKeySequence( key + modifiers )
            
        
    else:
        
        return QG.QKeySequence( QC.QKeyCombination( modifiers, key ) ) # pylint: disable=E1101
        
    

def AddShortcut( widget, modifier, key, func: typing.Callable, *args ):
    
    shortcut = QW.QShortcut( widget )
    
    shortcut.setKey( ToKeySequence( modifier, key ) )
    
    shortcut.setContext( QC.Qt.WidgetWithChildrenShortcut )
    
    shortcut.activated.connect( lambda: func( *args ) )
    

def GetBackgroundColour( widget ):
    
    return widget.palette().color( QG.QPalette.Window )


CallAfterEventType = registerEventType()

class CallAfterEvent( QC.QEvent ):
    
    def __init__( self, fn, *args, **kwargs ):
        
        QC.QEvent.__init__( self, CallAfterEventType )
        
        self._fn = fn
        self._args = args
        self._kwargs = kwargs
        
    
    def Execute( self ):
        
        if self._fn is not None:
            
            self._fn( *self._args, **self._kwargs )
            
        
    
class CallAfterEventCatcher( QC.QObject ):
    
    def __init__( self, parent ):
        
        QC.QObject.__init__( self, parent )
        
        self.installEventFilter( self )
        
    
    def eventFilter( self, watched, event ):
        
        try:
            
            if event.type() == CallAfterEventType and isinstance( event, CallAfterEvent ):
                
                if HG.profile_mode:
                    
                    summary = 'Profiling CallAfter Event: {}'.format( event._fn )
                    
                    HydrusProfiling.Profile( summary, 'event.Execute()', globals(), locals(), min_duration_ms = HG.callto_profile_min_job_time_ms )
                    
                else:
                    
                    event.Execute()
                    
                
                event.accept()
                
                return True
                
            
        except Exception as e:
            
            HydrusData.ShowException( e )
            
            return True
            
        
        return False
        
    

def CallAfter( fn, *args, **kwargs ):
    
    QW.QApplication.instance().postEvent( QW.QApplication.instance().call_after_catcher, CallAfterEvent( fn, *args, **kwargs ) )
    
    QW.QApplication.instance().eventDispatcher().wakeUp()
    
def ClearLayout( layout, delete_widgets = False ):
    
    while layout.count() > 0:

        item = layout.itemAt( 0 )

        if delete_widgets:

            if item.widget():

                item.widget().deleteLater()

            elif item.layout():

                ClearLayout( item.layout(), delete_widgets = True )
                item.layout().deleteLater()

            else:

                spacer = item.layout().spacerItem()

                del spacer

        layout.removeItem( item )
        
    
def GetClientData( widget, idx ):
    
    if isinstance( widget, QW.QComboBox ):
        
        return widget.itemData( idx, QC.Qt.UserRole )
    
    
    elif isinstance( widget, QW.QTreeWidget ):
        
        return widget.topLevelItem( idx ).data( 0, QC.Qt.UserRole )
    
    elif isinstance( widget, QW.QListWidget ):
        
        return widget.item( idx ).data( QC.Qt.UserRole )
    
    else:
        
        raise ValueError( 'Unknown widget class in GetClientData' )


def Unsplit( splitter, widget ):
    
    if widget.parentWidget() == splitter:
        
        widget.setVisible( False )
        
    
def CenterOnWindow( parent, window ):
    
    parent_window = parent.window()
    
    window.move( parent_window.frameGeometry().center() - window.rect().center() )

def ListWidgetDelete( widget, idx ):
    
    if isinstance( idx, QC.QModelIndex ):
        
        idx = idx.row()
    
    if idx != -1:
        
        item = widget.takeItem( idx )
        
        del item


def ListWidgetGetSelection( widget ):
    
    for i in range( widget.count() ):

        if widget.item( i ).isSelected(): return i

    return -1


def ListWidgetGetStrings( widget ):
    
    strings = []
    
    for i in range( widget.count() ):
        
        strings.append( widget.item( i ).text() )
        
    return strings


def ListWidgetIsSelected( widget, idx ):
    
    if idx == -1: return False
    
    return widget.item( idx ).isSelected()


def ListWidgetSetSelection( widget, idxs ):
    
    widget.clearSelection()

    if not isinstance( idxs, list ):
        
        idxs = [ idxs ]
        
    
    count = widget.count()
    
    for idx in idxs:
        
        if 0 <= idx <= count -1:
            
            widget.item( idx ).setSelected( True )
            
        
    
def SetInitialSize( widget, size ):
    
    if hasattr( widget, 'SetInitialSize' ):
        
        widget.SetInitialSize( size )
        
        return
    
    if isinstance( size, tuple ):
        
        size = QC.QSize( size[0], size[1] )
        
    
    if size.width() >= 0: widget.setMinimumWidth( size.width() )
    if size.height() >= 0: widget.setMinimumHeight( size.height() )

def SetBackgroundColour( widget, colour ):

    widget.setAutoFillBackground( True )

    object_name = widget.objectName()

    if not object_name:
        
        object_name = str( id( widget ) )

        widget.setObjectName( object_name )
    
    if isinstance( colour, QG.QColor ):
        
        widget.setStyleSheet( '#{} {{ background-color: {} }}'.format( object_name, colour.name()) )
        
    elif isinstance( colour, tuple ):
        
        colour = QG.QColor( *colour )
        
        widget.setStyleSheet( '#{} {{ background-color: {} }}'.format( object_name, colour.name() ) )
        
    else:

        widget.setStyleSheet( '#{} {{ background-color: {} }}'.format( object_name, QG.QColor( colour ).name() ) )
        
    
def SetStringSelection( combobox, string ):
    
    index = combobox.findText( string )
    
    if index != -1:
        
        combobox.setCurrentIndex( index )


def SetClientSize( widget, size ):
    
    if isinstance( size, tuple ):

        size = QC.QSize( size[ 0 ], size[ 1 ] )

    if size.width() < 0: size.setWidth( widget.width() )
    if size.height() < 0: size.setHeight( widget.height() )

    widget.resize( size )


def SetMinClientSize( widget, size ):
    
    if isinstance( size, tuple ):
        
        size = QC.QSize( size[0], size[1] )
        
    
    if size.width() >= 0: widget.setMinimumWidth( size.width() )
    if size.height() >= 0: widget.setMinimumHeight( size.height() )

def WheelEventIsSynthesised( event: QG.QWheelEvent ):
    
    if QtInit.WE_ARE_QT5:
    
        return event.source() == QC.Qt.MouseEventSynthesizedBySystem
        
    elif QtInit.WE_ARE_QT6:
        
        return event.pointerType() != QG.QPointingDevice.PointerType.Generic
        
    else:
        
        return False
        
    

class StatusBar( QW.QStatusBar ):
    
    def __init__( self, status_widths ):
        
        QW.QStatusBar.__init__( self )
        
        self._labels = []
        
        for w in status_widths:
            
            label = QW.QLabel()
            
            self._labels.append( label )
            
            if w < 0:
                
                self.addWidget( label, -1 * w )
                
            else:
                
                label.setFixedWidth( w )
                
                self.addWidget( label )
                
            
        
    
    def SetStatusText( self, text, index, tooltip = None ):
        
        if tooltip is None:
            
            tooltip = text
            
        
        cell = self._labels[ index ]
        
        if cell.text() != text:
            
            cell.setText( text )
            
        
        if cell.toolTip() != tooltip:
            
            cell.setToolTip( tooltip )
            
        
    
class UIActionSimulator:
    
    def __init__( self ):
        
        pass
        
    
    def Char( self, widget, key, text = None ):
        
        if widget is None:
            
            widget = QW.QApplication.focusWidget()
            
        
        ev1 = QG.QKeyEvent( QC.QEvent.KeyPress, key, QC.Qt.NoModifier, text = text )
        ev2 = QG.QKeyEvent( QC.QEvent.KeyRelease, key, QC.Qt.NoModifier, text = text )
        
        QW.QApplication.instance().postEvent( widget, ev1 )
        QW.QApplication.instance().postEvent( widget, ev2 )
        

class RadioBox( QW.QFrame ):
    
    radioBoxChanged = QC.Signal()
    
    def __init__( self, parent, choices, vertical = False ):
        
        QW.QFrame.__init__( self, parent )
        
        self.setFrameStyle( QW.QFrame.Box | QW.QFrame.Raised )
        
        if vertical:
            
            self.setLayout( VBoxLayout() )
            
        else:
            
            self.setLayout( HBoxLayout() )
            
        
        self._choices = []
        
        for choice in choices:
            
            radiobutton = QW.QRadioButton( choice, self )
            
            self._choices.append( radiobutton )
            
            radiobutton.clicked.connect( self.radioBoxChanged )
            
            self.layout().addWidget( radiobutton )
            
        
        if vertical and len( self._choices ):
            
            self._choices[0].setChecked( True )
            
        elif len( self._choices ):
            
            self._choices[-1].setChecked( True )
            
        
    
    def _GetCurrentChoiceWidget( self ):
        
        for choice in self._choices:
            
            if choice.isChecked():
                
                return choice
                
            
        
        return None
        
    
    def GetCurrentIndex( self ):
        
        for i in range( len( self._choices ) ):
            
            if self._choices[ i ].isChecked(): return i
            
        
        return -1
        
    
    def SetStringSelection( self, str ):

        for i in range( len( self._choices ) ):

            if self._choices[ i ].text() == str:
                
                self._choices[ i ].setChecked( True )
                
                return
                
            
        
    
    def GetStringSelection( self ):

        for i in range( len( self._choices ) ):

            if self._choices[ i ].isChecked(): return self._choices[ i ].text()

        return None
    
    def setFocus( self, reason ):
        
        item = self._GetCurrentChoiceWidget()
        
        if item is not None:
            
            item.setFocus( reason )
            
        else:
            
            QW.QFrame.setFocus( self, reason )
            
        
    
    def SetValue( self, data ):
        
        pass
        
    
    def Select( self, idx ):
    
        self._choices[ idx ].setChecked( True )


class DataRadioBox( QW.QFrame ):
    
    radioBoxChanged = QC.Signal()
    
    def __init__( self, parent, choice_tuples, vertical = False ):
        
        QW.QFrame.__init__( self, parent )
        
        self.setFrameStyle( QW.QFrame.Box | QW.QFrame.Raised )
        
        if vertical:
            
            self.setLayout( VBoxLayout() )
            
        else:
            
            self.setLayout( HBoxLayout() )
            
        
        self._choices = []
        self._buttons_to_data = {}
        
        for ( text, data ) in choice_tuples:
            
            radiobutton = QW.QRadioButton( text, self )
            
            self._choices.append( radiobutton )
            
            self._buttons_to_data[ radiobutton ] = data
            
            radiobutton.clicked.connect( self.radioBoxChanged )
            
            self.layout().addWidget( radiobutton )
            
        
        if vertical and len( self._choices ):
            
            self._choices[0].setChecked( True )
            
        elif len( self._choices ) > 0:
            
            self._choices[-1].setChecked( True )
            
        
    
    def _GetCurrentChoiceWidget( self ):
        
        for choice in self._choices:
            
            if choice.isChecked():
                
                return choice
                
            
        
        return None
        
    
    def GetValue( self ):
        
        for ( button, data ) in self._buttons_to_data.items():
            
            if button.isChecked():
                
                return data
                
            
        
        raise Exception( 'No button selected!' )
        
    
    def setFocus( self, reason ):
        
        for button in self._choices:
            
            if button.isChecked():
                
                button.setFocus( reason )
                
                return
                
            
        
        QW.QFrame.setFocus( self, reason )
        
    
    def SetValue( self, select_data ):
        
        for ( button, data ) in self._buttons_to_data.items():
            
            button.setChecked( data == select_data )
            
        
    

# Adapted from https://doc.qt.io/qt-5/qtwidgets-widgets-elidedlabel-example.html
class EllipsizedLabel( QW.QLabel ):
    
    def __init__( self, parent = None, ellipsize_end = False ):
        
        QW.QLabel.__init__( self, parent )
        
        self._ellipsize_end = ellipsize_end
        
    
    def minimumSizeHint( self ):
        
        if self._ellipsize_end:
            
            return self.sizeHint()
            
        else:
            
            return QW.QLabel.minimumSizeHint( self )
            
        
    
    def setText( self, text ):
        
        try:
            
            QW.QLabel.setText( self, text )
            
        except ValueError:
            
            QW.QLabel.setText( self, repr( text ) )
            
        
        self.update()
        
    
    def sizeHint( self ):
        
        if self._ellipsize_end:
            
            num_lines = self.text().count( '\n' ) + 1
            
            line_width = self.fontMetrics().lineWidth()
            line_height = self.fontMetrics().lineSpacing()
            
            size_hint = QC.QSize( 3 * line_width, num_lines * line_height )
            
        else:
            
            size_hint = QW.QLabel.sizeHint( self )
            
        
        return size_hint
        
    
    def paintEvent( self, event ):

        if not self._ellipsize_end:
            
            QW.QLabel.paintEvent( self, event )
            
            return
            
        
        painter = QG.QPainter( self )

        fontMetrics = painter.fontMetrics()

        text_lines = self.text().split( '\n' )
        
        line_spacing = fontMetrics.lineSpacing()
        
        current_y = 0
        
        done = False
        
        my_width = self.width()
        
        for text_line in text_lines:
            
            elided_line = fontMetrics.elidedText( text_line, QC.Qt.ElideRight, my_width )
            
            x = 0
            width = my_width
            height = line_spacing
            flags = self.alignment()
            
            painter.drawText( x, current_y, width, height, flags, elided_line )
            
            # old hacky line that doesn't support alignment flags
            #painter.drawText( QC.QPoint( 0, current_y + fontMetrics.ascent() ), elided_line )
            
            current_y += line_spacing
            
            # old code that did multiline wrap width stuff
            '''
            text_layout = QG.QTextLayout( text_line, painter.font() )
            
            text_layout.beginLayout()
            
            while True:
            
                line = text_layout.createLine()
                
                if not line.isValid(): break
                
                line.setLineWidth( self.width() )
                
                next_line_y = y + line_spacing
            
                if self.height() >= next_line_y + line_spacing:
            
                    line.draw( painter, QC.QPoint( 0, y ) )
                
                    y = next_line_y
                    
                else:

                    last_line = text_line[ line.textStart(): ]
                
                    elided_last_line = fontMetrics.elidedText( last_line, QC.Qt.ElideRight, self.width() )
                
                    painter.drawText( QC.QPoint( 0, y + fontMetrics.ascent() ), elided_last_line )
                    
                    done = True
                    
                    break
                    
                

            text_layout.endLayout()
            
            if done: break
            '''
            
        

class Dialog( QW.QDialog ):
    
    def __init__( self, parent = None, **kwargs ):

        title = None 
        
        if 'title' in kwargs:
            
            title = kwargs['title']
            
            del kwargs['title']
            
        
        QW.QDialog.__init__( self, parent, **kwargs )
        
        self.setWindowFlag( QC.Qt.WindowContextHelpButtonHint, on = False )
        
        if title is not None:
            
            self.setWindowTitle( title )
            
        
        self._closed_by_user = False
        
    
    def closeEvent( self, event ):
        
        if event.spontaneous():
            
            self._closed_by_user = True
            
        
        QW.QDialog.closeEvent( self, event )
        
    
    # True if the dialog was closed by the user clicking on the X on the titlebar (so neither reject nor accept was chosen - the dialog result is still reject in this case though)    
    def WasCancelled( self ):
        
        return self._closed_by_user
        
    
    def SetCancelled( self, closed ):
        
        self._closed_by_user = closed
        
    
    def __enter__( self ):
        
        return self
        
    
    def __exit__( self, exc_type, exc_val, exc_tb ):
        
        if isValid( self ):
            
            self.deleteLater()
            
        
    
class PasswordEntryDialog( Dialog ):
    
    def __init__( self, parent, message, caption ):
        
        Dialog.__init__( self, parent )
        
        self.setWindowTitle( caption )
        
        self._ok_button = QW.QPushButton( 'OK', self )
        self._ok_button.clicked.connect( self.accept )
        
        self._cancel_button = QW.QPushButton( 'Cancel', self )
        self._cancel_button.clicked.connect( self.reject )
        
        self._password = QW.QLineEdit( self )
        self._password.setEchoMode( QW.QLineEdit.Password )
        
        self.setLayout( QW.QVBoxLayout() )
        
        entry_layout = QW.QHBoxLayout()
        
        entry_layout.addWidget( QW.QLabel( message, self ) )
        entry_layout.addWidget( self._password )
        
        button_layout = QW.QHBoxLayout()
        
        button_layout.addStretch( 1 )
        button_layout.addWidget( self._cancel_button )
        button_layout.addWidget( self._ok_button )
        
        self.layout().addLayout( entry_layout )
        self.layout().addLayout( button_layout )
        

    def GetValue( self ):
        
        return self._password.text()
        

class DirDialog( QW.QFileDialog ):

    def __init__( self, parent = None, message = None ):
        
        QW.QFileDialog.__init__( self, parent )
        
        if message is not None: self.setWindowTitle( message )
        
        self.setAcceptMode( QW.QFileDialog.AcceptOpen )
        
        self.setFileMode( QW.QFileDialog.Directory )
        
        self.setOption( QW.QFileDialog.ShowDirsOnly, True )
        
        if CG.client_controller.new_options.GetBoolean( 'use_qt_file_dialogs' ):
            
            self.setOption( QW.QFileDialog.DontUseNativeDialog, True )
            
        
    
    def __enter__( self ):
        
        return self
        
    
    def __exit__( self, exc_type, exc_val, exc_tb ):
        
        self.deleteLater()
        
    
    def _GetSelectedFiles( self ):
        
        return [ os.path.normpath( path ) for path in self.selectedFiles() ]
        
    
    def GetPath(self):
        
        sel = self._GetSelectedFiles()
        
        if len( sel ) > 0:
            
            return sel[0]
            
        
        return None


class FileDialog( QW.QFileDialog ):
    
    def __init__( self, parent = None, message = None, acceptMode = QW.QFileDialog.AcceptOpen, fileMode = QW.QFileDialog.ExistingFile, default_filename = None, default_directory = None, wildcard = None, defaultSuffix = None ):
        
        QW.QFileDialog.__init__( self, parent )
        
        if message is not None:
            
            self.setWindowTitle( message )
            
        
        self.setAcceptMode( acceptMode )
        
        self.setFileMode( fileMode )
        
        if default_directory is not None:
            
            self.setDirectory( default_directory )
            
        
        if defaultSuffix is not None:
            
            self.setDefaultSuffix( defaultSuffix )
            
        
        if default_filename is not None:
            
            self.selectFile( default_filename )
            
        
        if wildcard:
            
            self.setNameFilter( wildcard )
            
        
        if CG.client_controller.new_options.GetBoolean( 'use_qt_file_dialogs' ):
            
            self.setOption( QW.QFileDialog.DontUseNativeDialog, True )
            
        

    def __enter__( self ):

        return self
        

    def __exit__( self, exc_type, exc_val, exc_tb ):

        self.deleteLater()
        

    def _GetSelectedFiles( self ):
        
        return [ os.path.normpath( path ) for path in self.selectedFiles() ]
        
    
    def GetPath( self ):

        sel = self._GetSelectedFiles()

        if len( sel ) > 0:
            
            return sel[ 0 ]
            

        return None
    
    
    def GetPaths( self ):
        
        return self._GetSelectedFiles()


# A QTreeWidget where if an item is (un)checked, all its children are also (un)checked, recursively
class TreeWidgetWithInheritedCheckState( QW.QTreeWidget ):
    
    def __init__( self, *args, **kwargs ):
        
        QW.QTreeWidget.__init__( self, *args, **kwargs )
        
        self.itemChanged.connect( self._HandleItemCheckStateUpdate )
        
    
    def _GetChildren( self, item: QW.QTreeWidgetItem ) -> typing.List[ QW.QTreeWidgetItem ]:
        
        children = [ item.child( i ) for i in range( item.childCount() ) ]
        
        return children
        
    
    def _HandleItemCheckStateUpdate( self, item, column ):
        
        self.blockSignals( True )
        
        self._UpdateChildrenCheckState( item, item.checkState( 0 ) )
        self._UpdateParentCheckState( item )
        
        self.blockSignals( False )
        
    
    def _UpdateChildrenCheckState( self, item, check_state ):
        
        for child in self._GetChildren( item ):
            
            child.setCheckState( 0, check_state )
            
            self._UpdateChildrenCheckState( child, check_state )
            
        
    
    def _UpdateParentCheckState( self, item: QW.QTreeWidgetItem ):
        
        parent = item.parent()
        
        if isinstance( parent, QW.QTreeWidgetItem ):
            
            all_values = { child.checkState( 0 ) for child in self._GetChildren( parent ) }
            
            if all_values == { QC.Qt.Checked }:
                
                end_state = QC.Qt.Checked
                
            elif all_values == { QC.Qt.Unchecked }:
                
                end_state = QC.Qt.Unchecked
                
            else:
                
                end_state = QC.Qt.PartiallyChecked
                
            
            if end_state != parent.checkState( 0 ):
                
                parent.setCheckState( 0, end_state )
                
                self._UpdateParentCheckState( parent )
                
            
        
    

def ListsToTuples( potentially_nested_lists ):
    
    if HydrusData.IsAListLikeCollection( potentially_nested_lists ):
        
        return tuple( map( ListsToTuples, potentially_nested_lists ) )
        
    else:
        
        return potentially_nested_lists
        
    

class WidgetEventFilter ( QC.QObject ):
    
    _mouse_tracking_required = { 'EVT_MOUSE_EVENTS' }

    _strong_focus_required = { 'EVT_KEY_DOWN' }

    def __init__( self, parent_widget ):

        self._parent_widget = parent_widget
        
        QC.QObject.__init__( self, parent_widget )
        
        parent_widget.installEventFilter( self )
        
        self._callback_map = defaultdict( list )
        
        self._user_moved_window = False # There is no EVT_MOVE_END in Qt so some trickery is required.

    def _ExecuteCallbacks( self, event_name, event ):
        
        if event_name not in self._callback_map: return
        
        event_killed = False
        
        for callback in self._callback_map[ event_name ]:
            
            if not callback( event ): event_killed = True
            
        return event_killed


    def eventFilter( self, watched, event ):
        
        try:
            
            # Once somehow this got called with no _parent_widget set - which is probably fixed now but leaving the check just in case, wew
            # Might be worth debugging this later if it still occurs - the only way I found to reproduce it is to run the help > debug > initialize server command
            if not hasattr( self, '_parent_widget') or not isValid( self._parent_widget ): return False
            
            type = event.type()
            
            event_killed = False
            
            if type == QC.QEvent.KeyPress:
                
                event_killed = event_killed or self._ExecuteCallbacks( 'EVT_KEY_DOWN', event )
                
            elif type == QC.QEvent.WindowStateChange:
                
                if isValid( self._parent_widget ):
                    
                    if self._parent_widget.isMaximized() or (event.oldState() & QC.Qt.WindowMaximized): event_killed = event_killed or self._ExecuteCallbacks( 'EVT_MAXIMIZE', event )
            
            elif type == QC.QEvent.MouseMove:
                
                event_killed = event_killed or self._ExecuteCallbacks( 'EVT_MOUSE_EVENTS', event )
                
            elif type == QC.QEvent.MouseButtonDblClick:
                
                if event.button() == QC.Qt.LeftButton:
                    
                    event_killed = event_killed or self._ExecuteCallbacks( 'EVT_LEFT_DCLICK', event )
                    
                elif event.button() == QC.Qt.RightButton:
                    
                    event_killed = event_killed or self._ExecuteCallbacks( 'EVT_RIGHT_DCLICK', event )
                    
                
                event_killed = event_killed or self._ExecuteCallbacks( 'EVT_MOUSE_EVENTS', event )
                
            elif type == QC.QEvent.MouseButtonPress:
                
                if event.buttons() & QC.Qt.LeftButton: event_killed = event_killed or self._ExecuteCallbacks( 'EVT_LEFT_DOWN', event )
                
                if event.buttons() & QC.Qt.MiddleButton: event_killed = event_killed or self._ExecuteCallbacks( 'EVT_MIDDLE_DOWN', event )
                
                if event.buttons() & QC.Qt.RightButton: event_killed = event_killed or self._ExecuteCallbacks( 'EVT_RIGHT_DOWN', event )
                
                event_killed = event_killed or self._ExecuteCallbacks( 'EVT_MOUSE_EVENTS', event )
                
            elif type == QC.QEvent.MouseButtonRelease:
                
                if event.buttons() & QC.Qt.LeftButton: event_killed = event_killed or self._ExecuteCallbacks( 'EVT_LEFT_UP', event )
                
                event_killed = event_killed or self._ExecuteCallbacks( 'EVT_MOUSE_EVENTS', event )
                
            elif type == QC.QEvent.Wheel:
                
                event_killed = event_killed or self._ExecuteCallbacks( 'EVT_MOUSEWHEEL', event )
                
                event_killed = event_killed or self._ExecuteCallbacks( 'EVT_MOUSE_EVENTS', event )
                
            elif type == QC.QEvent.Scroll:
                
                event_killed = event_killed or self._ExecuteCallbacks( 'EVT_SCROLLWIN', event )
                
            elif type == QC.QEvent.Move:
                
                event_killed = event_killed or self._ExecuteCallbacks( 'EVT_MOVE', event )
                
                if isValid( self._parent_widget ) and self._parent_widget.isVisible():
                    
                    self._user_moved_window = True
                
            elif type == QC.QEvent.Resize:
                
                event_killed = event_killed or self._ExecuteCallbacks( 'EVT_SIZE', event )
                
            elif type == QC.QEvent.NonClientAreaMouseButtonPress:
                
                self._user_moved_window = False
                
            elif type == QC.QEvent.NonClientAreaMouseButtonRelease:
                
                if self._user_moved_window:
                    
                    event_killed = event_killed or self._ExecuteCallbacks( 'EVT_MOVE_END', event )
                    
                    self._user_moved_window = False
                    
                
            
            if event_killed:
                
                event.accept()
                
                return True
                
            
        except Exception as e:
            
            HydrusData.ShowException( e )
            
            return True
            
        
        return False
        
    
    def _AddCallback( self, evt_name, callback ):
        
        if evt_name in self._mouse_tracking_required:
            
            self._parent_widget.setMouseTracking( True )
            
        if evt_name in self._strong_focus_required:
            
            self._parent_widget.setFocusPolicy( QC.Qt.StrongFocus )
            
        self._callback_map[ evt_name ].append( callback )

    def EVT_KEY_DOWN( self, callback ):
        
        self._AddCallback( 'EVT_KEY_DOWN', callback )

    def EVT_LEFT_DCLICK( self, callback ):
        
        self._AddCallback( 'EVT_LEFT_DCLICK', callback )

    def EVT_RIGHT_DCLICK( self, callback ):

        self._AddCallback( 'EVT_RIGHT_DCLICK', callback )
        
    def EVT_LEFT_DOWN( self, callback ):
        
        self._AddCallback( 'EVT_LEFT_DOWN', callback )

    def EVT_LEFT_UP( self, callback ):
        
        self._AddCallback( 'EVT_LEFT_UP', callback )

    def EVT_MAXIMIZE( self, callback ):
        
        self._AddCallback( 'EVT_MAXIMIZE', callback )

    def EVT_MIDDLE_DOWN( self, callback ):
        
        self._AddCallback( 'EVT_MIDDLE_DOWN', callback )

    def EVT_MOUSE_EVENTS( self, callback ):
        
        self._AddCallback( 'EVT_MOUSE_EVENTS', callback )

    def EVT_MOUSEWHEEL( self, callback ):
        
        self._AddCallback( 'EVT_MOUSEWHEEL', callback )

    def EVT_MOVE( self, callback ):
        
        self._AddCallback( 'EVT_MOVE', callback )

    def EVT_MOVE_END( self, callback ):
        
        self._AddCallback( 'EVT_MOVE_END', callback )

    def EVT_RIGHT_DOWN( self, callback ):
        
        self._AddCallback( 'EVT_RIGHT_DOWN', callback )

    def EVT_SCROLLWIN( self, callback ):
        
        self._AddCallback( 'EVT_SCROLLWIN', callback )

    def EVT_SIZE( self, callback ):
        
        self._AddCallback( 'EVT_SIZE', callback )
