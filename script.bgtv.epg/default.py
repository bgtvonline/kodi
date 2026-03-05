# -*- coding: utf-8 -*-
# script.bgtv.epg/default.py
# Downloads BGTV channel logos (picons) into Kodi's icon cache

import xbmc
import xbmcgui
import xbmcvfs
import os

try:
    from urllib.request import urlopen, Request
    from urllib.parse import quote
except ImportError:
    from urllib2 import urlopen, Request
    from urllib import quote

ADDON_NAME = "BGTV Channel Logos"
PICON_BASE_URL = "http://bgtv.pw/static/img/picons"
LOCAL_PICON_DIR = xbmcvfs.translatePath("special://profile/addon_data/script.bgtv.epg/picons/")


def log(msg, level=xbmc.LOGINFO):
    xbmc.log(f"[BGTV Logos] {msg}", level)


def fetch_picon_list():
    """Get channel names from TVHeadend XMLTV to build picon filenames."""
    try:
        import xml.etree.ElementTree as ET
        req = Request("http://bgtv.pw:9981/xmltv/channels", headers={"User-Agent": "Kodi BGTV"})
        resp = urlopen(req, timeout=15)
        root = ET.fromstring(resp.read())
        names = []
        for ch in root.findall(".//channel"):
            name_el = ch.find("display-name")
            if name_el is not None and name_el.text:
                names.append(name_el.text.strip() + ".png")
        return names
    except Exception as e:
        log(f"Failed to fetch channel list: {e}", xbmc.LOGWARNING)
        return []


def download_picon(filename, dest_dir):
    """Download a single picon PNG."""
    try:
        url = f"{PICON_BASE_URL}/{quote(filename)}"
        req = Request(url, headers={"User-Agent": "Kodi BGTV"})
        resp = urlopen(req, timeout=10)
        data = resp.read()
        if len(data) < 100:
            return False
        dest = os.path.join(dest_dir, filename)
        with open(dest, "wb") as f:
            f.write(data)
        return True
    except Exception:
        return False


def main():
    dialog = xbmcgui.Dialog()

    choice = dialog.yesno(
        ADDON_NAME,
        "Изтегляне на логата на BGTV каналите?\n\n"
        "• 500+ лога на канали\n"
        "• Красиви икони в TV справочника\n\n"
        "[COLOR gray](Download 500+ BGTV channel logos?)[/COLOR]",
        yeslabel="Да / Yes",
        nolabel="Не / No"
    )
    if not choice:
        return

    pbar = xbmcgui.DialogProgress()
    pbar.create(ADDON_NAME, "Зареждане на списъка...\nFetching channel list...")

    picons = fetch_picon_list()
    if not picons:
        pbar.close()
        dialog.ok(ADDON_NAME, "Не можах да намеря лога.\n[COLOR gray](Could not fetch logo list.)[/COLOR]")
        return

    if not os.path.exists(LOCAL_PICON_DIR):
        os.makedirs(LOCAL_PICON_DIR)

    total = len(picons)
    success = 0
    failed = 0

    for i, name in enumerate(picons):
        if pbar.iscanceled():
            break
        pct = int((i / total) * 100)
        pbar.update(pct, f"Изтегляне: {name}\n{i+1}/{total}")
        if download_picon(name, LOCAL_PICON_DIR):
            success += 1
        else:
            failed += 1

    pbar.close()
    dialog.ok(
        ADDON_NAME,
        f"✅ Готово!\n\n"
        f"Изтеглени: {success} лога\nНеуспешни: {failed}\n\n"
        f"[COLOR gray](Downloaded {success}, failed {failed})[/COLOR]"
    )


if __name__ == "__main__":
    main()
