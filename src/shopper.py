# Fix: On Windows, Python 3.8+ requires os.add_dll_directory for conda-forge DLLs
# that tesserocr depends on (tesseract51.dll, leptonica-1.78.0.dll).
import os, sys
if sys.platform == "win32":
    import ctypes
    _dll_dirs = [d for d in [
        os.path.join(sys.prefix, "Library", "bin"),
        os.path.join(sys.prefix, "Library", "mingw-w64", "bin"),
        os.path.join(sys.prefix, "Library", "usr", "bin"),
    ] if os.path.isdir(d)]
    for _d in _dll_dirs:
        os.add_dll_directory(_d)
    _LoadLibEx = ctypes.windll.kernel32.LoadLibraryExW
    _LoadLibEx.restype = ctypes.c_void_p
    _LoadLibEx.argtypes = [ctypes.c_wchar_p, ctypes.c_void_p, ctypes.c_ulong]
    for _d in _dll_dirs:
        _tess = os.path.join(_d, "tesseract51.dll")
        if os.path.isfile(_tess):
            _LoadLibEx(_tess, None, 0x1000)
            break

from beautifultable import BeautifulTable
import logging
import traceback
from input_layer import keyboard
import time
from utils.misc import wait
from shop.anya import AnyaShopper
from shop.drognan import DrognanShopper
from config import Config
from logger import Logger
from version import __version__
from screen import start_detecting_window, stop_detecting_window


def main():
    if Config().advanced_options["logg_lvl"] == "info":
        Logger.init(logging.INFO)
    elif Config().advanced_options["logg_lvl"] == "debug":
        Logger.init(logging.DEBUG)
    else:
        print(f"ERROR: Unkown logg_lvl {Config().advanced_options['logg_lvl']}. Must be one of [info, debug]")

    keyboard.add_hotkey(Config().advanced_options["exit_key"], lambda: Logger.info(f'Force Exit') or os._exit(1))

    print(f"============ Shop {__version__} [name: {Config().general['name']}] ============")
    table = BeautifulTable()
    table.rows.append(["f10", "Shop at Drognan (for D2R Classic)"])
    table.rows.append(["f11", "Shop at Anya"])
    table.rows.append([Config().advanced_options['exit_key'], "Stop shop"])
    table.columns.header = ["hotkey", "action"]
    print(table)
    print("\n")

    while 1:
        if keyboard.is_pressed("f10"):
            merchant = DrognanShopper()
            merchant.run()
            break
        if keyboard.is_pressed("f11"):
            merchant = AnyaShopper()
            merchant.run()
            break
        wait(0.02, 0.024)

if __name__ == "__main__":
    # To avoid cmd just closing down, except any errors and add a input() to the end
    try:
        start_detecting_window()
        wait(2, 2.4)
        main()
    except:
        traceback.print_exc()
    print("Press Enter to exit ...")
    input()
    stop_detecting_window()
