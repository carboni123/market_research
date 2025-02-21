# api/api.py
import os
from abc import ABC, abstractmethod
from dotenv import load_dotenv


class API(ABC):
    """
    Abstract base class for API interactions.
    """

    def __init__(self, api_key=None, **kwargs):
        """
        Initializes the API object.

        Args:
            api_key (str, optional): The API key for the service.
                                     If not provided, it tries to load it from an environment variable.
        """
        self.api_key = None

        # 1. If an api_key is provided and it's a file path, load from file.
        if api_key and os.path.isfile(api_key):
            self.api_key = self._load_api_key_from_file(api_key)

        # 2. If an api_key is provided but not a file path, assume it's the key itself.
        elif api_key:
            self.api_key = api_key

        # 3. If no api_key passed in or file loading failed, attempt to load from the environment.
        if not api_key and kwargs.get("api_env"):
            self.api_key = self._load_api_key_from_env(kwargs.get("api_env"))

        if not self.api_key:
            raise ValueError(
                "No valid API key found. Provide it as a string, file path, "
                "or set it in the environment."
            )

    def _load_api_key_from_file(self, key_path: str) -> str:
        """
        Loads the key from a file.

        :param key_path: Path to the file containing the API key.
        :return: The API key as a string.
        :raises ValueError: If the key file cannot be read or is not found.
        """
        try:
            with open(key_path, "r") as f:
                return f.read().strip()
        except FileNotFoundError:
            raise ValueError(
                f"API key file '{key_path}' not found. Please create this file with your API key."
            )
        except Exception as e:
            raise ValueError(f"Error reading API key file: {e}")

    def _load_api_key_from_env(self, api_env: str) -> str:
        """
        Loads the API key from environment variables.

        :return: The API key as a string.
        :raises ValueError: If the API key is not found in the environment variables.
        """
        dotenv_path = os.path.join(os.getcwd(), ".env")
        load_dotenv(dotenv_path)

        api_key = os.environ.get(api_env)
        if not api_key:
            raise ValueError(f"{api_env} not found in environment variables.")
        return api_key

    @abstractmethod
    async def process_text(self, prompt, **kwargs):
        """
        Abstract method to generate text from a given prompt.

        Args:
            prompt (str): The input prompt for text generation.
            **kwargs: Additional keyword arguments for the API call.

        Returns:
            str: The generated text.
        """
        pass
