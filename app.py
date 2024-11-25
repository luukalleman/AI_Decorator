import os
import streamlit as st
from streamlit_drawable_canvas import st_canvas
from PIL import Image
from dotenv import load_dotenv
from datetime import datetime
import tempfile
from io import BytesIO

from image_processing import create_mask_from_canvas
from api_client import StabilityAIClient
from prompts import item_prompts

# Load environment variables from .env file
load_dotenv()

# Retrieve the API key from environment variables
API_KEY = st.secrets["STABILITY_AI"]
# Set the app to wide mode
st.set_page_config(layout="wide")


def load_css():
    with open("style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


# Call this function at the beginning of your app
load_css()


class InteractiveImageApp:
    def __init__(self, api_key):
        self.api_client = StabilityAIClient(api_key)
        self.initialize_session_state()
        self.setup_sidebar()
        self.setup_results_directory()  # Set up the results directory

    def initialize_session_state(self):
        if 'current_image' not in st.session_state:
            st.session_state.current_image = None
        if 'canvas_data' not in st.session_state:
            st.session_state.canvas_data = None
        if 'current_mask' not in st.session_state:
            st.session_state.current_mask = None
        if 'image_update_counter' not in st.session_state:
            st.session_state.image_update_counter = 0  # Initialize the counter
        if 'image_history' not in st.session_state:
            st.session_state.image_history = []  # Initialize the history
        if 'has_generated_image' not in st.session_state:
            st.session_state.has_generated_image = False  # Track if generation has been made
        if 'action' not in st.session_state:
            st.session_state.action = "CompleteMakeOverAI"  # Default action
        if 'stroke_width' not in st.session_state:
            st.session_state.stroke_width = 25  # Fixed stroke width
        if 'bg_image_uploaded' not in st.session_state:
            st.session_state.bg_image_uploaded = None  # Keep track of the uploaded image
        if 'selected_item' not in st.session_state:
            st.session_state.selected_item = None  # Selected item from prompts

    def setup_sidebar(self):
        with st.sidebar:
            # Add company image
            # Update the path
            st.image("assets/logo_KRK.png", use_column_width=True)
            st.markdown(
                "<h2 style='color: var(--highlight-text-color2);'>PhotoShoot Options</h2>", unsafe_allow_html=True)

            # Show "Upload Image" or "Start New Photoshoot" based on the current state
            if st.session_state.current_image is None:
                st.markdown(
                    "<h5 style='color: var(--highlight-text-color2);'>Upload the image here:</h5>", unsafe_allow_html=True)
                # Upload image and save it in session state
                uploaded_file = st.file_uploader("Upload an image:", type=[
                                                 "png", "jpg", "jpeg"], label_visibility='collapsed')
                if uploaded_file is not None:
                    # Store in session state for use in run()
                    st.session_state.uploaded_image = uploaded_file
            else:
                # Show a "Start New Photoshoot" button
                if st.button("Start New Photoshoot"):
                    # Reset all relevant session state variables
                    st.session_state.current_image = None
                    st.session_state.canvas_data = None
                    st.session_state.current_mask = None
                    st.session_state.image_update_counter = 0
                    st.session_state.image_history = []
                    st.session_state.has_generated_image = False
                    st.session_state.action = "CompleteMakeOverAI"
                    st.session_state.selected_item = None
                    st.session_state.uploaded_image = None  # Reset uploaded image
                    st.rerun()
            # Add buttons for other functionalities if an image is uploaded
            if st.session_state.current_image is not None:
                # Separator for better organization
                st.markdown("<hr>", unsafe_allow_html=True)

                if st.button("Refresh Canvas"):
                    st.session_state.image_update_counter += 1
                    st.rerun()
                if st.session_state.image_history:
                    if st.button("Undo Last Change"):
                        # Push current image to redo stack
                        if 'redo_stack' not in st.session_state:
                            st.session_state.redo_stack = []
                        st.session_state.redo_stack.append(
                            st.session_state.current_image.copy())

                        # Undo last change
                        self.undo_last_change()

                if 'redo_stack' in st.session_state and st.session_state.redo_stack:
                    if st.button("Redo Last Change"):
                        # Pop the last image from the redo stack
                        redo_image = st.session_state.redo_stack.pop()

                        # Push current image to the history
                        st.session_state.image_history.append(
                            st.session_state.current_image.copy())

                        # Restore the redo image
                        st.session_state.current_image = redo_image

                        # Increment the image update counter to refresh the canvas
                        st.session_state.image_update_counter += 1
                        st.rerun()
                if st.button("Download Image"):
                    if self.canvas_result and self.canvas_result.image_data is not None:
                        # Convert canvas data to image
                        canvas_image = Image.fromarray(
                            self.canvas_result.image_data.astype('uint8'), 'RGBA')
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        save_path = f"canvas_image_{timestamp}.png"
                        canvas_image.save(save_path)
                        st.success(f"Image saved as {save_path}")

    def setup_results_directory(self):
        # Create the results directory if it doesn't exist
        self.results_dir = "results"
        os.makedirs(self.results_dir, exist_ok=True)

    def run(self):
        st.markdown(
            "<h1 style='color: var(--highlight-text-color);'>Furniture AI</h1>", unsafe_allow_html=True)

        # Handle image upload
        if 'uploaded_image' in st.session_state and st.session_state.uploaded_image:
            if st.session_state.bg_image_uploaded != st.session_state.uploaded_image:
                # Open the uploaded image
                uploaded_image = Image.open(
                    st.session_state.uploaded_image).convert('RGB')
                # Update session state with the new image
                st.session_state.current_image = uploaded_image.copy()
                st.session_state.bg_image_uploaded = st.session_state.uploaded_image
                # Reset the image update counter
                st.session_state.image_update_counter += 1  # Increment to refresh canvas
                # Clear any existing generated image and history
                st.session_state.image_history = []
                st.session_state.has_generated_image = False
                # Rerun to refresh the canvas with the new image
                st.rerun()
        if st.session_state.current_image:
            # Show the drawable canvas
            self.display_canvas()
            st.markdown(
                "<h1 style='color: var(--highlight-text-color);'>Select Action:</h1>", unsafe_allow_html=True)
            self.select_action()
            self.handle_image_generation()
        else:
            st.info("Please upload an image to start drawing!")

    def undo_last_change(self):
        if st.session_state.image_history:
            # Revert to the last image in history
            st.session_state.current_image = st.session_state.image_history.pop()
            st.session_state.image_update_counter += 1  # Increment counter
            # Clear the canvas data
            st.session_state.canvas_data = None
            # Rerun to update the canvas with the previous image
            st.rerun()        
        else:
            st.warning("No changes to undo.")

    def display_canvas(self):
        # Use the static image path
        static_image_path = "assets/logo_KRK.png"

        # Check if the file exists
        if not os.path.exists(static_image_path):
            st.error(f"Static image not found at: {static_image_path}")
            return

        # Load the static image
        try:
            static_image = Image.open(static_image_path).convert("RGBA")
        except Exception as e:
            st.error(f"Error loading static image: {e}")
            return

        # Set desired canvas dimensions
        desired_width = 1000  # Adjust as needed
        width, height = static_image.size
        scaling_factor = desired_width / width
        canvas_width = desired_width
        canvas_height = int(height * scaling_factor)

        # Resize the static image for canvas
        resized_image = static_image.resize((canvas_width, canvas_height))

        # Debug: Show the static image preview
        st.image(resized_image, caption="Static Image for Canvas",
                 use_column_width=True)

        # Generate a unique key for the canvas
        canvas_key = "static_image_canvas"

        # Add the canvas
        self.canvas_result = st_canvas(
            # Transparent fill color for drawing
            fill_color="rgba(255, 255, 255, 0.3)",
            stroke_width=st.session_state.stroke_width,
            stroke_color="#FFFFFF",
            background_image=resized_image,  # Use the static image as the background
            update_streamlit=True,
            height=canvas_height,
            width=canvas_width,
            drawing_mode="freedraw",
            key=canvas_key,
        )

        # Debugging feedback
        if self.canvas_result:
            st.success("Canvas loaded successfully with static image.")
        else:
            st.error("Canvas initialization failed.")

    def select_action(self):
        if not st.session_state.has_generated_image:
            st.session_state.action = "CompleteMakeOverAI"
            st.session_state.selected_item = "CompleteMakeOverAI"
        else:
            action_options = ["Add Item", "Erase"]
            st.session_state.action = st.radio(
                "Choose an action:", action_options)

            if st.session_state.action == "Add Item":
                st.markdown(
                    "<h1 style='color: var(--highlight-text-color);'>Select Item to Add:</h1>", unsafe_allow_html=True)

                item_list = [item for item in item_prompts.keys()
                             if item != "CompleteMakeOverAI"]
                st.session_state.selected_item = st.selectbox(
                    "Choose an item to add:", item_list)
            else:
                st.session_state.selected_item = None

    def handle_image_generation(self):
        generate = st.button("Generate Image", key="generate_image")
        if generate:
            if self.canvas_result.image_data is not None:
                # Store the canvas drawing data
                st.session_state.canvas_data = self.canvas_result.json_data

                with st.spinner("Processing the image..."):
                    # Create the mask from the canvas
                    mask_image = create_mask_from_canvas(self.canvas_result)

                    # Resize the mask to the original image size
                    width, height = st.session_state.current_image.size
                    mask_image = mask_image.resize(
                        (width, height), resample=Image.NEAREST)
                    # Save the mask locally with a timestamp
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    mask_dir = os.path.join("saved_masks")
                    os.makedirs(mask_dir, exist_ok=True)
                    mask_path = os.path.join(mask_dir, f"mask_{timestamp}.png")
                    mask_image.save(mask_path)

                    # Save the current image to temporary files
                    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as image_file:
                        st.session_state.current_image.save(image_file.name)
                        image_path = image_file.name

                    # Handle actions
                    if st.session_state.action == "Add Item" and st.session_state.has_generated_image:
                        selected_item = st.session_state.selected_item
                        if selected_item and selected_item in item_prompts:
                            prompt = item_prompts[selected_item]["prompt"]
                            negative_prompt = item_prompts[selected_item]["negative_prompt"]
                        else:
                            st.error("Please select an item to add.")
                            return

                        # Call the in-painting API
                        response = self.api_client.inpaint_image(
                            prompt=prompt,
                            negative_prompt=negative_prompt,
                            image_path=image_path,
                            mask_path=mask_path,
                            output_format="png"
                        )
                    elif st.session_state.action == "Erase" and st.session_state.has_generated_image:
                        # Set prompt for erasing
                        prompt = "Erase the selected area and fill it naturally."
                        negative_prompt = (
                            "Do not leave any traces of the erased object. Ensure seamless blending with the surrounding environment."
                        )

                        # Call the erase API
                        response = self.api_client.erase_image(
                            prompt=prompt,
                            negative_prompt=negative_prompt,
                            image_path=image_path,
                            mask_path=mask_path,
                            output_format="png"
                        )
                    else:  # Default action (CompleteMakeOverAI)
                        prompt = item_prompts["CompleteMakeOverAI"]["prompt"]
                        negative_prompt = item_prompts["CompleteMakeOverAI"]["negative_prompt"]

                        # Call the in-painting API
                        response = self.api_client.inpaint_image(
                            prompt=prompt,
                            negative_prompt=negative_prompt,
                            image_path=image_path,
                            mask_path=mask_path,
                            output_format="png"
                        )

                    if response.status_code == 200:
                        try:
                            # Open and store the generated image
                            output_image = Image.open(
                                BytesIO(response.content))
                            st.success("Image processed successfully!")
                            # Save the current image to history
                            st.session_state.image_history.append(
                                st.session_state.current_image.copy())
                            # Update the current image with the generated image
                            st.session_state.current_image = output_image.copy()
                            # Update state to enable additional actions
                            st.session_state.has_generated_image = True
                            st.session_state.image_update_counter += 1
                            st.rerun()                       
                        except Exception as e:
                            st.error(
                                f"Failed to process the generated image: {e}")
                    else:
                        st.error(
                            f"Error: {response.status_code} - {response.text}")

                    # Clean up temporary files
                    os.remove(image_path)
            else:
                st.warning("Please draw on the canvas to create a mask.")


if __name__ == "__main__":
    app = InteractiveImageApp(API_KEY)
    app.run()
