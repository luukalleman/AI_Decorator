import requests

class StabilityAIClient:
    def __init__(self, api_key):
        self.api_key = api_key.strip()
        self.headers = {
            "Accept": "image/*",
            "Authorization": f"Bearer {self.api_key}"
        }

    def inpaint_image(self, prompt, negative_prompt, image_path, mask_path, output_format="png"):
        url = "https://api.stability.ai/v2beta/stable-image/edit/inpaint"
        files = {
            "image": open(image_path, "rb"),
            "mask": open(mask_path, "rb"),
        }
        data = {
            "prompt": prompt,
            "grow_mask": 1,
            "output_format": output_format,
        }
        if negative_prompt:
            data["negative_prompt"] = negative_prompt
        response = requests.post(url, headers=self.headers, files=files, data=data)
        return response

    def search_and_replace_image(self, prompt, negative_prompt, image_path):
        url = "https://api.stability.ai/v2beta/stable-image/edit/search-and-replace"
        with open(image_path, "rb") as image_file:
            files = {
                "image": image_file
            }
            data = {
                "prompt": prompt,
                "search_prompt": "floor and white walls",
                "negative_prompt": negative_prompt,
                "output_format": "jpeg",
                "seed": 1
            }
            response = requests.post(url, headers=self.headers, files=files, data=data)
        return response
    
    def structure_image(self, prompt, negative_prompt, image_path,  output_format="png"):
        url = "https://api.stability.ai/v2beta/stable-image/control/structure"

        files = {
            "image": open(image_path, "rb"),
        }
        data = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "output_format": output_format,
        }
        response = requests.post(url, headers=self.headers, files=files, data=data)
        return response
    def erase_image(self, prompt, negative_prompt, image_path, mask_path, output_format="png"):
        url = "https://api.stability.ai/v2beta/stable-image/edit/erase"
        files = {
            "image": open(image_path, "rb"),
            "mask": open(mask_path, "rb"),
        }
        data = {
            "prompt": prompt,
            "output_format": output_format,
        }
        if negative_prompt:
            data["negative_prompt"] = negative_prompt
        response = requests.post(url, headers=self.headers, files=files, data=data)
        return response