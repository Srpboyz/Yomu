import sys

if sys.platform == "win32":
    from .window import Win32ReaderWindow as ReaderWindow
elif sys.platform == "linux":
    from .window import LinuxReaderWindow as ReaderWindow
else:
    from .window import ReaderWindow
del sys
