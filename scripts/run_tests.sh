#!/usr/bin/env bash
# Skip aio based files from older Python versions
ret=`python -c 'import sys; print(0 if sys.version_info < (3, 5, 3) else 1)'`
echo $ret
excludes=''
if [ $ret -eq 0 ]; then
    excludes='aiohttp'
fi
echo $excludes
pytest --ignore-glob=*$excludes*