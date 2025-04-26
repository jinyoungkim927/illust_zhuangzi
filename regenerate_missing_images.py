import json
import os
from pathlib import Path
import time
from typing import Optional

import requests
from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image
import io

# --- Functions copied/adapted from generate_zhuangzi_art.py ---

def generate_image(client: OpenAI, prompt: str) -> Optional[str]:
    """Generate an image using gpt-image-1 and return its URL"""
    print(f"   Attempting to generate image for prompt (first 80 chars): {prompt[:80]}...")
    try:
        response = client.images.generate(
            model="gpt-image-1", # Or your desired image model
            prompt=prompt,
            size="1024x1024",
            quality="medium", # Or your desired quality
            n=1,
        )
        image_url = response.data[0].url
        print(f"   Successfully generated image URL.")
        # Add a small delay to potentially avoid rate limits if generating many images
        time.sleep(2) 
        return image_url
    except Exception as e:
        print(f"   Error generating image: {e}")
        return None

def save_image(image_url: Optional[str], output_path: Path):
    """Save the generated image"""
    # Add print immediately upon entering the function
    print(f"   -> Entered save_image for {output_path.name}", flush=True) 
    if not image_url:
        print(f"   Skipping save for {output_path.name} due to generation error.", flush=True)
        return
        
    # Add print right before the potentially blocking network call
    print(f"   Attempting to download from URL: {image_url}", flush=True) 
    try:
        response = requests.get(image_url, stream=True, timeout=90) # Increased timeout slightly
        # Add print after the request returns (before checking status)
        print(f"   Download request completed with status code: {response.status_code}", flush=True) 
        response.raise_for_status() # Raise an exception for bad status codes
        
        # Add print before opening image data
        print(f"   Attempting to open image data...", flush=True) 
        img = Image.open(io.BytesIO(response.content))
        # Add print before saving
        print(f"   Attempting to save image to {output_path}...", flush=True) 
        img.save(output_path)
        print(f"   Successfully saved image to {output_path}", flush=True)
        
    except requests.exceptions.Timeout:
         print(f"   Error downloading image: Request timed out for {output_path.name}", flush=True)
    except requests.exceptions.RequestException as e:
        print(f"   Error downloading image: {e}", flush=True)
    except IOError as e:
        print(f"   Error opening or saving image: {e}", flush=True) # Combined IOError
    except Exception as e:
        print(f"   An unexpected error occurred during save_image: {e}", flush=True)
    # Add print upon exiting the function
    print(f"   <- Exiting save_image for {output_path.name}", flush=True) 


# --- Main Regeneration Logic ---

def regenerate(metadata_path: Path, artwork_dir: Path, client: OpenAI):
    """Reads metadata, finds missing images, and attempts regeneration."""
    
    if not metadata_path.exists():
        print(f"Error: Metadata file not found at {metadata_path}")
        return

    print(f"Loading metadata from {metadata_path}...")
    try:
        with open(metadata_path, 'r', encoding='utf-8') as f:
            all_metadata = json.load(f)
        print("Metadata loaded successfully.")
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {metadata_path}")
        return
    except Exception as e:
        print(f"Error reading metadata file: {e}")
        return

    regenerated_count = 0
    missing_prompts = 0
    failed_generation = 0

    for item in all_metadata:
        try:
            chapter = item.get('chapter')
            rank = item.get('rank')
            desc = item.get('image_description', 'Unknown Description')

            if chapter is None or rank is None:
                 print(f"\nSkipping item due to missing chapter or rank: {item}")
                 continue
                 
            print(f"\nProcessing Chapter {chapter}, Rank {rank}: {desc}")

            # --- Check and Regenerate Naturalistic ---
            nat_filename = f"chapter_{chapter}_image_{rank}_naturalistic.png"
            image_path = artwork_dir / nat_filename
            
            if not image_path.exists():
                print(f" -> Naturalistic image missing: {image_path.name}")
                nat_prompt_filename = f"chapter_{chapter}_image_{rank}_naturalistic_prompt.txt"
                prompt_path = artwork_dir / nat_prompt_filename
                
                if prompt_path.exists():
                    try:
                        with open(prompt_path, 'r', encoding='utf-8') as pf:
                            lines = pf.readlines()
                            prompt_text = "".join(lines[1:]).strip() if len(lines) > 1 else ""
                        
                        if prompt_text:
                            image_url = generate_image(client, prompt_text)
                            if image_url:
                                save_image(image_url, image_path)
                                regenerated_count += 1
                            else:
                                failed_generation += 1
                        else:
                             print(f"   Error: Prompt file {prompt_path.name} is empty.")
                             missing_prompts += 1

                    except Exception as e:
                        print(f"   Error reading prompt file {prompt_path.name}: {e}")
                        missing_prompts += 1
                else:
                    print(f"   Error: Prompt file not found: {prompt_path.name}")
                    missing_prompts += 1
            else:
                print(f" -> Naturalistic image exists: {image_path.name}")


            # --- Check and Regenerate Abstract ---
            abs_filename = f"chapter_{chapter}_image_{rank}_abstract.png"
            image_path = artwork_dir / abs_filename

            if not image_path.exists():
                print(f" -> Abstract image missing: {image_path.name}")
                abs_prompt_filename = f"chapter_{chapter}_image_{rank}_abstract_prompt.txt"
                prompt_path = artwork_dir / abs_prompt_filename

                if prompt_path.exists():
                    try:
                        with open(prompt_path, 'r', encoding='utf-8') as pf:
                            lines = pf.readlines()
                            prompt_text = "".join(lines[1:]).strip() if len(lines) > 1 else ""

                        if prompt_text:
                            image_url = generate_image(client, prompt_text)
                            if image_url:
                                save_image(image_url, image_path)
                                regenerated_count += 1
                            else:
                                failed_generation += 1
                        else:
                             print(f"   Error: Prompt file {prompt_path.name} is empty.")
                             missing_prompts += 1

                    except Exception as e:
                        print(f"   Error reading prompt file {prompt_path.name}: {e}")
                        missing_prompts += 1
                else:
                    print(f"   Error: Prompt file not found: {prompt_path.name}")
                    missing_prompts += 1
            else:
                print(f" -> Abstract image exists: {image_path.name}")
                
        except Exception as e:
             print(f"\nError processing metadata item {item}: {e}")
             continue

    print("\n--- Regeneration Summary ---")
    print(f"Successfully regenerated: {regenerated_count} images.")
    print(f"Failed generations (API/download/save errors): {failed_generation}")
    print(f"Missing prompt files or read errors: {missing_prompts}")
    print("-----------------------------")
    if regenerated_count > 0 or failed_generation > 0:
         print("\nRemember to run 'python create_website.py' again to update the website with new images.")


if __name__ == "__main__":
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set.")
        exit()

    try:
        client = OpenAI(
            api_key=api_key,
            timeout=60.0, 
        )
        print("OpenAI client initialized with timeout.")
        
        # --- ADD TEST CALL ---
        print("Attempting simple API test (list models)...")
        try:
            models = client.models.list()
            print(f"Simple API test successful. Found {len(models.data)} models.")
        except Exception as test_e:
            print(f"Simple API test failed: {test_e}")
            print("Exiting due to API test failure.")
            exit()
        # --- END TEST CALL ---

    except Exception as e:
        print(f"Error initializing OpenAI client: {e}")
        exit()

    script_dir = Path(__file__).parent
    artwork_dir = script_dir / "zhuangzi_artwork"
    metadata_file = artwork_dir / "chapter_images_metadata.json"

    regenerate(metadata_file, artwork_dir, client) 