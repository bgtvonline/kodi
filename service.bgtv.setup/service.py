# -*- coding: utf-8 -*-
# service.bgtv.setup/service.py

import json
import os
import xbmc
import xbmcgui
import xbmcvfs
import xbmcaddon

ADDON_ID = "service.bgtv.setup"
PVR_ADDON_ID = "pvr.hts"

# TVHeadend endpoint
HOST = "bgtv.pw"
HTTP_PORT = "9981"
HTSP_PORT = "9982"

# --- timing (keep modest; we avoid long waits) ---
BOOT_SETTLE_MS = 3000
AFTER_ENABLE_MS = 4000


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
        return {"error": {"message": "Invalid JSON-RPC"}, "raw": raw}


def vfs_path(path):
    return path.replace("\\", "/")


def addon_data_dir():
    return vfs_path(xbmcvfs.translatePath(f"special://profile/addon_data/{ADDON_ID}/"))


def state_path():
    return vfs_path(os.path.join(addon_data_dir(), "state.json"))


def vfs_read_json(path, default):
    try:
        if not xbmcvfs.exists(path):
            return default
        f = xbmcvfs.File(path)
        data = f.read()
        f.close()
        if isinstance(data, bytes):
            data = data.decode("utf-8", errors="replace")
        return json.loads(data) if data else default
    except Exception as e:
        log(f"Failed reading state: {e}", xbmc.LOGWARNING)
        return default


def vfs_write_json(path, obj):
    try:
        d = os.path.dirname(path)
        if not xbmcvfs.exists(d):
            xbmcvfs.mkdirs(d)
        s = json.dumps(obj, ensure_ascii=False, indent=2)
        f = xbmcvfs.File(path, "w")
        try:
            f.write(s.encode("utf-8"))
        except Exception:
            f.write(s)
        f.close()
        return True
    except Exception as e:
        log(f"Failed writing state: {e}", xbmc.LOGERROR)
        return False


def pvr_present():
    try:
        r = jsonrpc("Addons.GetAddonDetails", {"addonid": PVR_ADDON_ID, "properties": ["enabled"]})
        return "result" in r and r["result"].get("addon") is not None
    except Exception:
        return False


def pvr_enabled():
    try:
        r = jsonrpc("Addons.GetAddonDetails", {"addonid": PVR_ADDON_ID, "properties": ["enabled"]})
        return bool(r.get("result", {}).get("addon", {}).get("enabled", False))
    except Exception:
        return False


def set_pvr_enabled(enabled):
    try:
        jsonrpc("Addons.SetAddonEnabled", {"addonid": PVR_ADDON_ID, "enabled": bool(enabled)})
        log(f"Set pvr.hts enabled={enabled}")
        return True
    except Exception as e:
        log(f"SetAddonEnabled failed: {e}", xbmc.LOGWARNING)
        return False


def pvr_get_setting(key):
    try:
        a = xbmcaddon.Addon(PVR_ADDON_ID)
        if hasattr(a, "getSettingString"):
            return a.getSettingString(key)
        return a.getSetting(key)
    except Exception:
        return ""


def pvr_set_setting(key, value):
    try:
        a = xbmcaddon.Addon(PVR_ADDON_ID)
        if hasattr(a, "setSettingString"):
            a.setSettingString(key, str(value))
        else:
            a.setSetting(key, str(value))
        log(f"Set pvr.hts setting {key}={value}")
        return True
    except Exception as e:
        log(f"Failed to set pvr.hts setting {key}: {e}", xbmc.LOGWARNING)
        return False


def is_really_configured(expected_user=None):
    """
    Do NOT trust our state file. Check pvr.hts actual settings.
    """
    host = (pvr_get_setting("host") or "").strip().lower()
    user = (pvr_get_setting("user") or "").strip()
    if host != HOST.lower():
        return False
    if not user:
        return False
    if expected_user and user != expected_user:
        # optional strictness; usually keep false to allow user changes later
        return False
    return True


def ensure_install_flow(state):
    """
    Production approach:
    - If missing and we haven't requested install -> trigger InstallAddon + set install_pending + exit.
    - If install_pending and still missing -> exit quietly (Kodi is still doing its thing).
    - If now present -> clear install_pending and continue.
    """
    dialog = xbmcgui.Dialog()

    if pvr_present():
        if state.get("install_pending"):
            state["install_pending"] = False
        return True

    if state.get("install_pending"):
        # Don't spam dialogs; Kodi may still be downloading or waiting for prompts.
        dialog.notification("BGTV", "Installing TVHeadend client... (accept Kodi prompts)", xbmcgui.NOTIFICATION_INFO, 5000)
        return False

    # First time: ask permission, then trigger install and exit.
    if not dialog.yesno(
        "BGTV Setup",
        "TVHeadend HTSP Client is required.\n\n"
        "Kodi will download it now.\n"
        "If Kodi asks for dependencies, press YES/OK.\n\n"
        "Start download?"
    ):
        return False

    log("Triggering InstallAddon(pvr.hts)")
    xbmc.executebuiltin(f"InstallAddon({PVR_ADDON_ID})")

    state["install_pending"] = True

    dialog.ok(
        "BGTV Setup",
        "Download started.\n\n"
        "If Kodi shows prompts, press YES/OK.\n\n"
        "When finished, restart Kodi (recommended) and BGTV Setup will continue."
    )
    return False


def apply_settings(username, password):
    """
    Try API first (requires pvr.hts enabled), fall back to XML.
    """
    ok = True
    ok &= pvr_set_setting("host", HOST)
    ok &= pvr_set_setting("http_port", HTTP_PORT)
    ok &= pvr_set_setting("htsp_port", HTSP_PORT)
    ok &= pvr_set_setting("user", username)
    ok &= pvr_set_setting("pass", password)

    pvr_set_setting("epg_async", "true")
    pvr_set_setting("connect_timeout", "10")
    pvr_set_setting("response_timeout", "5")

    return ok


def vfs_write_text(path, text):
    try:
        d = os.path.dirname(path).replace("\\", "/")
        if not xbmcvfs.exists(d):
            xbmcvfs.mkdirs(d)
        f = xbmcvfs.File(path, "w")
        try:
            f.write(text.encode("utf-8"))
        except Exception:
            f.write(text)
        f.close()
        log(f"Wrote {path}")
        return True
    except Exception as e:
        log(f"Write failed {path}: {e}", xbmc.LOGERROR)
        return False


def vfs_read_text(path):
    try:
        if not xbmcvfs.exists(path):
            return ""
        f = xbmcvfs.File(path)
        data = f.read()
        f.close()
        if isinstance(data, bytes):
            data = data.decode("utf-8", errors="replace")
        return data or ""
    except Exception:
        return ""


def apply_settings_xml(username, password):
    """Write settings.xml directly via xbmcvfs. Works even when pvr.hts is disabled."""
    instance_path = f"special://profile/addon_data/{PVR_ADDON_ID}/instances/instance-1/settings.xml"
    legacy_path   = f"special://profile/addon_data/{PVR_ADDON_ID}/settings.xml"

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

    ok1 = vfs_write_text(instance_path, instance_xml)
    ok2 = vfs_write_text(legacy_path, legacy_xml)

    # Verify it really stuck (at least instance-1)
    txt = vfs_read_text(instance_path)
    verified = (HOST in txt) and (f'<setting id="user">{username}</setting>' in txt)

    if not verified:
        log("Verification FAILED: instance-1 settings.xml does not contain expected host/user", xbmc.LOGERROR)

    return ok1 and ok2 and verified


def activate_tv():
    # Try common windows. (Skins vary; we just best-effort.)
    for cmd in ("ActivateWindow(TVChannels)", "ActivateWindow(TVGuide)"):
        try:
            xbmc.executebuiltin(cmd)
            return True
        except Exception:
            pass
    return False


def wait_boot_settle(monitor):
    # Give Kodi time to bring up GUI / JSONRPC etc.
    xbmc.sleep(BOOT_SETTLE_MS)
    # wait a bit more if still starting
    for _ in range(10):
        if monitor.abortRequested():
            return
        # when GUI is up, home window is typically visible
        if xbmc.getCondVisibility("Window.IsVisible(home)"):
            break
        xbmc.sleep(500)


def run():
    monitor = xbmc.Monitor()
    wait_boot_settle(monitor)

    spath = state_path()
    state = vfs_read_json(spath, default={
        "configured": False,
        "install_pending": False,
        "needs_enable_on_next_boot": False,
        "open_tv_pending": False,
    })

    # If state claims configured but pvr.hts is NOT actually pointing to bgtv.pw -> reset state
    if state.get("configured") and not is_really_configured():
        log("State says configured, but pvr.hts settings are not applied. Resetting state.")
        state.update({
            "configured": False,
            "install_pending": False,
            "needs_enable_on_next_boot": False,
            "open_tv_pending": False,
        })
        vfs_write_json(spath, state)

    # If we are in "enable after reboot" phase, do it now
    if state.get("configured") and state.get("needs_enable_on_next_boot"):
        log("Phase B: enabling pvr.hts after reboot")
        set_pvr_enabled(True)
        xbmc.sleep(AFTER_ENABLE_MS)
        state["needs_enable_on_next_boot"] = False
        vfs_write_json(spath, state)

        # Open TV once (optional)
        if state.get("open_tv_pending"):
            xbmc.sleep(1000)
            activate_tv()
            state["open_tv_pending"] = False
            vfs_write_json(spath, state)
        return

    # If already configured and nothing pending, optionally open TV once
    if state.get("configured") and state.get("open_tv_pending"):
        log("Configured already; opening TV section once.")
        xbmc.sleep(1000)
        activate_tv()
        state["open_tv_pending"] = False
        vfs_write_json(spath, state)
        return

    if state.get("configured"):
        return

    # --- Phase A: ensure pvr installed (non-blocking, no timeouts) ---
    if not ensure_install_flow(state):
        vfs_write_json(spath, state)
        return

    # Disable pvr.hts first so it stops running with 127.0.0.1 defaults
    set_pvr_enabled(False)
    xbmc.sleep(1500)

    # Ask for credentials
    dialog = xbmcgui.Dialog()
    dialog.ok("BGTV Setup", "Enter your BGTV username and password.")

    username = dialog.input("BGTV username:", type=xbmcgui.INPUT_ALPHANUM)
    if not username:
        dialog.ok("Cancelled", "No username entered.")
        return

    password = dialog.input("BGTV password:", type=xbmcgui.INPUT_ALPHANUM, option=xbmcgui.ALPHANUM_HIDE_INPUT)
    if not password:
        dialog.ok("Cancelled", "No password entered.")
        return

    # Write settings via XML (works even when pvr.hts is disabled)
    log("Writing settings via XML while pvr.hts is disabled")
    ok = apply_settings_xml(username, password)
    if not ok:
        dialog.ok("BGTV Setup", "Failed to write settings.xml (see Kodi log).")
        return

    # Keep pvr.hts disabled. On next boot our service enables it with correct settings.
    set_pvr_enabled(False)
    xbmc.sleep(1000)

    # Mark state for next boot
    state["configured"] = True
    state["needs_enable_on_next_boot"] = True
    state["open_tv_pending"] = True
    vfs_write_json(spath, state)

    dialog.ok("BGTV Setup", "Settings saved.\n\nKodi will now restart to start Live TV.")
    xbmc.executebuiltin("Quit")


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        log(f"Fatal error: {e}", xbmc.LOGERROR)