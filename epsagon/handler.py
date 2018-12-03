"""
Epsagon generic wrapper used only in Lambda environments.
"""

from .utils import init, import_original_module
from .wrappers import lambda_wrapper

init()
ORIGINAL_MODULE = import_original_module()


@lambda_wrapper
def wrapper(event, context):
    """
    Generic wrapper for Lambda functions.
    :param event: Lambda's event
    :param context: Lambda's context
    :return: Original handler
    """
    original_module, module_path, handler_name = ORIGINAL_MODULE

    try:
        wrapped_handler = getattr(original_module, handler_name)
    except AttributeError:
        raise AttributeError(
            'No handler {} in module {}'.format(handler_name, module_path)
        )

    return wrapped_handler(event, context)
