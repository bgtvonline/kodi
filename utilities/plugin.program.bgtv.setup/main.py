import os
import xbmc
import xbmcgui
import xbmcvfs
import json
import time

ADDON_ID = 'pvr.hts'
HOST = 'bgtv.pw'
HTTP_PORT = '9981'
HTSP_PORT = '9982'


def jsonrpc(method, params=None):
    """Execute a JSON-RPC call and return the response dict."""
    payload = {"jsonrpc": "2.0", "method": method, "id": 1}
    if params:
        payload["params"] = params
    return json.loads(xbmc.executeJSONRPC(json.dumps(payload)))


def is_pvr_installed():
    """Check if pvr.hts is installed."""
    try:
        resp = jsonrpc("Addons.GetAddonDetails",
                       {"addonid": ADDON_ID, "properties": ["installed", "enabled"]})
        return 'result' in resp
    except:
        return False


def is_pvr_enabled():
    """Check if pvr.hts is enabled."""
    try:
        resp = jsonrpc("Addons.GetAddonDetails",
                       {"addonid": ADDON_ID, "properties": ["installed", "enabled"]})
        return resp.get('result', {}).get('addon', {}).get('enabled', False)
    except:
        return False


def set_pvr_enabled(enabled):
    """Enable or disable pvr.hts."""
    try:
        jsonrpc("Addons.SetAddonEnabled",
                {"addonid": ADDON_ID, "enabled": enabled})
    except:
        pass


def get_addon_data_path():
    """Get the addon_data path for pvr.hts."""
    return xbmcvfs.translatePath('special://profile/addon_data/{}/'.format(ADDON_ID))


def write_settings(username, password):
    """
    Write pvr.hts settings to ALL known locations.
    Covers Kodi 19 (Matrix), 20 (Nexus), and 21 (Omega).
    """
    addon_data = get_addon_data_path()

    # Kodi 20+ instance-based settings (primary)
    instance_xml = """<?xml version="1.0" encoding="utf-8" standalone="yes"?>
<settings version="2">
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
    <setting id="auto_rec_use_regex">false</setting>
    <setting id="total_tuners">0</setting>
    <setting id="pretuner_closedelay">10</setting>
    <setting id="autorec_approxtime">0</setting>
    <setting id="autorec_maxdiff">15</setting>
    <setting id="streaming_protocol">0</setting>
</settings>""".format(host=HOST, http_port=HTTP_PORT, htsp_port=HTSP_PORT,
                      user=username, password=password)

    # Legacy root-level settings (Kodi 19 and below, also read by some builds)
    root_xml = """<?xml version="1.0" encoding="utf-8" standalone="yes"?>
<settings version="2">
    <setting id="host">{host}</setting>
    <setting id="http_port">{http_port}</setting>
    <setting id="htsp_port">{htsp_port}</setting>
    <setting id="user">{user}</setting>
    <setting id="pass">{password}</setting>
    <setting id="epg_async">true</setting>
</settings>""".format(host=HOST, http_port=HTTP_PORT, htsp_port=HTSP_PORT,
                      user=username, password=password)

    paths_to_write = [
        # Kodi 20+ primary location
        (os.path.join(addon_data, 'instances', 'instance-1', 'settings.xml'), instance_xml),
        # Legacy / fallback location
        (os.path.join(addon_data, 'settings.xml'), root_xml),
    ]

    success = True
    for filepath, content in paths_to_write:
        dirpath = os.path.dirname(filepath)
        if not os.path.exists(dirpath):
            try:
                os.makedirs(dirpath)
            except OSError:
                pass
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            xbmc.log("BGTV Setup: Wrote settings to " + filepath, xbmc.LOGINFO)
        except Exception as e:
            xbmc.log("BGTV Setup ERROR writing " + filepath + ": " + str(e), xbmc.LOGERROR)
            success = False

    return success


def try_install_pvr():
    """
    Fallback: Should rarely be hit now that pvr.hts is a required dependency in addon.xml.
    If hit, it means the dependency resolution failed (e.g., repository is missing the client).
    """
    dialog = xbmcgui.Dialog()

    dialog.ok(
        "[COLOR red]BGTV[/COLOR] Съветник",
        "Липсва TVHeadend клиент.\n\n"
        "Опитахме да го инсталираме автоматично, но устройството ви може "
        "да изисква ръчна инсталация.\n\n"
        "Ще отворя търсачката. Напишете [COLOR yellow]tvheadend[/COLOR]\n"
        "отворете го и натиснете [COLOR green]Install[/COLOR]."
    )
    
    xbmc.executebuiltin('ActivateWindow(10040,"addons://search/",return)')
    return False


def run():
    dialog = xbmcgui.Dialog()

    # ============================================================
    # STEP 1: Check if PVR client is installed
    # ============================================================
    if not is_pvr_installed():
        installed = try_install_pvr()
        if not installed:
            # User was directed to install manually
            return

    # ============================================================
    # STEP 2: PVR is installed — disable it before writing settings
    # ============================================================
    was_enabled = is_pvr_enabled()

    dialog.ok(
        "[COLOR red]BGTV[/COLOR] Съветник",
        "TVHeadend PVR клиентът е намерен!\n\n"
        "Сега въведете вашите BGTV данни за достъп."
    )

    username = dialog.input(
        'Въведете вашето BGTV потребителско име:',
        type=xbmcgui.INPUT_ALPHANUM
    )
    if not username:
        dialog.ok("Отказано", "Не въведохте потребителско име. Опитайте отново.")
        return

    password = dialog.input(
        'Въведете вашата парола:',
        type=xbmcgui.INPUT_ALPHANUM,
        option=xbmcgui.ALPHANUM_HIDE_INPUT
    )
    if not password:
        dialog.ok("Отказано", "Не въведохте парола. Опитайте отново.")
        return

    # ============================================================
    # STEP 3: Disable PVR, write settings, then re-enable
    # ============================================================
    pDialog = xbmcgui.DialogProgress()
    pDialog.create("[COLOR red]BGTV[/COLOR] Съветник", "Подготовка...")
    pDialog.update(10)

    # CRITICAL: Disable pvr.hts so it doesn't overwrite our settings
    if was_enabled:
        xbmc.log("BGTV Setup: Disabling pvr.hts before writing settings", xbmc.LOGINFO)
        set_pvr_enabled(False)
        pDialog.update(20, "Спиране на PVR клиента...")
        xbmc.sleep(2000)  # Give Kodi time to fully unload the addon

    # Write settings while pvr.hts is stopped
    pDialog.update(40, "Записване на настройките...")
    success = write_settings(username, password)

    if not success:
        pDialog.close()
        dialog.ok("Грешка", "Проблем при записване на настройките.")
        # Re-enable if it was enabled before
        if was_enabled:
            set_pvr_enabled(True)
        return

    pDialog.update(60, "Записването е готово...")
    xbmc.sleep(500)

    # Now re-enable pvr.hts — it will load our freshly written settings
    pDialog.update(70, "Стартиране на PVR клиента...")
    set_pvr_enabled(True)
    xbmc.sleep(3000)  # Give it time to connect to TVHeadend

    pDialog.update(90, "Почти готово...")
    xbmc.sleep(500)
    pDialog.close()

    # ============================================================
    # STEP 4: Offer to verify settings or restart
    # ============================================================
    choice = dialog.yesno(
        "Успех! ✅",
        "BGTV е настроена!\n\n"
        "Сървър: {host}\n"
        "Потребител: {user}\n\n"
        "Kodi трябва да се рестартира.\n"
        "Да го затворя ли сега?".format(host=HOST, user=username)
    )

    if choice:
        xbmc.executebuiltin('Quit')


if __name__ == '__main__':
    run()
