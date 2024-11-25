from PIL import Image
import numpy as np
from io import BytesIO
import streamlit as st
import cv2

def preprocess_image(image_path, api_client):
    prompt = "an oak wooden floor, some nice painting on the walls with a light tint"
    negative_prompt = (
        "Avoid altering the existing walls or introducing new structural elements. "
        "Ensure all furniture is appropriately scaled to the room’s dimensions. "
        "Exclude any deformed structures, incorrect ratios, or anatomically incorrect objects."
    )
    response = api_client.search_and_replace_image(prompt, negative_prompt, image_path)
    if response.status_code == 200:
        output_image = Image.open(BytesIO(response.content))
        return output_image
    else:
        st.error(f"Error: {response.status_code} - {response.text}")
        return None



def create_mask_from_canvas(canvas_result):
    # Get the canvas image data
    canvas_data = canvas_result.image_data  # This is a numpy array with shape (height, width, 4)

    # Extract the alpha channel (transparency)
    alpha_channel = canvas_data[:, :, 3]

    # Create a binary image where the alpha channel is greater than zero
    binary_image = np.where(alpha_channel > 0, 255, 0).astype('uint8')

    # Find contours
    contours, _ = cv2.findContours(binary_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Create an empty mask
    mask = np.zeros_like(binary_image)

    # Fill the contours to create the mask
    cv2.drawContours(mask, contours, -1, 255, thickness=cv2.FILLED)

    # Convert mask to PIL Image
    mask_image = Image.fromarray(mask, mode='L')

    return mask_image