"""
Epsagon generic wrapper used only in Lambda environments.
"""

from .utils import init, import_original_module
from .wrappers import lambda_wrapper


def init_module():
    """
    Initialize user's module handler.
    :return: wrapper handler.
    """
    original_module, module_path, handler_name = import_original_module()
    try:
        return getattr(original_module, handler_name)
    except AttributeError:
        raise AttributeError(
            'No handler {} in module {}'.format(handler_name, module_path)
        )


init()
wrapper = lambda_wrapper(init_module())
