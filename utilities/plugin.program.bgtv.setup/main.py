import os
import xbmc
import xbmcgui
import xbmcvfs
import json

def is_pvr_installed():
    """Check if pvr.hts is installed using JSON-RPC"""
    try:
        request = json.dumps({
            "jsonrpc": "2.0",
            "method": "Addons.GetAddonDetails",
            "params": {"addonid": "pvr.hts", "properties": ["installed", "enabled"]},
            "id": 1
        })
        response = json.loads(xbmc.executeJSONRPC(request))
        return 'result' in response
    except:
        return False

def enable_pvr():
    """Enable pvr.hts via JSON-RPC"""
    try:
        request = json.dumps({
            "jsonrpc": "2.0",
            "method": "Addons.SetAddonEnabled",
            "params": {"addonid": "pvr.hts", "enabled": True},
            "id": 1
        })
        xbmc.executeJSONRPC(request)
    except:
        pass

def run():
    dialog = xbmcgui.Dialog()

    # ============================================================
    # STEP 1: Check if PVR client is installed
    # ============================================================
    if not is_pvr_installed():
        dialog.ok(
            "[COLOR red]BGTV[/COLOR] Съветник",
            "За да гледате телевизия, е нужен PVR клиент.\n\n"
            "Ще отворя списъка с PVR добавки.\n"
            "Намерете [COLOR yellow]Tvheadend HTSP Client[/COLOR]\n"
            "и натиснете [COLOR green]Install[/COLOR].\n\n"
            "След това стартирайте Съветника отново!"
        )
        # Open the PVR clients list in the addon browser
        # Using multiple fallback paths for compatibility
        xbmc.executebuiltin('ActivateWindow(10040,addons://browse/xbmc.pvrclient,return)')
        # Give Kodi time to process the command before script exits
        xbmc.sleep(2000)
        return

    # ============================================================
    # STEP 2: PVR is installed! Ask for credentials
    # ============================================================
    dialog.ok(
        "[COLOR red]BGTV[/COLOR] Съветник",
        "TVHeadend PVR клиентът е намерен!\n\n"
        "Сега въведете вашите BGTV данни за достъп."
    )

    username = dialog.input('Въведете вашето BGTV потребителско име:', type=xbmcgui.INPUT_ALPHANUM)
    if not username:
        dialog.ok("Отказано", "Не въведохте потребителско име. Опитайте отново.")
        return

    password = dialog.input('Въведете вашата парола:', type=xbmcgui.INPUT_ALPHANUM, option=xbmcgui.ALPHANUM_HIDE_INPUT)
    if not password:
        dialog.ok("Отказано", "Не въведохте парола. Опитайте отново.")
        return

    # ============================================================
    # STEP 3: Enable and configure TVHeadend
    # ============================================================
    pDialog = xbmcgui.DialogProgress()
    pDialog.create("[COLOR red]BGTV[/COLOR] Съветник", "Активиране на PVR клиента...")
    pDialog.update(20)

    enable_pvr()
    xbmc.sleep(2000)
    pDialog.update(40, "Записване на настройките...")

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
</settings>'''.format(host='bgtv.pw', http_port='9981', htsp_port='9982', user=username, password=password)

    root_settings_xml = '''<?xml version="1.0" encoding="utf-8" standalone="yes"?>
<settings version="1">
    <setting id="host">{host}</setting>
    <setting id="http_port">{http_port}</setting>
    <setting id="htsp_port">{htsp_port}</setting>
    <setting id="user">{user}</setting>
    <setting id="pass">{password}</setting>
    <setting id="epg_async">true</setting>
</settings>'''.format(host='bgtv.pw', http_port='9981', htsp_port='9982', user=username, password=password)

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
            xbmc.log("BGTV Setup Error: " + filepath + ": " + str(e), xbmc.LOGERROR)
            success = False

    pDialog.update(90, "Почти готово...")
    xbmc.sleep(1000)
    pDialog.close()

    if not success:
        dialog.ok("Грешка", "Проблем при записване на настройките.")
        return

    restart = dialog.yesno(
        "Успех! ✅",
        "BGTV е настроена!\n\n"
        "Сървър: bgtv.pw\n"
        "Потребител: {user}\n\n"
        "Kodi трябва да се рестартира.\n"
        "Да го затворя ли сега?".format(user=username)
    )

    if restart:
        xbmc.executebuiltin('Quit')

if __name__ == '__main__':
    run()
