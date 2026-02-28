import os
import xbmc
import xbmcgui
import xbmcvfs
import json

def is_addon_installed(addon_id):
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
    
    # Check if pvr.hts is installed (it should be, because it's a strict dependency now)
    if not is_addon_installed('pvr.hts'):
        dialog.ok(
            "Грешка",
            "TVHeadend PVR клиентът липсва!\n\n"
            "Kodi не успя да го инсталира. Моля отидете на:\n"
            "[COLOR yellow]Add-ons > Install from repository > Kodi Add-on repository > PVR clients > Tvheadend HTSP Client[/COLOR]\n\n"
            "Инсталирайте го ръчно и стартирайте този Съветник отново."
        )
        return
    
    # PVR is installed, proceed with setup
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

    # Configure the addon
    pDialog = xbmcgui.DialogProgress()
    pDialog.create("[COLOR red]BGTV[/COLOR] Съветник", "Активиране на PVR клиента...")
    pDialog.update(20)

    xbmc.executebuiltin('EnableAddon(pvr.hts)')
    xbmc.sleep(2000)
    pDialog.update(40, "Записване на настройките...")

    # Kodi 20+ multi-instance settings + legacy root settings
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
    
    paths_to_write = [
        (os.path.join(addon_data, 'instances', 'instance-1', 'settings.xml'), instance_settings_xml),
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

    restart = dialog.yesno(
        "Успех! ✅", 
        "BGTV е настроена!\n\nСървър: bgtv.pw\nПотребител: {user}\n\nKodi трябва да се рестартира.\nДа го затворя ли сега?".format(user=username)
    )

    if restart:
        xbmc.executebuiltin('Quit')

if __name__ == '__main__':
    run()
