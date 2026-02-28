import os
import xbmc
import xbmcgui
import xbmcvfs

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

    # Inform user we are setting things up
    pDialog = xbmcgui.DialogProgress()
    pDialog.create("[COLOR red]BGTV[/COLOR] Съветник", "Инсталиране на PVR клиент...")
    pDialog.update(10)

    # Enable the PVR addon (it should already be installed as a dependency)
    xbmc.executebuiltin('EnableAddon(pvr.hts)')
    xbmc.sleep(3000)
    pDialog.update(40, "Конфигуриране на сървъра...")

    # Build the settings XML content
    # This directly writes to the Kodi userdata filesystem, 
    # bypassing the broken setSetting() API for binary PVR addons
    settings_xml = '''<?xml version="1.0" encoding="utf-8"?>
<settings version="2">
    <setting id="host">{host}</setting>
    <setting id="http_port">{http_port}</setting>
    <setting id="htsp_port">{htsp_port}</setting>
    <setting id="user">{user}</setting>
    <setting id="pass">{password}</setting>
    <setting id="epg_async" default="true">true</setting>
    <setting id="streaming_profile">default</setting>
</settings>'''.format(
        host='bgtv.pw',
        http_port='9981',
        htsp_port='9982',
        user=username,
        password=password
    )

    pDialog.update(60, "Записване на настройките...")

    # Get the correct path for the PVR addon settings
    settings_dir = xbmcvfs.translatePath('special://profile/addon_data/pvr.hts/')
    settings_path = os.path.join(settings_dir, 'settings.xml')

    # Ensure the directory exists
    if not os.path.exists(settings_dir):
        os.makedirs(settings_dir)

    # Write the settings file directly
    try:
        with open(settings_path, 'w', encoding='utf-8') as f:
            f.write(settings_xml)
        xbmc.log("BGTV Setup: Successfully wrote settings to " + settings_path, xbmc.LOGINFO)
    except Exception as e:
        xbmc.log("BGTV Setup Error writing settings: " + str(e), xbmc.LOGERROR)
        pDialog.close()
        dialog.ok("Грешка", "Не можах да запиша настройките.\nГрешка: " + str(e))
        return

    pDialog.update(90, "Почти готово...")
    xbmc.sleep(1000)
    pDialog.close()

    # Ask user to restart Kodi
    restart = dialog.yesno(
        "Успех! ✅", 
        "BGTV телевизията е настроена перфектно!\n\nСървър: bgtv.pw\nПотребител: {user}\n\nKodi трябва да се рестартира, за да се покажат каналите.\nДа го рестартирам ли сега?".format(user=username)
    )

    if restart:
        xbmc.executebuiltin('Quit')

if __name__ == '__main__':
    run()
