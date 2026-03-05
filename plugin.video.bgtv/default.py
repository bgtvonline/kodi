# -*- coding: utf-8 -*-
# plugin.video.bgtv/default.py
# Browse and play BGTV channels via XC API

import sys
import json
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon

try:
    from urllib.request import urlopen, Request
    from urllib.parse import urlencode, parse_qs
except ImportError:
    from urllib2 import urlopen, Request
    from urllib import urlencode
    from urlparse import parse_qs

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo("id")
HANDLE = int(sys.argv[1])
BASE_URL = sys.argv[0]

API_URL = "http://bgtv.pw/player_api.php"
PICON_URL = "http://bgtv.pw/static/img/picons"


def log(msg, level=xbmc.LOGINFO):
    xbmc.log(f"[BGTV Player] {msg}", level)


def get_credentials():
    username = ADDON.getSetting("username")
    password = ADDON.getSetting("password")
    if not username or not password:
        xbmcgui.Dialog().ok(
            "BGTV",
            "Моля въведете потребителско име и парола в настройките.\n\n"
            "[COLOR gray](Please set username/password in addon settings.)[/COLOR]"
        )
        ADDON.openSettings()
        username = ADDON.getSetting("username")
        password = ADDON.getSetting("password")
    return username, password


def api_request(action, extra_params=None):
    username, password = get_credentials()
    if not username or not password:
        return None

    params = {"username": username, "password": password, "action": action}
    if extra_params:
        params.update(extra_params)

    url = f"{API_URL}?{urlencode(params)}"
    try:
        req = Request(url, headers={"User-Agent": "Kodi BGTV"})
        resp = urlopen(req, timeout=15)
        return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        log(f"API error: {e}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification("BGTV", "Грешка при свързване / Connection error",
                                       xbmcgui.NOTIFICATION_ERROR, 3000)
        return None


def build_url(params):
    return f"{BASE_URL}?{urlencode(params)}"


def list_categories():
    """Show category list (root menu)."""
    data = api_request("get_live_categories")
    if not data:
        return

    # Add "All Channels" entry
    li = xbmcgui.ListItem(label="[COLOR yellow]📺 Всички канали / All Channels[/COLOR]")
    li.setArt({"icon": "DefaultTVShows.png"})
    url = build_url({"mode": "channels", "cat_id": "all"})
    xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)

    for cat in data:
        cat_name = cat.get("category_name", "Unknown")
        cat_id = str(cat.get("category_id", ""))
        li = xbmcgui.ListItem(label=cat_name)
        li.setArt({"icon": "DefaultFolder.png"})
        url = build_url({"mode": "channels", "cat_id": cat_id})
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)

    xbmcplugin.endOfDirectory(HANDLE)


def list_channels(cat_id):
    """Show channels in a category."""
    data = api_request("get_live_streams", {"category_id": cat_id} if cat_id != "all" else None)
    if not data:
        return

    for ch in data:
        if cat_id != "all" and str(ch.get("category_id", "")) != cat_id:
            continue

        name = ch.get("name", "Unknown")
        stream_id = str(ch.get("stream_id", ""))
        icon = ch.get("stream_icon", "")

        # Try to use local picon name if no icon URL
        if not icon:
            from urllib.parse import quote
            icon = f"{PICON_URL}/{quote(name + '.png')}"

        li = xbmcgui.ListItem(label=name)
        li.setArt({"icon": icon, "thumb": icon})
        li.setInfo("video", {"title": name, "mediatype": "video"})
        li.setProperty("IsPlayable", "true")

        url = build_url({"mode": "play", "stream_id": stream_id, "name": name})
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=False)

    xbmcplugin.endOfDirectory(HANDLE)


def play_channel(stream_id, name):
    """Play a channel stream."""
    username, password = get_credentials()
    if not username:
        return

    stream_url = f"http://bgtv.pw/live/{username}/{password}/{stream_id}.ts"

    li = xbmcgui.ListItem(label=name, path=stream_url)
    li.setInfo("video", {"title": name})
    li.setProperty("inputstream", "inputstream.ffmpegdirect")
    li.setProperty("inputstream.ffmpegdirect.stream_mode", "timeshift")
    li.setProperty("inputstream.ffmpegdirect.is_realtime_stream", "true")
    li.setMimeType("video/mp2t")

    xbmcplugin.setResolvedUrl(HANDLE, True, li)
    log(f"Playing: {name} (stream_id={stream_id})")


def router():
    """Route based on URL parameters."""
    params = parse_qs(sys.argv[2].lstrip("?"))
    mode = params.get("mode", [None])[0]

    if mode is None:
        list_categories()
    elif mode == "channels":
        cat_id = params.get("cat_id", ["all"])[0]
        list_channels(cat_id)
    elif mode == "play":
        stream_id = params.get("stream_id", [""])[0]
        name = params.get("name", [""])[0]
        play_channel(stream_id, name)


if __name__ == "__main__":
    router()
