"""
Simple example for epsagon
"""

import os
import epsagon


@epsagon.lambda_wrapper(app_name='my-app-name', token='my-secret-token')
def handle(event, context):
    return 'It worked!'
