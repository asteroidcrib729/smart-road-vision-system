import os
import asyncio
from PIL import Image
import io
import shutil
import cv2

try:
    from gradio_client import Client, handle_file
except ImportError:
    pass

class RealESRGANAPI:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get('HF_API_KEY')
        if not self.api_key:
            print("WARNING: HF_API_KEY not set. Real-ESRGAN enhancements will be skipped.")
            self.client = None
        else:
            try:
                self.client = Client("Nick088/Real-ESRGAN_Pytorch", token=self.api_key)
            except Exception as e:
                print(f"Failed to initialize Real-ESRGAN client: {e}")
                self.client = None

    async def enhance_image(self, image_np, save_path):
        """
        Asynchronously enhances an image using the Real-ESRGAN Hugging Face Space.
        image_np: cropped image as a numpy array.
        save_path: The path where the restored image should be saved.
        Returns: True if successful, False otherwise.
        """
        if not self.client:
            return False

        try:
            # We must save the np array temporarily so gradio_client can handle_file()
            loop = asyncio.get_event_loop()

            def sync_call():
                import tempfile
                with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                    cv2.imwrite(tmp.name, image_np)
                    tmp_path = tmp.name

                try:
                    result = self.client.predict(
                        img=handle_file(tmp_path),
                        api_name="/predict"
                    )

                    recreated_image_path = result[0] if isinstance(result, tuple) else result

                    if recreated_image_path and os.path.exists(recreated_image_path):
                        shutil.copy(recreated_image_path, save_path)
                        return True
                    return False
                finally:
                    os.remove(tmp_path)

            success = await loop.run_in_executor(None, sync_call)
            return success

        except Exception as e:
            print(f"Real-ESRGAN Enhancement Failed: {e}")
            return False
