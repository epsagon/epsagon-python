"""
Automatically imports all available modules for patch
"""

from __future__ import absolute_import
import os
from importlib import import_module

MODULES = {}
IGNORE_MODULES = ('__init__',)
PYTHON_EXTENSIONS = ('.py', '.pyc')

for module_name in os.listdir(os.path.dirname(__file__)):
    filename, ext = os.path.splitext(module_name)
    if filename in IGNORE_MODULES or ext not in PYTHON_EXTENSIONS:
        continue
    try:
        imported = import_module('.{}'.format(filename), __name__)
        MODULES[filename] = imported
    except ImportError:
        pass
