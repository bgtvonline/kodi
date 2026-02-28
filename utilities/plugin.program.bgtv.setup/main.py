import os
import xbmc
import xbmcgui
import xbmcvfs
import json

def is_pvr_installed():
    """Check if pvr.hts is truly installed and available"""
    try:
        request = json.dumps({
            "jsonrpc": "2.0",
            "method": "Addons.GetAddonDetails",
            "params": {"addonid": "pvr.hts", "properties": ["installed", "enabled"]},
            "id": 1
        })
        response = json.loads(xbmc.executeJSONRPC(request))
        if 'result' in response:
            addon = response['result']['addon']
            return addon.get('installed', False)
        return False
    except:
        return False

def run():
    dialog = xbmcgui.Dialog()

    # ============================================================
    # STEP 1: Check if PVR client is installed. If not, install it.
    # ============================================================
    if not is_pvr_installed():
        # Tell user EXACTLY what to do
        dialog.ok(
            "[COLOR red]BGTV[/COLOR] Съветник",
            "За да гледате телевизия, е нужен PVR клиент.\n\n"
            "След като натиснете [COLOR yellow]OK[/COLOR], Kodi ще ви\n"
            "попита дали искате да го инсталирате.\n\n"
            "[COLOR green]Натиснете YES / ДА![/COLOR]"
        )
        # User clicked OK - our dialog is now CLOSED
        # Trigger the install - Kodi's native dialog should appear unblocked
        xbmc.executebuiltin('InstallAddon(pvr.hts)')

        # Wait silently (no progress dialog!) for up to 90 seconds
        # This gives the user time to see Kodi's dialog and click Yes
        installed = False
        for i in range(90):
            xbmc.sleep(1000)
            if is_pvr_installed():
                installed = True
                break

        if not installed:
            dialog.ok(
                "PVR не е инсталиран",
                "Изглежда PVR клиентът не беше инсталиран.\n\n"
                "Моля стартирайте Съветника отново и\n"
                "натиснете [COLOR green]YES / ДА[/COLOR] когато Kodi ви попита."
            )
            return

        # Success notification
        dialog.notification('BGTV', 'PVR клиентът е инсталиран!', xbmcgui.NOTIFICATION_INFO, 3000)
        xbmc.sleep(1000)

    # ============================================================
    # STEP 2: PVR is installed. Now ask for credentials.
    # ============================================================
    dialog.ok(
        "[COLOR red]BGTV[/COLOR] Съветник",
        "PVR клиентът е готов!\n\n"
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
    # STEP 3: Configure TVHeadend with BGTV server details
    # ============================================================
    pDialog = xbmcgui.DialogProgress()
    pDialog.create("[COLOR red]BGTV[/COLOR] Съветник", "Активиране на PVR клиента...")
    pDialog.update(20)

    xbmc.executebuiltin('EnableAddon(pvr.hts)')
    xbmc.sleep(2000)
    pDialog.update(40, "Записване на настройките...")

    # Kodi 20+ multi-instance settings
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

    # Legacy root settings (Kodi 19 and below)
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
        "BGTV е настроена!\n\nСървър: bgtv.pw\nПотребител: {user}\n\nKodi трябва да се рестартира.\nДа го затворя ли сега?".format(user=username)
    )

    if restart:
        xbmc.executebuiltin('Quit')

if __name__ == '__main__':
    run()
