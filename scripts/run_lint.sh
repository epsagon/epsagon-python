#!/usr/bin/env bash
# Skip aio based files from older Python versions
ret=`python -c 'import sys; print(0 if sys.version_info < (3, 5, 3) else 1)'`
excludes=''
if [ $ret -eq 0 ]; then
    excludes='aiohttp.py,fastapi.py'
fi
pylint --msg-template='{path}:{line}: [{msg_id}({symbol}) {obj}] {msg}' --ignore-patterns=$excludes epsagon/
