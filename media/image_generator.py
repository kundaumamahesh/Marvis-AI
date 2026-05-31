import os
import requests
from PIL import Image
from io import BytesIO
from urllib.parse import quote


class ImageGenerator:

    def __init__(self):

        self.output_dir = (
            "outputs/images"
        )

        os.makedirs(
            self.output_dir,
            exist_ok=True
        )

    async def generate(self, prompt):

        encoded_prompt = quote(prompt)

        image_url = (
            "https://image.pollinations.ai/"
            f"prompt/{encoded_prompt}"
        )

        image_data = requests.get(
            image_url,
            timeout=120
        )

        image = Image.open(
            BytesIO(image_data.content)
        )

        output = os.path.join(
            self.output_dir,
            "generated.png"
        )

        image.save(output)

        return output
