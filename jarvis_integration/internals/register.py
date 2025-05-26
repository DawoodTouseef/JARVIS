register = {}


def define_table(name):
    def decorator(fn):
        # Register the table function by its name
        register[name] = fn
        return fn

    return decorator


def register_table(name, model_fn):
    """
    Programmatically register a model-defining function.

    Args:
        name (str): Name of the table.
        model_fn (callable): Function that takes Base (and optionally db) and returns a model class.
    """
    if name in register:
        raise ValueError(f"Table '{name}' is already registered")
    register[name] = model_fn