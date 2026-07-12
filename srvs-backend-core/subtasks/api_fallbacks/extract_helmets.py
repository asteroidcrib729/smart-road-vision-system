import os
import asyncio
from PIL import Image
import io

try:
    from google import genai
    from google.genai import errors
except ImportError:
    pass # Will be handled by missing dependency in environment if needed

class HelmetExtractorAPI:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get('GEMINI_API_KEY')
        if not self.api_key:
            print("WARNING: GEMINI_API_KEY not set. Helmet API fallback will return UNKNOWN.")
        else:
            self.client = genai.Client(api_key=self.api_key)
        self.model_id = 'gemma-4-31b-it'
        self.prompt = "Analyze this image of a bike rider. Does the rider appear to be wearing a helmet? Provide only a concise 'YES' or 'NO' answer. If unsure or if the rider is not visible, return 'UNKNOWN'."

    async def extract_helmet(self, image_np):
        """
        Asynchronously checks if a rider is wearing a helmet.
        image_np: cropped image as a numpy array.
        Returns: True (Helmet), False (No Helmet), or None (Unknown/Error)
        """
        if not self.api_key:
            return None

        try:
            # Convert numpy array to bytes to upload
            img_pil = Image.fromarray(image_np)
            img_byte_arr = io.BytesIO()
            img_pil.save(img_byte_arr, format='JPEG')
            img_bytes = img_byte_arr.getvalue()

            # Since the google-genai library might be synchronous, we wrap it in an executor
            # For a truly async httpx implementation we'd use raw REST, but we adapt the SDK here
            loop = asyncio.get_event_loop()

            def sync_call():
                # Write to temp file because the SDK expects a file path or file-like object for upload
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

            if "yes" in text_response.lower():
                return True
            elif "no" in text_response.lower():
                return False
            else:
                return None

        except Exception as e:
            print(f"Helmet API Fallback Failed: {e}")
            return None
