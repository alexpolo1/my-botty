# Fix: On Windows, Python 3.8+ requires os.add_dll_directory for conda-forge DLLs
# that tesserocr depends on (tesseract51.dll, leptonica-1.78.0.dll).
# This must run BEFORE any import that might trigger tesserocr loading.
import os, sys
if sys.platform == "win32":
    _conda_dll_dir = os.path.join(os.path.dirname(os.path.dirname(sys.executable)), "Library", "bin")
    if os.path.isdir(_conda_dll_dir):
        os.add_dll_directory(_conda_dll_dir)
