import sys
from semantic_release.history import set_new_version

if __name__ == '__main__':
    set_new_version(sys.argv[1])
