import typing

from qtpy import QtCore as QC
from qtpy import QtGui as QG
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientSearch
from hydrus.client.gui import ClientGUICore as CGC
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIMenus
from hydrus.client.gui import ClientGUITags
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.search import ClientGUISearch
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.gui.widgets import ClientGUIMenuButton
from hydrus.client.media import ClientMedia
from hydrus.client.metadata import ClientTags

# wew lad
# https://stackoverflow.com/questions/46456238/checkbox-not-visible-inside-combobox
class CheckBoxDelegate( QW.QStyledItemDelegate ):
    
    def __init__( self, parent = None ):
        
        super( CheckBoxDelegate, self ).__init__( parent )
        

    def createEditor( self, parent, op, idx ):
        
        self.editor = QW.QCheckBox( parent )
        
    

class CollectComboCtrl( QW.QComboBox ):
    
    itemChanged = QC.Signal()
    
    def __init__( self, parent, media_collect ):
        
        QW.QComboBox.__init__( self, parent )
        
        self.view().pressed.connect( self._HandleItemPressed )
        
        # this was previously 'if Fusion style only', but as it works for normal styles too, it is more helpful to have it always on
        self.setItemDelegate( CheckBoxDelegate() )
        
        self.setModel( QG.QStandardItemModel( self ) )
        
        self._ReinitialiseChoices()
        
        # Trick to display custom text
        
        self._cached_text = ''
        
        if media_collect.DoesACollect():
            
            QP.CallAfter( self.SetCollectByValue, media_collect )
            
        
    
    def _HandleItemPressed( self, index ):
        
        item = self.model().itemFromIndex( index )
        
        if item.checkState() == QC.Qt.Checked:
            
            item.setCheckState( QC.Qt.Unchecked )
            
        else:
            
            item.setCheckState( QC.Qt.Checked )
            
        
        self.SetValue( self._cached_text )
        
        self.itemChanged.emit()
        
    
    def _ReinitialiseChoices( self ):
        
        text_and_data_tuples = set()
        
        for media_sort in HG.client_controller.new_options.GetDefaultNamespaceSorts():
            
            namespaces = media_sort.GetNamespaces()
            
            try:
                
                text_and_data_tuples.update( namespaces )
                
            except:
                
                HydrusData.DebugPrint( 'Bad namespaces: {}'.format( namespaces ) )
                
                HydrusData.ShowText( 'Hey, your namespace-based sorts are likely damaged. Details have been written to the log, please let hydev know!' )
                
            
        
        text_and_data_tuples = sorted( ( ( namespace, ( 'namespace', namespace ) ) for namespace in text_and_data_tuples ) )
        
        ratings_services = HG.client_controller.services_manager.GetServices( ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ) )
        
        for ratings_service in ratings_services:
            
            text_and_data_tuples.append( ( ratings_service.GetName(), ('rating', ratings_service.GetServiceKey() ) ) )
            
        
        current_text_and_data_tuples = []
        
        for i in range( self.count() ):
            
            item = self.model().item( i, 0 )
            
            t = item.text()
            d = self.itemData( i, QC.Qt.UserRole )
            
            current_text_and_data_tuples.append( ( t, d ) )
            
        
        made_changes = False
        
        if current_text_and_data_tuples != text_and_data_tuples:
            
            if self.count() > 0:
                
                # PRO TIP 4 U: if you say self.clear() here, the program has a ~15% chance to crash instantly if you have previously done a clear/add cycle!
                # this affects PyQt and PySide, 5 and 6, running from source, so must be something in Qt core. some argument between the model and widget
                self.model().clear()
                
            
            for ( text, data ) in text_and_data_tuples:
                
                self.addItem( text, userData = data )
                
                item = self.model().item( self.count() - 1, 0 )
                
                item.setCheckState( QC.Qt.Unchecked )
                
            
            made_changes = True
            
        
        return made_changes
        
    
    def GetCheckedIndices( self ):
        
        indices = []
        
        for idx in range( self.count() ):

            item = self.model().item( idx )
            
            if item.checkState() == QC.Qt.Checked:
                
                indices.append( idx )
                
            
        
        return indices
        

    def GetCheckedStrings( self ):
        
        strings = [ ]
        
        for idx in range( self.count() ):
            
            item = self.model().item( idx )
            
            if item.checkState() == QC.Qt.Checked:
                
                strings.append( item.text() )
                
            
        
        return strings
        
    
    def GetValues( self ):
        
        namespaces = []
        rating_service_keys = []
        
        for index in self.GetCheckedIndices():
            
            ( collect_type, collect_data ) = self.itemData( index, QC.Qt.UserRole )
            
            if collect_type == 'namespace':
                
                namespaces.append( collect_data )
                
            elif collect_type == 'rating':
                
                rating_service_keys.append( collect_data )
                
            
        
        collect_strings = self.GetCheckedStrings()
        
        if len( collect_strings ) > 0:
            
            description = 'collect by ' + '-'.join( collect_strings )
            
        else:
            
            description = 'no collections'
            
        
        return ( namespaces, rating_service_keys, description )
        
    
    def hidePopup(self):
        
        if not self.view().underMouse():
            
            QW.QComboBox.hidePopup( self )
            
            
        
    
    def paintEvent( self, e ):
        
        painter = QW.QStylePainter( self )
        painter.setPen( self.palette().color( QG.QPalette.Text ) )

        opt = QW.QStyleOptionComboBox()
        self.initStyleOption( opt )

        opt.currentText = self._cached_text

        painter.drawComplexControl( QW.QStyle.CC_ComboBox, opt )

        painter.drawControl( QW.QStyle.CE_ComboBoxLabel, opt )
        
    
    def ReinitialiseChoices( self ):
        
        return self._ReinitialiseChoices()
        
    
    def SetValue( self, text ):
        
        self._cached_text = text
        
        self.setCurrentText( text )
        
        
    
    def SetCollectByValue( self, media_collect ):

        try:
            
            indices_to_check = []

            for index in range( self.count() ):

                ( collect_type, collect_data ) = self.itemData( index, QC.Qt.UserRole )

                p1 = collect_type == 'namespace' and collect_data in media_collect.namespaces
                p2 = collect_type == 'rating' and collect_data in media_collect.rating_service_keys

                if p1 or p2:
                    
                    indices_to_check.append( index )
                    
                

            self.SetCheckedIndices( indices_to_check )
            
            self.itemChanged.emit()
            
        except Exception as e:
            
            HydrusData.ShowText( 'Failed to set a collect-by value!' )

            HydrusData.ShowException( e )
            
        

    def SetCheckedIndices( self, indices_to_check ):
        
        for idx in range( self.count() ):

            item = self.model().item( idx )
            
            if idx in indices_to_check:
                
                item.setCheckState( QC.Qt.Checked )
                
            else:
                
                item.setCheckState( QC.Qt.Unchecked )
                
            
        
    

class MediaCollectControl( QW.QWidget ):
    
    def __init__( self, parent, management_controller = None, silent = False ):
        
        QW.QWidget.__init__( self, parent )
        
        # this is trash, rewrite it to deal with the media_collect object, not the management controller
        
        self._management_controller = management_controller
        
        if self._management_controller is not None and self._management_controller.HasVariable( 'media_collect' ):
            
            self._media_collect = self._management_controller.GetVariable( 'media_collect' )
            
        else:
            
            self._media_collect = HG.client_controller.new_options.GetDefaultCollect()
            
        
        self._silent = silent
        
        self._collect_comboctrl = CollectComboCtrl( self, self._media_collect )
        
        choice_tuples = [
            ( 'collect unmatched', True ),
            ( 'leave unmatched', False )
        ]
        
        self._collect_unmatched = ClientGUIMenuButton.MenuChoiceButton( self, choice_tuples )
        
        width = ClientGUIFunctions.ConvertTextToPixelWidth( self._collect_unmatched, 19 )
        
        self._collect_unmatched.setMinimumWidth( width )
        
        self._tag_context_button = ClientGUISearch.TagContextButton( self, self._media_collect.tag_context, use_short_label = True )
        
        #
        
        self._collect_unmatched.SetValue( self._media_collect.collect_unmatched )
        
        #
        
        hbox = QP.HBoxLayout( margin = 0 )
        
        QP.AddToLayout( hbox, self._collect_comboctrl, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, self._collect_unmatched, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._tag_context_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self.setLayout( hbox )
        
        #
        
        self._UpdateButtonsVisible()
        self._UpdateLabel()
        
        self._collect_unmatched.valueChanged.connect( self.CollectValuesChanged )
        self._collect_comboctrl.itemChanged.connect( self.CollectValuesChanged )
        self._tag_context_button.valueChanged.connect( self.CollectValuesChanged )
        
        self._collect_comboctrl.installEventFilter( self )
        
        HG.client_controller.sub( self, 'NotifyAdvancedMode', 'notify_advanced_mode' )
        HG.client_controller.sub( self, 'SetCollectFromPage', 'set_page_collect' )
        
    
    def _BroadcastCollect( self ):
        
        if not self._silent and self._management_controller is not None:
            
            self._management_controller.SetVariable( 'media_collect', self._media_collect )
            
            page_key = self._management_controller.GetKey( 'page' )
            
            HG.client_controller.pub( 'collect_media', page_key, self._media_collect )
            HG.client_controller.pub( 'a_collect_happened', page_key )
            
        
    
    def _UpdateButtonsVisible( self ):
        
        self._tag_context_button.setVisible( HG.client_controller.new_options.GetBoolean( 'advanced_mode' ) )
        
    
    def _UpdateLabel( self ):
        
        ( namespaces, rating_service_keys, description ) = self._collect_comboctrl.GetValues()
        
        self._collect_comboctrl.SetValue( description )
        
    
    def CollectValuesChanged( self ):
        
        ( namespaces, rating_service_keys, description ) = self._collect_comboctrl.GetValues()
        
        self._UpdateLabel()
        
        collect_unmatched = self._collect_unmatched.GetValue()
        
        tag_context = self._tag_context_button.GetValue()
        
        self._media_collect = ClientMedia.MediaCollect( namespaces = namespaces, rating_service_keys = rating_service_keys, collect_unmatched = collect_unmatched, tag_context = tag_context )
        
        self._BroadcastCollect()
        
    
    def eventFilter( self, watched, event ):
        
        if watched == self._collect_comboctrl:
            
            if event.type() == QC.QEvent.MouseButtonPress and event.button() == QC.Qt.MiddleButton:
                
                self.SetCollect( ClientMedia.MediaCollect( collect_unmatched = self._media_collect.collect_unmatched ) )
                
                return True
                
            
        
        return False
        
    
    def GetValue( self ):
        
        return self._media_collect
        
    
    def ListenForNewOptions( self ):
        
        HG.client_controller.sub( self, 'NotifyNewOptions', 'notify_new_options' )
        
    
    def NotifyAdvancedMode( self ):
        
        self._UpdateButtonsVisible()
        
    
    def NotifyNewOptions( self ):
        
        media_collect = self._media_collect.Duplicate()
        
        made_changes = self._collect_comboctrl.ReinitialiseChoices()
        
        if made_changes:
            
            self.SetCollect( media_collect, do_broadcast = False )
            
        
    
    def SetCollect( self, media_collect: ClientMedia.MediaCollect, do_broadcast = True ):
        
        self._media_collect = media_collect
        
        self._collect_comboctrl.blockSignals( True )
        self._collect_unmatched.blockSignals( True )
        
        self._collect_comboctrl.SetCollectByValue( self._media_collect )
        self._collect_unmatched.SetValue( self._media_collect.collect_unmatched )
        
        self._UpdateLabel()
        
        self._collect_comboctrl.blockSignals( False )
        self._collect_unmatched.blockSignals( False )
        
        if do_broadcast:
            
            self._BroadcastCollect()
            
        
    
    def SetCollectFromPage( self, page_key, media_collect ):
        
        if page_key == self._management_controller.GetKey( 'page' ):
            
            self.SetCollect( media_collect )
            
            self._BroadcastCollect()
            
        
    
class MediaSortControl( QW.QWidget ):
    
    sortChanged = QC.Signal( ClientMedia.MediaSort )
    
    def __init__( self, parent, management_controller = None ):
        
        QW.QWidget.__init__( self, parent )
        
        self._management_controller = management_controller
        
        self._sort_type = ( 'system', CC.SORT_FILES_BY_FILESIZE )
        
        self._sort_type_button = ClientGUICommon.BetterButton( self, 'sort', self._SortTypeButtonClick )
        self._sort_tag_display_type_button = ClientGUIMenuButton.MenuChoiceButton( self, [] )
        self._sort_order_choice = ClientGUIMenuButton.MenuChoiceButton( self, [] )
        
        tag_context = ClientSearch.TagContext( service_key = CC.COMBINED_TAG_SERVICE_KEY )
        
        self._tag_context_button = ClientGUISearch.TagContextButton( self, tag_context, use_short_label = True )
        
        type_width = ClientGUIFunctions.ConvertTextToPixelWidth( self._sort_type_button, 14 )
        
        self._sort_type_button.setMinimumWidth( type_width )
        
        tdt_width = ClientGUIFunctions.ConvertTextToPixelWidth( self._sort_tag_display_type_button, 8 )
        
        self._sort_tag_display_type_button.setMinimumWidth( tdt_width )
        
        asc_width = ClientGUIFunctions.ConvertTextToPixelWidth( self._sort_order_choice, 14 )
        
        self._sort_order_choice.setMinimumWidth( asc_width )
        
        self._UpdateSortTypeLabel()
        self._UpdateAscDescLabelsAndDefault()
        
        #
        
        hbox = QP.HBoxLayout( margin = 0 )
        
        QP.AddToLayout( hbox, self._sort_type_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, self._sort_tag_display_type_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._sort_order_choice, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._tag_context_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self.setLayout( hbox )
        
        HG.client_controller.sub( self, 'ACollectHappened', 'a_collect_happened' )
        HG.client_controller.sub( self, 'BroadcastSort', 'do_page_sort' )
        
        if self._management_controller is not None and self._management_controller.HasVariable( 'media_sort' ):
            
            media_sort = self._management_controller.GetVariable( 'media_sort' )
            
            try:
                
                self.SetSort( media_sort )
                
            except:
                
                default_sort = ClientMedia.MediaSort( ( 'system', CC.SORT_FILES_BY_FILESIZE ), CC.SORT_ASC )
                
                self.SetSort( default_sort )
                
            
        
        self._sort_tag_display_type_button.valueChanged.connect( self.EventTagDisplayTypeChoice )
        self._sort_order_choice.valueChanged.connect( self.EventSortAscChoice )
        self._tag_context_button.valueChanged.connect( self._TagContextChanged )
        
    
    def _BroadcastSort( self ):
        
        media_sort = self._GetCurrentSort()
        
        if self._management_controller is not None:
            
            self._management_controller.SetVariable( 'media_sort', media_sort )
            
        
        self.sortChanged.emit( media_sort )
        
    
    def _GetCurrentSort( self ) -> ClientMedia.MediaSort:
        
        sort_order = self._sort_order_choice.GetValue()
        
        if sort_order is None:
            
            sort_order = CC.SORT_ASC
            
        
        tag_context = self._tag_context_button.GetValue()
        
        media_sort = ClientMedia.MediaSort( sort_type = self._sort_type, sort_order = sort_order, tag_context = tag_context )
        
        return media_sort
        
    
    def _PopulateSortMenuOrList( self, menu = None ):
        
        sort_types = []
        
        menu_items_and_sort_types = []
        
        submetatypes_to_menus = {}
        
        for system_sort_type in CC.SYSTEM_SORT_TYPES_SORT_CONTROL_SORTED:
            
            sort_type = ( 'system', system_sort_type )
            
            sort_types.append( sort_type )
            
            if menu is not None:
                
                submetatype = CC.system_sort_type_submetatype_string_lookup[ system_sort_type ]
                
                if submetatype is None:
                    
                    menu_to_add_to = menu
                    
                else:
                    
                    if submetatype not in submetatypes_to_menus:
                        
                        submenu = QW.QMenu( menu )
                        
                        submetatypes_to_menus[ submetatype ] = submenu
                        
                        ClientGUIMenus.AppendMenu( menu, submenu, submetatype )
                        
                    
                    menu_to_add_to = submetatypes_to_menus[ submetatype ]
                    
                
                label = CC.sort_type_basic_string_lookup[ system_sort_type ]
                
                menu_item = ClientGUIMenus.AppendMenuItem( menu_to_add_to, label, 'Select this sort type.', self._SetSortTypeFromUser, sort_type )
                
                menu_items_and_sort_types.append( ( menu_item, sort_type ) )
                
            
        
        default_namespace_sorts = HG.client_controller.new_options.GetDefaultNamespaceSorts()
        
        if menu is not None:
            
            submenu = QW.QMenu( menu )
            
            ClientGUIMenus.AppendMenu( menu, submenu, 'namespaces' )
            
        
        for namespace_sort in default_namespace_sorts:
            
            sort_type = namespace_sort.sort_type
            
            sort_types.append( sort_type )
            
            if menu is not None:
                
                example_sort = ClientMedia.MediaSort( sort_type, CC.SORT_ASC )
                
                label = example_sort.GetSortTypeString()
                
                menu_item = ClientGUIMenus.AppendMenuItem( submenu, label, 'Select this sort type.', self._SetSortTypeFromUser, sort_type )
                
                menu_items_and_sort_types.append( ( menu_item, sort_type ) )
                
            
        
        if menu is not None:
            
            ClientGUIMenus.AppendMenuItem( submenu, 'custom', 'Set a custom namespace sort', self._SetCustomNamespaceSortFromUser )
            
        
        rating_service_keys = HG.client_controller.services_manager.GetServiceKeys( ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ) )
        
        if len( rating_service_keys ) > 0:
            
            if menu is not None:
                
                submenu = QW.QMenu( menu )
                
                ClientGUIMenus.AppendMenu( menu, submenu, 'ratings' )
                
            
            for service_key in rating_service_keys:
                
                sort_type = ( 'rating', service_key )
                
                sort_types.append( sort_type )
                
                if menu is not None:
                    
                    example_sort = ClientMedia.MediaSort( sort_type, CC.SORT_ASC )
                    
                    label = example_sort.GetSortTypeString()
                    
                    menu_item = ClientGUIMenus.AppendMenuItem( submenu, label, 'Select this sort type.', self._SetSortTypeFromUser, sort_type )
                    
                    menu_items_and_sort_types.append( ( menu_item, sort_type ) )
                    
                
            
        
        if menu is not None:
            
            for ( menu_item, sort_choice ) in menu_items_and_sort_types:
                
                if sort_choice == self._sort_type:
                    
                    menu_item.setCheckable( True )
                    menu_item.setChecked( True )
                    
                
            
        
        return sort_types
        
    
    def _SetCustomNamespaceSortFromUser( self ):
        
        if self._sort_type[0] == 'namespaces':
            
            sort_data = self._sort_type[1]
            
        else:
            
            sort_data = ( [ 'series' ], ClientTags.TAG_DISPLAY_ACTUAL )
            
        
        try:
            
            sort_data = ClientGUITags.EditNamespaceSort( self, sort_data )
            
            sort_type = ( 'namespaces', sort_data )
            
            self._SetSortTypeFromUser( sort_type )
            
        except HydrusExceptions.VetoException:
            
            return
            
        
    
    def _SortTypeButtonClick( self ):
        
        menu = QW.QMenu()
        
        self._PopulateSortMenuOrList( menu = menu )
        
        CGC.core().PopupMenu( self, menu )
        
    
    def _SetSortType( self, sort_type ):
        
        self._sort_type = sort_type
        
        self._UpdateSortTypeLabel()
        self._UpdateAscDescLabelsAndDefault()
        
    
    def _SetSortTypeFromUser( self, sort_type ):
        
        self._SetSortType( sort_type )
        
        self._UserChoseASort()
        
        self._BroadcastSort()
        
    
    def _TagContextChanged( self, tag_context: ClientSearch.TagContext ):
        
        self._UserChoseASort()
        
        self._BroadcastSort()
        
    
    def _UpdateAscDescLabelsAndDefault( self ):
        
        media_sort = self._GetCurrentSort()
        
        self._sort_order_choice.blockSignals( True )
        
        if media_sort.CanAsc():
            
            ( asc_str, desc_str, default_sort_order ) = media_sort.GetSortOrderStrings()
            
            choice_tuples = [
                ( asc_str, CC.SORT_ASC ),
                ( desc_str, CC.SORT_DESC )
            ]
            
            if choice_tuples != self._sort_order_choice.GetChoiceTuples():
                
                self._sort_order_choice.SetChoiceTuples( choice_tuples )
                
                self._sort_order_choice.SetValue( default_sort_order )
                
            
            # if there are no changes to asc/desc texts, then we'll keep the previous value
            
        else:
            
            self._sort_order_choice.SetChoiceTuples( [] )
            
        
        self._sort_order_choice.blockSignals( False )
        
    
    def _UpdateButtonsVisible( self ):
        
        self._tag_context_button.setVisible( HG.client_controller.new_options.GetBoolean( 'advanced_mode' ) )
        
    
    def _UpdateSortTypeLabel( self ):
        
        example_sort = ClientMedia.MediaSort( self._sort_type, CC.SORT_ASC )
        
        self._sort_type_button.setText( example_sort.GetSortTypeString() )
        
        ( sort_metatype, sort_data ) = self._sort_type
        
        show_tdt = sort_metatype == 'namespaces' and HG.client_controller.new_options.GetBoolean( 'advanced_mode' )
        
        if show_tdt:
            
            if sort_metatype == 'namespaces':
                
                ( namespaces, current_tag_display_type ) = sort_data
                
                tag_display_types = [
                    ClientTags.TAG_DISPLAY_ACTUAL,
                    ClientTags.TAG_DISPLAY_SELECTION_LIST,
                    ClientTags.TAG_DISPLAY_SINGLE_MEDIA
                ]
                
                choice_tuples = [ ( ClientTags.tag_display_str_lookup[ tag_display_type ], tag_display_type ) for tag_display_type in tag_display_types ]
                
                self._sort_tag_display_type_button.blockSignals( True )
                
                self._sort_tag_display_type_button.SetChoiceTuples( choice_tuples )
                
                self._sort_tag_display_type_button.SetValue( current_tag_display_type )
                
                self._sort_tag_display_type_button.blockSignals( False )
                
            
        
        self._sort_tag_display_type_button.setVisible( show_tdt )
        
    
    def _UserChoseASort( self ):
        
        if HG.client_controller.new_options.GetBoolean( 'save_page_sort_on_change' ):
            
            media_sort = self._GetCurrentSort()
            
            HG.client_controller.new_options.SetDefaultSort( media_sort )
            
        
    
    def ACollectHappened( self, page_key ):
        
        if self._management_controller is not None:
            
            my_page_key = self._management_controller.GetKey( 'page' )
            
            if page_key == my_page_key:
                
                self._BroadcastSort()
                
            
        
    
    def BroadcastSort( self, page_key = None ):
        
        if page_key is not None and page_key != self._management_controller.GetKey( 'page' ):
            
            return
            
        
        self._BroadcastSort()
        
    
    def EventSortAscChoice( self ):
        
        self._UserChoseASort()
        
        self._BroadcastSort()
        
    
    def EventTagDisplayTypeChoice( self ):
        
        tag_display_type = self._sort_tag_display_type_button.GetValue()
        
        ( sort_metatype, sort_data ) = self._sort_type
        
        if sort_metatype == 'namespaces':
            
            ( namespaces, current_tag_display_type ) = sort_data
            
            sort_data = ( namespaces, tag_display_type )
            
            self._sort_type = ( sort_metatype, sort_data )
            
            self._UserChoseASort()
            
            self._BroadcastSort()
            
        
    
    def GetSort( self ) -> ClientMedia.MediaSort:
        
        return self._GetCurrentSort()
        
    
    def NotifyAdvancedMode( self ):
        
        self._UpdateButtonsVisible()
        
    
    def SetSort( self, media_sort: ClientMedia.MediaSort ):
        
        self._SetSortType( media_sort.sort_type )
        
        # put this after 'asclabels', since we may transition from one-state to two-state
        self._sort_order_choice.SetValue( media_sort.sort_order )
        
        self._tag_context_button.SetValue( media_sort.tag_context )
        
        self._UpdateButtonsVisible()
        
    
    def wheelEvent( self, event ):
        
        if self._sort_type_button.rect().contains( self._sort_type_button.mapFromGlobal( QG.QCursor.pos() ) ):
            
            if event.angleDelta().y() > 0:
                
                index_delta = -1
                
            else:
                
                index_delta = 1
                
            
            sort_types = self._PopulateSortMenuOrList()
            
            if self._sort_type in sort_types:
                
                index = sort_types.index( self._sort_type )
                
                new_index = ( index + index_delta ) % len( sort_types )
                
                new_sort_type = sort_types[ new_index ]
                
                self._SetSortTypeFromUser( new_sort_type )
                
            
        
        event.accept()
        
    
