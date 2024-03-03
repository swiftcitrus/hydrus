from qtpy import QtCore as QC
from qtpy import QtGui as QG
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC

from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUIMenus

class GUICore( QC.QObject ):
    
    my_instance = None
    
    def __init__( self ):
        
        QC.QObject.__init__( self )
        
        self._menu_open = False
        
        # TODO: populate this shortly after boot and use it in place of many manual pixel counts
        self.decent_pixel_text_height = 10
        
        GUICore.my_instance = self
        
    
    @staticmethod
    def instance() -> 'GUICore':
        
        if GUICore.my_instance is None:
            
            raise Exception( 'GUICore is not yet initialised!' )
            
        else:
            
            return GUICore.my_instance
            
        
    
    def MenubarMenuIsOpen( self ):
        
        self._menu_open = True
        
    
    def MenubarMenuIsClosed( self ):
        
        self._menu_open = False
        
    
    def MenuIsOpen( self ):
        
        return self._menu_open
        
    
    def PopupMenu( self, widget: QW.QWidget, menu: QW.QMenu ):
        
        if HC.PLATFORM_MACOS and widget.window().isModal():
            
            # Ok, seems like Big Sur can't do menus at the moment lmao. it shows the menu but the mouse can't interact with it
            
            if CG.client_controller.new_options.GetBoolean( 'do_macos_debug_dialog_menus' ):
                
                from hydrus.client.gui import ClientGUICoreMenuDebug
                
                ClientGUICoreMenuDebug.ShowMenuDialog( widget, menu )
                
                ClientGUIMenus.DestroyMenu( menu )
                
                return
                
            
        
        if not menu.isEmpty():
            
            self._menu_open = True
            
            menu.exec_( QG.QCursor.pos() ) # This could also be window.mapToGlobal( QC.QPoint( 0, 0 ) ), but in practice, popping up at the current cursor position feels better.
            
            self._menu_open = False
            
        
        ClientGUIMenus.DestroyMenu( menu )
        
    

core = GUICore.instance
