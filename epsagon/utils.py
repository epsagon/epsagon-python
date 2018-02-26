from .trace import tracer


def add_data_if_needed(dictionary, name, data):
    dictionary[name] = None
    if not tracer.metadata_only:
        dictionary[name] = data
