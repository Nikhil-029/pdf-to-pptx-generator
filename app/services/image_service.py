# app/services/image_service.py
import os
import requests
import logging
from app.core.config import settings
UNSPLASH_ACCESS_KEY = settings.UNSPLASH_ACCESS_KEY

logger = logging.getLogger(__name__)

class ImageFetchingService:
    @staticmethod
    def fetch_image_for_slide(visual_instruction: str, download_dir: str, slide_num: int) -> str | None:
        """
        Searches Unsplash for a relevant image and downloads it locally.
        Returns the local file path, or None if it fails.
        """
        if not visual_instruction or visual_instruction.lower() in ["none", "n/a", ""]:
            return None

        # Clean the AI instruction to make it a better search query
        # E.g., "A bar chart showing growth" -> "bar chart growth"
        query = visual_instruction.replace("A photo of", "").replace("An image of", "").strip()

        url = "https://api.unsplash.com/search/photos"
        params = {
            "query": query,
            "per_page": 1,
            "orientation": "landscape", # Presentations are landscape
            "client_id": UNSPLASH_ACCESS_KEY
        }

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            if data.get("results"):
                # Grab the 'regular' size image URL
                img_url = data["results"][0]["urls"]["regular"]
                
                # Download the actual image bytes
                img_response = requests.get(img_url, stream=True)
                img_response.raise_for_status()

                img_path = os.path.join(download_dir, f"slide_{slide_num}_img.jpg")
                
                with open(img_path, 'wb') as f:
                    for chunk in img_response.iter_content(1024):
                        f.write(chunk)
                        
                return img_path
                
        except Exception as e:
            logger.error(f"Failed to fetch image for slide {slide_num}: {e}")
        
        # If API rate limits or network fails, return None to trigger the fallback
        return None