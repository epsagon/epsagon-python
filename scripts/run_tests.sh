#!/usr/bin/env bash
# Skip aio based files from older Python versions
ret=`python -c 'import sys; print(0 if sys.version_info < (3, 5, 3) else 1)'`
excludes=''
if [ $ret -eq 0 ]; then
    echo $excludes
    excludes='aio'
fi
pytest --ignore-glob='*$excludes*'