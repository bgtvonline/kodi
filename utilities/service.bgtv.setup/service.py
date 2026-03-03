# service.bgtv.setup/service.py
import json
import re
import os
import xbmc
import xbmcgui
import xbmcvfs
import xbmcaddon

ADDON_ID = "service.bgtv.setup"
PVR_ADDON_ID = "pvr.hts"

# BGTV / TVHeadend endpoint
HOST = "bgtv.pw"
HTTP_PORT = "9981"
HTSP_PORT = "9982"

# Timing
INSTALL_WAIT_SECONDS = 120
CONNECT_SETTLE_MS = 3000


def log(msg, level=xbmc.LOGINFO):
    xbmc.log(f"[BGTV Setup] {msg}", level)


def jsonrpc(method, params=None):
    payload = {"jsonrpc": "2.0", "method": method, "id": 1}
    if params is not None:
        payload["params"] = params
    raw = xbmc.executeJSONRPC(json.dumps(payload))
    try:
        return json.loads(raw)
    except Exception:
        return {"error": {"message": "Invalid JSON-RPC response"}, "raw": raw}


def addon_data_path():
    # e.g. special://profile/addon_data/service.bgtv.setup/
    return xbmcvfs.translatePath(f"special://profile/addon_data/{ADDON_ID}/").replace("\\", "/")


def state_file_path():
    return (addon_data_path() + "state.json").replace("\\", "/")


def vfs_exists(path):
    try:
        return xbmcvfs.exists(path)
    except Exception:
        return False


def vfs_mkdirs(path):
    try:
        if not xbmcvfs.exists(path):
            return xbmcvfs.mkdirs(path)
        return True
    except Exception:
        return False


def vfs_read_json(path, default):
    try:
        if not vfs_exists(path):
            return default
        f = xbmcvfs.File(path)
        data = f.read()
        f.close()
        if isinstance(data, bytes):
            data = data.decode("utf-8", errors="replace")
        return json.loads(data) if data else default
    except Exception as e:
        log(f"Failed to read state file: {e}", xbmc.LOGWARNING)
        return default


def vfs_write_json(path, obj):
    try:
        base = os.path.dirname(path).replace("\\", "/")
        vfs_mkdirs(base)
        s = json.dumps(obj, ensure_ascii=False, indent=2)
        f = xbmcvfs.File(path, "w")
        # xbmcvfs.File can require bytes on some platforms
        try:
            f.write(s.encode("utf-8"))
        except Exception:
            f.write(s)
        f.close()
        return True
    except Exception as e:
        log(f"Failed to write state file: {e}", xbmc.LOGERROR)
        return False


def pvr_present():
    # Treat “addon details returned” as present/installed.
    try:
        resp = jsonrpc("Addons.GetAddonDetails", {"addonid": PVR_ADDON_ID, "properties": ["enabled"]})
        return "result" in resp and resp["result"].get("addon") is not None
    except Exception:
        return False


def pvr_enabled():
    try:
        resp = jsonrpc("Addons.GetAddonDetails", {"addonid": PVR_ADDON_ID, "properties": ["enabled"]})
        return bool(resp.get("result", {}).get("addon", {}).get("enabled", False))
    except Exception:
        return False


def set_pvr_enabled(enabled):
    try:
        jsonrpc("Addons.SetAddonEnabled", {"addonid": PVR_ADDON_ID, "enabled": bool(enabled)})
        return True
    except Exception as e:
        log(f"SetAddonEnabled failed: {e}", xbmc.LOGWARNING)
        return False


def wait_for_pvr_install(monitor):
    # Wait until pvr.hts shows up as present
    for i in range(INSTALL_WAIT_SECONDS):
        if monitor.abortRequested():
            return False
        if pvr_present():
            return True
        xbmc.sleep(1000)
    return False


def _special(path):
    # Ensure clean VFS path
    return path.replace("\\", "/")

def _vfs_read_text(path):
    try:
        if not xbmcvfs.exists(path):
            return ""
        f = xbmcvfs.File(path)
        data = f.read()
        f.close()
        if isinstance(data, bytes):
            data = data.decode("utf-8", errors="replace")
        return data or ""
    except Exception as e:
        log(f"Read failed {path}: {e}", xbmc.LOGERROR)
        return ""

def _vfs_write_text(path, text):
    try:
        dirpath = os.path.dirname(path).replace("\\", "/")
        if not xbmcvfs.exists(dirpath):
            xbmcvfs.mkdirs(dirpath)
        f = xbmcvfs.File(path, "w")
        try:
            f.write(text.encode("utf-8"))
        except Exception:
            f.write(text)
        f.close()
        return True
    except Exception as e:
        log(f"Write failed {path}: {e}", xbmc.LOGERROR)
        return False

def _list_instance_settings():
    base = _special(f"special://profile/addon_data/{PVR_ADDON_ID}/instances/")
    out = []
    try:
        if xbmcvfs.exists(base):
            dirs, _files = xbmcvfs.listdir(base)
            for d in dirs:
                if d.lower().startswith("instance-"):
                    out.append(_special(base + d + "/settings.xml"))
    except Exception as e:
        log(f"List instances failed: {e}", xbmc.LOGWARNING)
    return out

def write_pvr_settings(username, password):
    """
    Hardened: writes to special:// paths + verifies written content.
    """
    legacy_path = _special(f"special://profile/addon_data/{PVR_ADDON_ID}/settings.xml")
    instance_default = _special(f"special://profile/addon_data/{PVR_ADDON_ID}/instances/instance-1/settings.xml")

    instance_xml = f"""<?xml version="1.0" encoding="utf-8" standalone="yes"?>
<settings version="2">
  <setting id="host">{HOST}</setting>
  <setting id="http_port">{HTTP_PORT}</setting>
  <setting id="htsp_port">{HTSP_PORT}</setting>
  <setting id="user">{username}</setting>
  <setting id="pass">{password}</setting>
  <setting id="connect_timeout">10</setting>
  <setting id="response_timeout">5</setting>
  <setting id="epg_async">true</setting>
  <setting id="streaming_protocol">0</setting>
</settings>
"""

    legacy_xml = f"""<?xml version="1.0" encoding="utf-8" standalone="yes"?>
<settings version="2">
  <setting id="host">{HOST}</setting>
  <setting id="http_port">{HTTP_PORT}</setting>
  <setting id="htsp_port">{HTSP_PORT}</setting>
  <setting id="user">{username}</setting>
  <setting id="pass">{password}</setting>
  <setting id="epg_async">true</setting>
</settings>
"""

    # Always write legacy
    targets = [(legacy_path, legacy_xml)]

    # Ensure at least instance-1 exists as a target
    targets.append((instance_default, instance_xml))

    # Also write to any existing instance settings.xml
    for p in _list_instance_settings():
        targets.append((p, instance_xml))

    ok = True
    for path, content in targets:
        if _vfs_write_text(path, content):
            log(f"Wrote settings to {path}")
        else:
            ok = False

    # Verify: host + user appear in at least one instance file (preferred), else legacy
    def looks_configured(txt):
        return (HOST in txt) and (f'<setting id="user">{username}</setting>' in txt)

    instance_files = _list_instance_settings()
    verified = False

    for p in instance_files:
        if looks_configured(_vfs_read_text(p)):
            verified = True
            break

    if not verified:
        # fallback verification against instance-1 and legacy
        if looks_configured(_vfs_read_text(instance_default)) or looks_configured(_vfs_read_text(legacy_path)):
            verified = True

    if not verified:
        log("Settings write verification FAILED: Kodi is not seeing bgtv.pw/user in settings files.", xbmc.LOGERROR)
        ok = False

    return ok


def set_pvr_setting(key, value):
    """
    Best-effort: set pvr.hts setting via Kodi addon settings API.
    This is often more reliable than writing XML manually on Kodi 20/21.
    """
    try:
        a = xbmcaddon.Addon(PVR_ADDON_ID)
        # Kodi 19+ supports setSettingString, older uses setSetting
        if hasattr(a, "setSettingString"):
            a.setSettingString(key, str(value))
        else:
            a.setSetting(key, str(value))
        log(f"Set pvr.hts setting: {key}={value}")
        return True
    except Exception as e:
        log(f"Failed to set pvr.hts setting {key}: {e}", xbmc.LOGWARNING)
        return False


def apply_pvr_settings(username, password):
    """
    Apply settings using the API first; fall back to XML write.
    """
    ok_api = True
    ok_api &= set_pvr_setting("host", HOST)
    ok_api &= set_pvr_setting("http_port", str(HTTP_PORT))
    ok_api &= set_pvr_setting("htsp_port", str(HTSP_PORT))
    ok_api &= set_pvr_setting("user", username)
    ok_api &= set_pvr_setting("pass", password)

    # Some builds use these ids; harmless if ignored
    set_pvr_setting("epg_async", "true")
    set_pvr_setting("connect_timeout", "10")
    set_pvr_setting("response_timeout", "5")

    # If API worked, return True. If it failed, try XML fallback.
    if ok_api:
        return True

    # Fallback: XML write (hardened version)
    return write_pvr_settings(username, password)


def activate_tv_section():
    # Builtins differ a bit by skin/version; try a few.
    candidates = [
        "ActivateWindow(TVChannels)",
        "ActivateWindow(TVGuide)",
        "ActivateWindow(TVRecordings)",
        # fallback: old-style numeric window ids are risky; avoid unless necessary
    ]
    for c in candidates:
        try:
            xbmc.executebuiltin(c)
            return True
        except Exception:
            continue
    return False


def run_wizard():
    monitor = xbmc.Monitor()
    dialog = xbmcgui.Dialog()

    # Load state
    state_path = state_file_path()
    state = vfs_read_json(state_path, default={"configured": False, "open_tv_pending": False})

    # If configured and we still want to auto-open TV once (post-restart)
    if state.get("configured") and state.get("open_tv_pending"):
        log("Configured already; opening TV section once.")
        xbmc.sleep(1500)
        activate_tv_section()
        state["open_tv_pending"] = False
        vfs_write_json(state_path, state)
        return

    # If configured and nothing pending, do nothing
    if state.get("configured"):
        return

    # --- Step 1: Ensure PVR installed ---
    if not pvr_present():
        install_now = dialog.yesno(
            "[COLOR red]BGTV[/COLOR] Setup",
            "TVHeadend client (pvr.hts) is missing.\n\n"
            "Install it now? Kodi may ask to install dependencies.\n\n"
            "Choose [COLOR green]Yes[/COLOR] and accept any prompts."
        )
        if not install_now:
            return

        log("Triggering InstallAddon(pvr.hts)")
        xbmc.executebuiltin(f"InstallAddon({PVR_ADDON_ID})")

        p = xbmcgui.DialogProgress()
        p.create("[COLOR red]BGTV[/COLOR]", "Installing TVHeadend client...")
        installed = False

        for i in range(INSTALL_WAIT_SECONDS):
            if monitor.abortRequested() or p.iscanceled():
                break
            if pvr_present():
                installed = True
                break
            pct = int((i / float(INSTALL_WAIT_SECONDS)) * 100)
            p.update(pct, "Installing...\nIf Kodi asks, select OK/Yes.")
            xbmc.sleep(1000)

        p.close()

        if not installed:
            dialog.ok(
                "[COLOR red]BGTV[/COLOR] Setup",
                "Automatic install did not complete.\n\n"
                "Please install manually:\n"
                "Add-ons → Download → PVR clients → TVHeadend HTSP Client\n\n"
                "Then run BGTV Setup again."
            )
            try:
                xbmc.executebuiltin('ActivateWindow(10040,"addons://search/",return)')
            except Exception:
                pass
            return

    # Immediately disable pvr.hts after install to prevent it from
    # initializing with defaults (127.0.0.1) before we write our settings
    if pvr_present():
        log("Disabling pvr.hts immediately after install to prevent default init")
        set_pvr_enabled(False)
        xbmc.sleep(1500)

    # --- Step 2: Ask for credentials ---
    dialog.ok(
        "[COLOR red]BGTV[/COLOR] Setup",
        "TVHeadend client found.\n\n"
        "Enter your BGTV username and password."
    )

    username = dialog.input("BGTV username:", type=xbmcgui.INPUT_ALPHANUM)
    if not username:
        dialog.ok("Cancelled", "No username entered.")
        return

    password = dialog.input(
        "BGTV password:",
        type=xbmcgui.INPUT_ALPHANUM,
        option=xbmcgui.ALPHANUM_HIDE_INPUT
    )
    if not password:
        dialog.ok("Cancelled", "No password entered.")
        return

    # --- Step 3: Stop PVR, apply settings (API first, XML fallback), re-enable ---
    # Always force-disable before writing, even if already stopped
    set_pvr_enabled(False)
    xbmc.sleep(1500)

    prog = xbmcgui.DialogProgress()
    prog.create("[COLOR red]BGTV[/COLOR] Setup", "Preparing...")
    prog.update(10, "Preparing...")

    prog.update(45, "Writing settings...")
    ok = apply_pvr_settings(username, password)
    if not ok:
        prog.close()
        dialog.ok("Error", "Failed to apply TVHeadend settings.")
        return

    prog.update(70, "Starting PVR client...")
    set_pvr_enabled(True)
    xbmc.sleep(CONNECT_SETTLE_MS)

    prog.update(90, "Finalizing...")
    xbmc.sleep(500)
    prog.close()

    # --- Step 4: Mark configured; set open TV pending (after restart) ---
    state["configured"] = True
    state["open_tv_pending"] = True
    vfs_write_json(state_path, state)

    # --- Step 5: Restart (most reliable) ---
    restart_now = dialog.yesno(
        "Success ✅",
        f"BGTV is configured!\n\nServer: {HOST}\nUser: {username}\n\n"
        "Kodi should restart to apply PVR cleanly.\n\nRestart now?"
    )
    if restart_now:
        xbmc.executebuiltin("Quit")
    else:
        dialog.ok(
            "Note",
            "If TV doesn’t appear immediately, restart Kodi manually.\n"
            "After restart, BGTV Setup will open the TV section once."
        )


if __name__ == "__main__":
    try:
        # Service addons should stay lightweight; run once per boot.
        run_wizard()
    except Exception as e:
        log(f"Fatal error: {e}", xbmc.LOGERROR)