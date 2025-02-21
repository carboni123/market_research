# api/__init__.py
import os
import importlib

_api_registry = {}
_apis_discovered = False # Added a discovery flag


def register_api(name):
    """
    Decorator to register API classes.
    """
    def decorator(cls):
        _api_registry[name] = cls
        return cls
    return decorator

def _discover_apis(api_dir):
    """
    Discovers and imports all available API classes in the specified directory.

    Args:
        api_dir (str): The directory containing the API implementations.
    """
    global _apis_discovered
    if _apis_discovered: # Prevent duplicated runs
      return
    for filename in os.listdir(api_dir):
        if filename.endswith('.py') and filename != '__init__.py' and filename != "api.py":
            module_name = filename[:-3] # remove .py
            module_path = f"api.{module_name}"
            try:
              importlib.import_module(module_path)
            except ModuleNotFoundError as e:
              print(f"Warning: Could not import {module_path}. Error: {e}")
    _apis_discovered = True



def create_api_instance(api_type, api_key=None, api_dir=None):
    """
    Creates an instance of the specified API class.

    Args:
        api_type (str): The name of the API type.
        api_key (str, optional): The API key or path to key.
        api_dir (str, optional): The directory where API files are located.

    Returns:
        API: An instance of the API class.

    Raises:
        ValueError: If the API type is invalid.
    """
    if not api_dir:
       api_dir = os.path.join(os.path.dirname(__file__))
    _discover_apis(api_dir)
    api_class = _api_registry.get(api_type)
    if not api_class:
        raise ValueError(f"Invalid API type: {api_type}")
    return api_class(api_key=api_key)