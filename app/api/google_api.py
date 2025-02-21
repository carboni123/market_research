# api/google_api.py
from api.api import API
from api import register_api
from google import genai
from google.genai import types
import pathlib
import PIL.Image

@register_api("google")
class GoogleAPI(API):
    """
    Concrete class for interactions with the Google API.
    """

    MODEL_NAME = "models/gemini-2.0-flash-thinking-exp"
    # MODEL_NAME = "models/gemini-2.0-pro-exp"

    def __init__(self, api_key=None):
        """
        Initializes the GoogleAPI object.

        :param api_key: Can be either an actual API key string or a path to a file containing the API key.
        """
        super().__init__(api_key, api_env="GOOGLEAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "No valid GoogleAI API key found. Provide it as a string, file path, "
                "or set GOOGLEAI_API_KEY in the environment."
            )
        self.client = genai.Client(api_key = self.api_key)

    def set_model(self, model_name):
        self.MODEL_NAME = model_name

    async def process_text(self, prompt, timeout=10, **kwargs):
        """
        Generates text using the Google API.

        Args:
            prompt (str): The input prompt for text generation.
            timeout (int): Timeout in seconds for the API call.
            **kwargs: Additional keyword arguments for the API call.

        Returns:
            str: The generated text.

        Raises:
             NotImplementedError: This method is not yet implemented for Google API.
        """
        try:
            response = self.client.models.generate_content(model=self.MODEL_NAME, contents=prompt)
            return response.text
        except Exception as e:
            print(f"Error generating text with Google API: {e}")
            raise

    async def process_image(self, prompt, image, timeout=10, **kwargs):
        try:
            if isinstance(image, PIL.Image.Image):
                image = image
            elif isinstance(image, str):
                # assume path to image
                image = PIL.Image.open(image)
            elif isinstance(image, bytes):
                # assume base64
                image = image

            response = self.client.models.generate_content(model=self.MODEL_NAME, contents=[prompt, image])
            return response.text
        except Exception as e:
            print(f"Error generating text with Google API: {e}")
            raise

    async def process_audio(self, prompt, audio, timeout=10, **kwargs):
        if isinstance(audio, str):
            # assume path to file
            audio = self.client.files.upload(file=audio)
        try:
            response = self.client.models.generate_content(model=self.MODEL_NAME,contents=[prompt, audio])
            return response.text
        except Exception as e:
            print(f"Error generating text with Google API: {e}")
            raise

    def list_models(self):
        print("List of models that support generateContent:\n")
        for m in genai.list_models():
            if "generateContent" in m.supported_generation_methods:
                print(m.name)

    def get_model_info(self, model: str):
        model_info = genai.get_model(model)
        print(model_info)


if __name__ == "__main__":
    api = GoogleAPI()
    api.list_models()
