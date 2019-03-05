import os
import logging
from semantic_release.pypi import upload_to_pypi

if __name__ == '__main__':
    try:
        upload_to_pypi(
            username=os.environ['PYPI_USERNAME'],
            password=os.environ['PYPI_PASSWORD'],
        )
    except Exception:
        logging.exception('failed to publish')
        exit(1)
