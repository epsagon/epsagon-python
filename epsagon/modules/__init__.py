"""
Automatically imports all available modules for patch
"""

from __future__ import absolute_import
import os

MODULES = {}

for module_file in os.listdir(os.path.dirname(__file__)):
    if module_file == '__init__.py' or module_file[-3:] != '.py':
        continue
    try:
        imported = __import__(module_file[:-3], locals(), globals())
        MODULES[module_file[:-3]] = imported
    except ImportError:
        pass
