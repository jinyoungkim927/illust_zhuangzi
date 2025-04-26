import os
import io
import time
from pathlib import Path
from typing import Optional
import random

import requests
from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image
import base64

# --- Functions adapted from your existing scripts ---

def generate_image(client: OpenAI, prompt: str, quality: str) -> Optional[str]:
    """Generate an image using gpt-image-1 with specified quality and return its base64 encoded data"""
    print(f"Attempting to generate image with gpt-image-1 (quality: {quality}) for prompt (first 80 chars): {prompt[:80]}...")
    try:
        response = client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            size="1024x1024",
            quality=quality,
            n=1,
        )

        if response.data and len(response.data) > 0 and hasattr(response.data[0], 'b64_json') and response.data[0].b64_json:
            b64_data = response.data[0].b64_json
            print(f"Successfully received base64 image data (quality: {quality}, first 30 chars): {b64_data[:30]}...")
            return b64_data
        else:
            print(f"Error: Image generation API call (quality: {quality}) succeeded but returned no valid b64_json data.")
            print(f"Response data received: {response.data}")
            return None

    except Exception as e:
        print(f"Error during image generation API call (quality: {quality}): {e}")
        if "invalid_request_error" in str(e).lower() and "quality" in str(e).lower():
            print(f"Hint: The quality '{quality}' might be causing issues.")
            print("      Valid qualities for gpt-image-1: 'high', 'medium', 'low', 'auto'.")
        elif "authentication_error" in str(e).lower():
            print("Hint: Check your API key.")
        elif "permission_error" in str(e).lower():
            print("Hint: Your API key might not have access to gpt-image-1.")
        elif "rate_limit_error" in str(e).lower():
            print("Hint: You might have exceeded your API usage rate limit.")

        return None

def save_image(b64_json: Optional[str], output_path: Path):
    """Decode base64 image data and save the generated image"""
    print(f"Attempting to save image from base64 data to {output_path}")
    if not b64_json:
        print(f"Skipping save for {output_path.name} due to generation error or missing data.")
        return False

    try:
        print("Decoding base64 data...")
        image_bytes = base64.b64decode(b64_json)
        print(f"Decoded {len(image_bytes)} bytes.")

        print(f"Attempting to open image data from bytes...")
        img = Image.open(io.BytesIO(image_bytes))

        print(f"Attempting to save image file...")
        img.save(output_path)
        print(f"Successfully saved image to {output_path}")
        return True

    except base64.binascii.Error as e:
        print(f"Error decoding base64 string: {e}")
    except IOError as e:
        print(f"Error opening or saving image file from decoded data: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during save_image: {e}")

    return False

# --- Main Test Logic ---

def main_test():
    # --- Configuration ---
    artwork_dir = Path("zhuangzi_artwork")
    num_files_to_test = 3
    qualities_to_test = ["low", "medium", "high"]
    # --- End Configuration ---

    print("--- Starting Multi-Image Generation Test ---")
    print(f"Will test {num_files_to_test} random prompt files with qualities: {qualities_to_test}")

    # Load API Key
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set.")
        return

    # Initialize OpenAI Client
    try:
        client = OpenAI(api_key=api_key, timeout=180.0) # Increased timeout slightly for multiple calls
        print("OpenAI client initialized.")
    except Exception as e:
        print(f"Error initializing OpenAI client: {e}")
        return

    # Find all prompt files
    all_prompt_files = list(artwork_dir.glob("*_prompt.txt"))
    if not all_prompt_files:
        print(f"Error: No prompt files found in {artwork_dir}")
        return

    print(f"Found {len(all_prompt_files)} prompt files.")

    # Select random files
    num_to_select = min(num_files_to_test, len(all_prompt_files))
    if num_to_select < num_files_to_test:
         print(f"Warning: Found fewer than {num_files_to_test} prompt files. Testing {num_to_select}.")

    selected_files = random.sample(all_prompt_files, num_to_select)

    print(f"Selected files for testing: {[f.name for f in selected_files]}")

    # Loop through selected files and qualities
    total_generated = 0
    total_failed_generation = 0
    total_failed_saving = 0

    for i, prompt_file_path in enumerate(selected_files):
        print(f"\n--- Processing File {i+1}/{num_to_select}: {prompt_file_path.name} ---")

        # Read the prompt file
        prompt_text = ""
        try:
            with open(prompt_file_path, 'r', encoding='utf-8') as pf:
                lines = pf.readlines()
                prompt_text = "".join(lines[1:]).strip() # Skip first line
            if not prompt_text:
                 print(f"   Error: Prompt text is empty in {prompt_file_path.name}. Skipping file.")
                 continue # Skip to the next file
            print(f"   Successfully read prompt.")
        except Exception as e:
            print(f"   Error reading prompt file {prompt_file_path.name}: {e}. Skipping file.")
            continue # Skip to the next file

        # Test each quality for this prompt
        for quality in qualities_to_test:
            print(f"  -- Testing Quality: {quality} --")

            # Define output path including quality
            output_image_path = artwork_dir / f"test_{prompt_file_path.stem}_{quality}.png"

            # Generate the image
            image_b64_data = generate_image(client, prompt_text, quality)

            # Save the image
            if image_b64_data:
                save_successful = save_image(image_b64_data, output_image_path)
                if save_successful:
                    print(f"     -> Image saved to: {output_image_path.name}")
                    total_generated += 1
                else:
                    print(f"     -> Failed to save image for quality '{quality}'.")
                    total_failed_saving += 1
            else:
                print(f"     -> Failed to generate image for quality '{quality}'.")
                total_failed_generation += 1

            time.sleep(1) # Add a small delay between API calls

    print("\n--- Test Run Summary ---")
    print(f"Successfully generated and saved: {total_generated}")
    print(f"Failed generations:             {total_failed_generation}")
    print(f"Failed saves (after generation): {total_failed_saving}")
    print("--- Test Completed ---")

if __name__ == "__main__":
    main_test()
