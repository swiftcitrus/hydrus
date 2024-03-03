import os

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusGlobals as HG

from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUIMenus
from hydrus.client.gui import QtPorting as QP

SystemTrayAvailable = QW.QSystemTrayIcon.isSystemTrayAvailable

class ClientSystemTrayIcon( QW.QSystemTrayIcon ):
    
    flip_show_ui = QC.Signal()
    flip_pause_network_jobs = QC.Signal()
    flip_pause_subscription_jobs = QC.Signal()
    highlight = QC.Signal()
    flip_minimise_ui = QC.Signal()
    exit_client = QC.Signal()
    
    def __init__( self, parent: QW.QWidget ):
        
        QW.QSystemTrayIcon.__init__( self, parent )
        
        self._ui_is_currently_shown = True
        self._ui_is_currently_minimised = False
        self._should_always_show = False
        self._network_traffic_paused = False
        self._subscriptions_paused = False
        
        self._show_hide_menu_item = None
        self._network_traffic_menu_item = None
        self._subscriptions_paused_menu_item = None
        
        self._just_clicked_to_show = False
        
        png_path = os.path.join( HC.STATIC_DIR, 'hydrus_non-transparent.png' )
        
        self.setIcon( QG.QIcon( png_path ) )
        
        self.activated.connect( self._ClickActivated )
        
        self._RegenerateMenu()
        
    
    def _ClickActivated( self, activation_reason ):
        
        # if we click immediately, some users get frozen ui, I assume a mix-up with the icon being destroyed during the same click event or similar
        
        QP.CallAfter( self._WasActivated, activation_reason )
        
    
    def _RegenerateMenu( self ):
        
        # I'm not a qwidget, but a qobject, so use my parent for this
        parent_widget = self.parent()
        
        new_menu = ClientGUIMenus.GenerateMenu( parent_widget )
        
        self._show_hide_menu_item = ClientGUIMenus.AppendMenuItem( new_menu, 'show/hide', 'Hide or show the hydrus client', self.flip_show_ui.emit )
        
        self._minimise_restore_menu_item = ClientGUIMenus.AppendMenuItem( new_menu, 'restore/minimise', 'Restore or minimise the hydrus client window', self.flip_minimise_ui.emit )
        
        self._UpdateShowHideMenuItemLabel()
        
        ClientGUIMenus.AppendSeparator( new_menu )
        
        self._network_traffic_menu_item = ClientGUIMenus.AppendMenuItem( new_menu, 'network traffic', 'Pause/resume network traffic', self.flip_pause_network_jobs.emit )
        
        self._UpdateNetworkTrafficMenuItemLabel()
        
        self._subscriptions_paused_menu_item = ClientGUIMenus.AppendMenuItem( new_menu, 'subscriptions', 'Pause/resume subscriptions', self.flip_pause_subscription_jobs.emit )
        
        self._UpdateSubscriptionsMenuItemLabel()
        
        ClientGUIMenus.AppendSeparator( new_menu )
        
        ClientGUIMenus.AppendMenuItem( new_menu, 'exit', 'Close the hydrus client', self.exit_client.emit )
        
        #
        
        old_menu = self.contextMenu()
        
        self.setContextMenu( new_menu )
        
        if old_menu is not None:
            
            ClientGUIMenus.DestroyMenu( old_menu )
            
        
        self._UpdateTooltip()
        
    
    def _UpdateNetworkTrafficMenuItemLabel( self ):
        
        label = 'unpause network traffic' if self._network_traffic_paused else 'pause network traffic'
        
        self._network_traffic_menu_item.setText( label )
        
    
    def _UpdateRestoreMinimiseMenuItemLabel( self ):
        
        label = 'restore' if self._ui_is_currently_minimised else 'minimise'
        
        self._minimise_restore_menu_item.setText( label )
        
        show_it = self._ui_is_currently_shown and not CG.client_controller.new_options.GetBoolean( 'minimise_client_to_system_tray' )
        
        self._minimise_restore_menu_item.setVisible( show_it )
        
    
    def _UpdateShowHideMenuItemLabel( self ):
        
        label = 'hide' if self._ui_is_currently_shown else 'show'
        
        self._show_hide_menu_item.setText( label )
        
        self._UpdateRestoreMinimiseMenuItemLabel()
        
    
    def _UpdateShowSelf( self ) -> bool:
        
        menu_regenerated = False
        
        should_show = self._should_always_show or not self._ui_is_currently_shown
        
        if should_show != self.isVisible():
            
            self.setVisible( should_show )
            
            if should_show:
                
                # apparently context menu needs to be regenerated on re-show
                
                self._RegenerateMenu()
                
                menu_regenerated = True
                
            
        
        return menu_regenerated
        
    
    def _UpdateSubscriptionsMenuItemLabel( self ):
        
        if self._subscriptions_paused_menu_item is not None:
            
            label = 'unpause subscriptions' if self._subscriptions_paused else 'pause subscriptions'
            
            self._subscriptions_paused_menu_item.setText( label )
            
        
    
    def _UpdateTooltip( self ):
        
        app_display_name = CG.client_controller.new_options.GetString( 'app_display_name' )
        
        tooltip = app_display_name
        
        if self._network_traffic_paused:
            
            tooltip = '{} - network traffic paused'.format( tooltip )
            
        
        if self._subscriptions_paused:
            
            tooltip = '{} - subscriptions paused'.format( tooltip )
            
        
        if self.toolTip != tooltip:
            
            self.setToolTip( tooltip )
            
        
    
    def _WasActivated( self, activation_reason ):
        
        if not QP.isValid( self ) or HC.PLATFORM_MACOS:
            
            return
            
        
        if activation_reason in ( QW.QSystemTrayIcon.Unknown, QW.QSystemTrayIcon.Trigger ):
            
            if self._ui_is_currently_shown:
                
                self._just_clicked_to_show = False
                
                self.highlight.emit()
                
            else:
                
                self._just_clicked_to_show = True
                
                self.flip_show_ui.emit()
                
            
        elif activation_reason in ( QW.QSystemTrayIcon.DoubleClick, QW.QSystemTrayIcon.MiddleClick ):
            
            if activation_reason == QW.QSystemTrayIcon.DoubleClick and self._just_clicked_to_show:
                
                return
                
            
            self.flip_show_ui.emit()
            
        
    
    def SetNetworkTrafficPaused( self, network_traffic_paused: bool ):
        
        if network_traffic_paused != self._network_traffic_paused:
            
            self._network_traffic_paused = network_traffic_paused
            
            self._UpdateNetworkTrafficMenuItemLabel()
            
            self._UpdateTooltip()
            
        
    
    def SetSubscriptionsPaused( self, subscriptions_paused: bool ):
        
        if subscriptions_paused != self._subscriptions_paused:
            
            self._subscriptions_paused = subscriptions_paused
            
            self._UpdateSubscriptionsMenuItemLabel()
            
            self._UpdateTooltip()
            
        
    
    def SetUIIsCurrentlyMinimised( self, ui_is_currently_minimised: bool ):
        
        if ui_is_currently_minimised != self._ui_is_currently_minimised:
            
            self._ui_is_currently_minimised = ui_is_currently_minimised
            
            self._UpdateRestoreMinimiseMenuItemLabel()
            
        
    
    def SetUIIsCurrentlyShown( self, ui_is_currently_shown: bool ):
        
        if ui_is_currently_shown != self._ui_is_currently_shown:
            
            self._ui_is_currently_shown = ui_is_currently_shown
            
            menu_regenerated = self._UpdateShowSelf()
            
            if not menu_regenerated:
                
                self._UpdateShowHideMenuItemLabel()
                
            
            if not self._ui_is_currently_shown:
                
                self._just_clicked_to_show = False
                
            
        
    
    def SetShouldAlwaysShow( self, should_always_show: bool ):
        
        if should_always_show != self._should_always_show:
            
            self._should_always_show = should_always_show
            
            self._UpdateShowSelf()
            
        
