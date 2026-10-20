#!/usr/bin/env python3
"""Install or uninstall this Bankai edition; pass --help for options."""
from pathlib import Path
import runpy
import sys

sys.argv.insert(1, "rust")
runpy.run_path(str(Path(__file__).resolve().parents[1] / 'install.py'), run_name='__main__')
