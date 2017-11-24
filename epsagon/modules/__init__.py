import os

MODULES = {}

for module in os.listdir(os.path.dirname(__file__)):
    if module == '__init__.py' or module[-3:] != '.py':
        continue

    imported = __import__(module[:-3], locals(), globals())
    MODULES[module[:-3]] = imported
del module
