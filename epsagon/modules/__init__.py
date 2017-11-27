"""
Automatically imports all available modules for patch
"""

import os

MODULES = {}

for module_file in os.listdir(os.path.dirname(__file__)):
    if module_file == '__init__.py' or module_file[-3:] != '.py':
        continue

    imported = __import__(module_file[:-3], locals(), globals())
    MODULES[module_file[:-3]] = imported
