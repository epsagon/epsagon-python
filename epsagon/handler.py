"""
Epsagon generic wrapper used only in Lambda environments.
"""

from .utils import init as epsagon_init, import_original_module
from .wrappers import lambda_wrapper


def init_module():
    """
    Initialize user's module handler.
    :return: wrapper handler.
    """
    original_module, module_path, handler_name = import_original_module()
    try:
        handler = original_module
        for name in module_path.split('.')[1:] + [handler_name]:
            handler = getattr(handler, name)
        return handler
    except AttributeError:
        raise AttributeError(
            'No handler {} in module {}'.format(handler_name, module_path)
        )


epsagon_init()
wrapper = lambda_wrapper(init_module())
