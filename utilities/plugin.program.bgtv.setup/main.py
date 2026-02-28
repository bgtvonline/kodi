import os
import xbmc
import xbmcgui
import xbmcvfs
import json

def is_addon_installed(addon_id):
    """Check if an addon is installed using JSON-RPC"""
    try:
        request = json.dumps({
            "jsonrpc": "2.0",
            "method": "Addons.GetAddonDetails",
            "params": {"addonid": addon_id},
            "id": 1
        })
        response = json.loads(xbmc.executeJSONRPC(request))
        return 'result' in response
    except:
        return False

def run():
    dialog = xbmcgui.Dialog()
    
    # Show welcome message
    dialog.ok(
        "[COLOR red]BGTV[/COLOR] Съветник", 
        "Добре дошли в инсталатора на BGTV!\nЩе ви помолим само за вашето потребителско име и парола."
    )

    # Prompt for username
    username = dialog.input('Въведете вашето BGTV потребителско име:', type=xbmcgui.INPUT_ALPHANUM)
    if not username:
        dialog.ok("Отказано", "Не въведохте потребителско име. Опитайте отново.")
        return

    # Prompt for password (masked)
    password = dialog.input('Въведете вашата парола:', type=xbmcgui.INPUT_ALPHANUM, option=xbmcgui.ALPHANUM_HIDE_INPUT)
    if not password:
        dialog.ok("Отказано", "Не въведохте парола. Опитайте отново.")
        return

    # Check if pvr.hts is already installed
    pvr_installed = is_addon_installed('pvr.hts')

    if not pvr_installed:
        dialog.ok(
            "[COLOR red]BGTV[/COLOR] Съветник",
            "Сега Kodi ще ви попита дали искате да инсталирате PVR клиента.\n\nМоля, натиснете [COLOR green]ДА[/COLOR] (Yes)!"
        )
        xbmc.executebuiltin('InstallAddon(pvr.hts)')
        
        pDialog = xbmcgui.DialogProgress()
        pDialog.create("[COLOR red]BGTV[/COLOR] Съветник", "Изчакване PVR клиентът да се инсталира...")
        
        for i in range(60):
            xbmc.sleep(1000)
            pDialog.update(int(i * 100 / 60))
            if is_addon_installed('pvr.hts'):
                break
            if pDialog.iscanceled():
                pDialog.close()
                dialog.ok("Отказано", "Инсталацията беше прекъсната.")
                return
        
        pDialog.close()
        
        if not is_addon_installed('pvr.hts'):
            dialog.ok("Грешка", "PVR клиентът не беше инсталиран.\nМоля стартирайте Съветника отново.")
            return

    # Now configure the addon
    pDialog = xbmcgui.DialogProgress()
    pDialog.create("[COLOR red]BGTV[/COLOR] Съветник", "Активиране на PVR клиента...")
    pDialog.update(20)

    xbmc.executebuiltin('EnableAddon(pvr.hts)')
    xbmc.sleep(2000)
    pDialog.update(40, "Записване на настройките...")

    # --- CRITICAL FIX ---
    # Kodi 20+ (Nexus/Omega) uses MULTI-INSTANCE PVR settings.
    # The old settings.xml in addon_data/pvr.hts/ is OBSOLETE for connection settings.
    # Connection settings (host, user, pass) are now stored PER INSTANCE at:
    #   addon_data/pvr.hts/instances/instance-1/settings.xml
    # We must also write to the root settings.xml for backward compatibility.
    
    # Instance settings (where connection info actually lives in Kodi 20+)
    instance_settings_xml = '''<?xml version="1.0" encoding="utf-8" standalone="yes"?>
<settings version="1">
    <setting id="host">{host}</setting>
    <setting id="http_port">{http_port}</setting>
    <setting id="htsp_port">{htsp_port}</setting>
    <setting id="user">{user}</setting>
    <setting id="pass">{password}</setting>
    <setting id="connect_timeout">10</setting>
    <setting id="response_timeout">5</setting>
    <setting id="streaming_profile"></setting>
    <setting id="streaming_http">false</setting>
    <setting id="pretuner_enabled">false</setting>
    <setting id="epg_async">true</setting>
    <setting id="dvr_playstatus">true</setting>
</settings>'''.format(
        host='bgtv.pw',
        http_port='9981',
        htsp_port='9982',
        user=username,
        password=password
    )

    # Legacy root settings (for older Kodi or migration)
    root_settings_xml = '''<?xml version="1.0" encoding="utf-8" standalone="yes"?>
<settings version="1">
    <setting id="host">{host}</setting>
    <setting id="http_port">{http_port}</setting>
    <setting id="htsp_port">{htsp_port}</setting>
    <setting id="user">{user}</setting>
    <setting id="pass">{password}</setting>
    <setting id="epg_async">true</setting>
</settings>'''.format(
        host='bgtv.pw',
        http_port='9981',
        htsp_port='9982',
        user=username,
        password=password
    )

    addon_data = xbmcvfs.translatePath('special://profile/addon_data/pvr.hts/')
    
    # Write to ALL possible settings locations to cover every Kodi version
    paths_to_write = [
        # Modern Kodi 20+ instance path
        (os.path.join(addon_data, 'instances', 'instance-1', 'settings.xml'), instance_settings_xml),
        # Legacy root path (Kodi 19 and below, also migration)
        (os.path.join(addon_data, 'settings.xml'), root_settings_xml),
    ]
    
    pDialog.update(60, "Записване на настройките...")
    
    success = True
    for filepath, content in paths_to_write:
        dirpath = os.path.dirname(filepath)
        if not os.path.exists(dirpath):
            os.makedirs(dirpath)
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            xbmc.log("BGTV Setup: Wrote settings to " + filepath, xbmc.LOGINFO)
        except Exception as e:
            xbmc.log("BGTV Setup Error writing to " + filepath + ": " + str(e), xbmc.LOGERROR)
            success = False

    pDialog.update(90, "Почти готово...")
    xbmc.sleep(1000)
    pDialog.close()

    if not success:
        dialog.ok("Грешка", "Не можах да запиша всички настройки. Моля опитайте отново.")
        return

    # Ask to restart
    restart = dialog.yesno(
        "Успех! ✅", 
        "BGTV е настроена!\n\nСървър: bgtv.pw\nПотребител: {user}\n\nKodi трябва да се рестартира.\nДа го затворя ли сега?".format(user=username)
    )

    if restart:
        xbmc.executebuiltin('Quit')

if __name__ == '__main__':
    run()
