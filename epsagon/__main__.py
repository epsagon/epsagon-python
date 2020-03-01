"""Entry-point to the `python -m epsagon` command."""
import os
import sys

__all__ = ('main',)


def main():
    """Entry-point to the `python -m epsagon` command."""
    program_exec_path = sys.argv[1]

    if not os.path.dirname(program_exec_path):
        program_search_path = os.environ.get('PATH', '').split(os.path.pathsep)
        for path in program_search_path:
            path = os.path.join(path, program_exec_path)
            if os.path.exists(path) and os.access(path, os.X_OK):
                program_exec_path = path
                break

    os.execl(program_exec_path, *sys.argv[1:])


if __name__ == '__main__':
    main()
