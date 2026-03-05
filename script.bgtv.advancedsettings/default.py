# -*- coding: utf-8 -*-
# script.bgtv.advancedsettings/default.py
# One-click IPTV buffering optimizer for Kodi

import xbmc
import xbmcgui
import xbmcvfs
import os

ADDON_NAME = "BGTV Buffering Fix"

OPTIMIZED_XML = """\
<advancedsettings version="1.0">
  <cache>
    <buffermode>1</buffermode>
    <memorysize>104857600</memorysize>
    <readfactor>8</readfactor>
  </cache>
</advancedsettings>
"""

# buffermode=1: buffer all internet streams
# memorysize=104857600: 100MB buffer (Kodi uses 3x this = 300MB RAM)
# readfactor=8: read 8x the bitrate (fills buffer faster)

SETTINGS_PATH = xbmcvfs.translatePath("special://profile/advancedsettings.xml")


def log(msg, level=xbmc.LOGINFO):
    xbmc.log(f"[BGTV Buffer] {msg}", level)


def read_current():
    """Read current advancedsettings.xml if it exists."""
    try:
        if not os.path.exists(SETTINGS_PATH):
            return None
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return None


def write_settings(xml_content):
    """Write advancedsettings.xml."""
    try:
        d = os.path.dirname(SETTINGS_PATH)
        if not os.path.exists(d):
            os.makedirs(d)
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            f.write(xml_content)
        log(f"Wrote {SETTINGS_PATH}")
        return True
    except Exception as e:
        log(f"Failed to write: {e}", xbmc.LOGERROR)
        return False


def remove_settings():
    """Remove advancedsettings.xml (restore Kodi defaults)."""
    try:
        if os.path.exists(SETTINGS_PATH):
            os.remove(SETTINGS_PATH)
            log("Removed advancedsettings.xml")
            return True
        return False
    except Exception as e:
        log(f"Failed to remove: {e}", xbmc.LOGERROR)
        return False


def main():
    dialog = xbmcgui.Dialog()
    current = read_current()

    if current and "<memorysize>104857600</memorysize>" in current:
        # Already optimized — offer to reset
        choice = dialog.yesno(
            ADDON_NAME,
            "IPTV буферирането вече е оптимизирано!\n\n"
            "Искате ли да върнете настройките по подразбиране?\n\n"
            "[COLOR gray](Buffering is already optimized.\n"
            "Do you want to restore Kodi defaults?)[/COLOR]",
            yeslabel="Да / Yes",
            nolabel="Не / No"
        )
        if choice:
            if remove_settings():
                dialog.ok(
                    ADDON_NAME,
                    "Настройките са върнати по подразбиране.\n"
                    "Рестартирайте Kodi за да се приложат.\n\n"
                    "[COLOR gray](Defaults restored. Restart Kodi.)[/COLOR]"
                )
            else:
                dialog.ok(ADDON_NAME, "Грешка при изтриване.")
        return

    if current:
        # Has custom settings already — warn
        choice = dialog.yesno(
            ADDON_NAME,
            "Вече имате advancedsettings.xml.\n"
            "Искате ли да го замените с BGTV оптимизация?\n\n"
            "[COLOR yellow]⚠ Старият файл ще бъде презаписан![/COLOR]\n\n"
            "[COLOR gray](You already have advancedsettings.xml.\n"
            "Replace with BGTV optimization?)[/COLOR]",
            yeslabel="Да / Yes",
            nolabel="Не / No"
        )
        if not choice:
            return
    else:
        # No settings — simple prompt
        choice = dialog.yesno(
            ADDON_NAME,
            "Оптимизиране на IPTV буферирането?\n\n"
            "• 100MB буфер (300MB RAM)\n"
            "• По-бързо зареждане на каналите\n"
            "• Без спиране на картината\n\n"
            "[COLOR gray](Optimize IPTV buffering?\n"
            "100MB buffer, faster channel loading.)[/COLOR]",
            yeslabel="Да / Yes",
            nolabel="Не / No"
        )
        if not choice:
            return

    if write_settings(OPTIMIZED_XML):
        dialog.ok(
            ADDON_NAME,
            "✅ Буферирането е оптимизирано!\n\n"
            "Рестартирайте Kodi за да се приложат настройките.\n\n"
            "[COLOR gray](Buffering optimized! Restart Kodi.)[/COLOR]"
        )
    else:
        dialog.ok(ADDON_NAME, "❌ Грешка при записване. Вижте Kodi лога.")


if __name__ == "__main__":
    main()
