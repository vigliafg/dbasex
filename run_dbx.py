"""Launcher per PyInstaller: apre dBX passando gli argomenti ricevuti."""

import sys

from dbx.__main__ import main

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
