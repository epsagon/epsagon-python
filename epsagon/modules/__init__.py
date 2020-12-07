"""
Automatically imports all available modules for patch
"""

from __future__ import absolute_import
import os
import sys
from importlib import import_module

MODULES = {}
IGNORE_MODULES = ('__init__',)
PYTHON_EXTENSIONS = ('.py', '.pyc')
VERSION_DEPENDENCIES = {
    'aiohttp': (3, 5, 3),
    'fastapi': (3, 5, 3),
}

for module_name in os.listdir(os.path.dirname(__file__)):
    filename, ext = os.path.splitext(module_name)
    if filename in IGNORE_MODULES or ext not in PYTHON_EXTENSIONS:
        continue

    # Verify that the loaded module meets the minimum Python version
    if filename in VERSION_DEPENDENCIES:
        if sys.version_info < VERSION_DEPENDENCIES[filename]:
            continue

    try:
        imported = import_module('.{}'.format(filename), __name__)
        MODULES[filename] = imported
    except ImportError:
        pass
