import sys
import xbmc
import xbmcgui
import xbmcaddon

def run():
    dialog = xbmcgui.Dialog()
    
    # Show welcome message
    dialog.ok(
        "[COLOR red]BGTV[/COLOR] Съветник", 
        "Добре дошли в инсталатора на BGTV телевизия!\nЩе ви помолим само за вашето потребителско име и парола."
    )

    # Prompt for username
    username = dialog.input('Въведете вашето BGTV потребителско име:', type=xbmcgui.INPUT_ALPHANUM)
    if not username:
        return

    # Prompt for password (masked)
    password = dialog.input('Въведете вашата парола:', type=xbmcgui.INPUT_ALPHANUM, option=xbmcgui.ALPHANUM_HIDE_INPUT)
    if not password:
        return

    # Inform user we are setting things up
    dialog.notification('BGTV Съветник', 'Инсталиране и конфигуриране на TVHeadend...', xbmcgui.NOTIFICATION_INFO, 3000)

    # Automatically trigger install/enable of the PVR client
    xbmc.executebuiltin('InstallAddon(pvr.hts)')
    xbmc.executebuiltin('EnableAddon(pvr.hts)')
    
    # Wait to allow Kodi to enable the add-on in the background
    xbmc.sleep(2000)

    try:
        # Access the PVR HTS add-on settings
        pvr_addon = xbmcaddon.Addon('pvr.hts')
        
        # Inject BGTV server configuration
        pvr_addon.setSetting('host', 'bgtv.pw')
        pvr_addon.setSetting('port', '9981')      # Standard HTTP port
        pvr_addon.setSetting('htsp_port', '9982') # HTSP streaming port
        
        # Inject user credentials
        pvr_addon.setSetting('user', username)
        pvr_addon.setSetting('pass', password)
        
        # Inform user of success
        dialog.ok(
            "Успех!", 
            "Всичко е настроено перфектно!\nЗа да се визуализират каналите, моля рестартирайте Kodi (Exit -> Start)."
        )

    except Exception as e:
        xbmc.log("BGTV Setup Error: " + str(e), xbmc.LOGERROR)
        dialog.ok(
            "Внимание: TVHeadend не е наличен", 
            "Kodi не можа да намери добавката TVHeadend HTSP Client. Сега ще ви отворим прозореца за инсталация.\n\nМоля, цъкнете 'Install' (Инсталирай) и след това стартирайте нашия BGTV Съветник отново."
        )
        xbmc.executebuiltin("ActivateWindow(AddonInformation,pvr.hts)")

if __name__ == '__main__':
    run()
