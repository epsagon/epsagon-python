"""
Simple example for Epsagon usage when running a custom Python code
"""
import sys

import epsagon
epsagon.init(
    token='my-secret-token',
    app_name='my-app-name',
    metadata_only=False  # Optional
)


@epsagon.python_wrapper(name='my-python-resource')
def main(args):
    print('Hello world: ' + str(args))
    return 'It worked!'


if __name__ == '__main__':
    main(sys.argv[1:])
