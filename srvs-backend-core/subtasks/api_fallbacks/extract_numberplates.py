import os
import asyncio
from PIL import Image
import io

try:
    from google import genai
    from google.genai import errors
except ImportError:
    pass

class NumberplateExtractorAPI:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get('GEMINI_API_KEY')
        if not self.api_key:
            print("WARNING: GEMINI_API_KEY not set. Numberplate API fallback will return None.")
        else:
            self.client = genai.Client(api_key=self.api_key)
        self.model_id = 'gemini-1.5-flash'
        self.prompt = "Read the numberplate of the vehicle in this image. Provide only the text of the numberplate. If no valid numberplate is found, return 'UNKNOWN'."

    async def extract_plate(self, image_np):
        """
        Asynchronously extracts the numberplate text from a vehicle crop.
        image_np: cropped image as a numpy array.
        Returns: String (The plate text) or None.
        """
        if not self.api_key:
            return None

        try:
            img_pil = Image.fromarray(image_np)
            img_byte_arr = io.BytesIO()
            img_pil.save(img_byte_arr, format='JPEG')
            img_bytes = img_byte_arr.getvalue()

            loop = asyncio.get_event_loop()

            def sync_call():
                import tempfile
                with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                    tmp.write(img_bytes)
                    tmp_path = tmp.name

                try:
                    uploaded_img = self.client.files.upload(file=tmp_path)
                    response = self.client.models.generate_content(
                        model=self.model_id,
                        contents=[uploaded_img, self.prompt]
                    )
                    self.client.files.delete(name=uploaded_img.name)
                    return response.text.strip()
                finally:
                    os.remove(tmp_path)

            text_response = await loop.run_in_executor(None, sync_call)

            if "unknown" in text_response.lower() or not text_response:
                return None
            return text_response

        except Exception as e:
            print(f"Numberplate API Fallback Failed: {e}")
            return None
