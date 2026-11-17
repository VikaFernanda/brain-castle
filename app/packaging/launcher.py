"""PyInstaller entry point. (brain_castle\__main__.py uses a relative import, which fails as a top-level script.)"""
import sys

from brain_castle.main import main

sys.exit(main())
