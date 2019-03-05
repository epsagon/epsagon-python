import os
from semantic_release.pypi import upload_to_pypi

if __name__ == '__main__':
    upload_to_pypi(
        username=os.environ['PYPI_USERNAME'],
        password=os.environ['PYPI_PASSWORD'],
    )
