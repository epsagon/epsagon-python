from .trace import tracer


def add_data_if_needed(dictionary, name, data):
    if not tracer.metadata_only:
        dictionary[name] = data
