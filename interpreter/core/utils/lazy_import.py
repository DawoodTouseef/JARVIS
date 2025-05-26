import importlib.util
import sys
import subprocess
import sys


def install_package(package_name: str) -> bool:
    """
    Install the given package using pip in the current virtual environment.
    """
    try:
        # Run the pip install command using the current Python executable.
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", package_name],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        print(f"Package '{package_name}' installed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error installing package '{package_name}':")
        print(e.stderr)
        return False




def lazy_import(name, optional=True):
    """Lazily import a module, specified by the name. Useful for optional packages, to speed up startup times."""
    # Check if module is already imported
    if name in sys.modules:
        return sys.modules[name]

    # Find the module specification from the module name
    spec = importlib.util.find_spec(name)
    if spec is None:
        if optional:
            return None  # Do not raise an error if the module is optional
        else:
            value=install_package(name)
            if not value:
                raise ImportError(f"Module '{name}' cannot be found")

    # Use LazyLoader to defer the loading of the module
    loader = importlib.util.LazyLoader(spec.loader)
    spec.loader = loader

    # Create a module from the spec and set it up for lazy loading
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)

    return module
