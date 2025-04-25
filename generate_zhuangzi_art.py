import fitz  # PyMuPDF
from openai import OpenAI # Updated import
import os
from pathlib import Path
import requests
from PIL import Image
import io
from dotenv import load_dotenv  # Add this import
from dataclasses import dataclass
from typing import List, Optional
import re
import json

@dataclass
class Story:
    chapter: int
    title: str
    start_page: float  # page number including fraction for position
    end_page: float
    text: str
    image_prompts: Optional[List[str]] = None
    image_paths: Optional[List[str]] = None

class ZhuangziArtGenerator:
    def __init__(self, api_key):
        # Initialize the OpenAI client
        self.client = OpenAI(api_key=api_key)
        # Story markers - common patterns that indicate new stories
        self.story_markers = [
            r'\n\n[A-Z][^.!?]*[.!?]',  # New paragraph starting with capital letter
            r'(?<=\n)\s*[A-Z][^.!?]*said[^.!?]*[.!?]',  # Dialogue introductions
            r'\n\n[^\n]+\n[-—]{3,}',  # Section breaks with dashes
        ]

    def extract_text_from_pdf(self, pdf_path, chapter):
        """Extract text from specific chapter using page numbers"""
        # PDF has 37 pages before actual content starts (intro, contents, etc.)
        pdf_offset = 37  # Actual page 1 starts on PDF page 38
        
        # Chapter start pages mapping (based on contents, adjusted for PDF offset)
        chapter_pages = {
            1: 1 + pdf_offset,   # "Free and Easy Wandering" (PDF page 38)
            2: 7 + pdf_offset,   # "Discussion on Making All Things Equal" (PDF page 44)
            3: 19 + pdf_offset,  # "The Secret of Caring for Life" (PDF page 56)
            4: 22 + pdf_offset,  # "In the World of Men" (PDF page 59)
            5: 34 + pdf_offset,  # "The Sign of Virtue Complete" (PDF page 71)
            6: 42 + pdf_offset,  # "The Great and Venerable Teacher" (PDF page 79)
            7: 55 + pdf_offset   # "Fit for Emperors and Kings" (PDF page 92)
        }
        
        # Get the start page for current chapter
        start_page = chapter_pages.get(chapter)
        # Get the start page for next chapter (for end boundary)
        end_page = chapter_pages.get(chapter + 1, float('inf'))
        
        if not start_page:
            print(f"Error: Could not find start page for Chapter {chapter}")
            return ""

        doc = fitz.open(pdf_path)
        chapter_text = ""
        in_chapter = False
        
        try:
            # Use 0-based page numbers for PyMuPDF
            for page_num in range(start_page - 1, min(end_page - 1 if end_page != float('inf') else len(doc), len(doc))):
                page = doc.load_page(page_num)
                text = page.get_text()
                chapter_text += text
                
        except Exception as e:
            print(f"Error processing PDF: {e}")
        finally:
            doc.close()
        
        return chapter_text

    def analyze_chapter_imagery(self, chapter_text: str) -> List[dict]:
        """Analyze CHAPTER text for top 3 key visual elements and rank by significance"""
        system_prompt = """You are an expert in classical Chinese philosophy and visual imagery.
        Create a JSON response analyzing the most significant visual elements from this CHAPTER text.
        Focus on concrete objects and symbolic imagery that can be depicted without human figures."""
        
        # Update the user prompt to reflect chapter-level analysis
        user_prompt = """Analyze this entire chapter text and return a JSON object with an 'images' array containing the top 3 most meaningful visual elements for the chapter, each with:
        - rank (1 being most significant)
        - image (brief description of core visual element)
        - significance (philosophical meaning)
        - location (approximate position in chapter text as decimal, e.g. 0.3)
        
        Example format:
        {
            "images": [
                {
                    "rank": 1,
                    "image": "A gnarled tree with twisted branches",
                    "significance": "The beauty and utility of seeming uselessness",
                    "location": 0.2
                },
                {
                    "rank": 2,
                    "image": "A praying mantis waving its arms before a chariot",
                    "significance": "Ignoring limitations, the spirit of defiance",
                    "location": 0.6
                }
                // ... up to 3 images total
            ]
        }"""

        try:
            response = self.client.chat.completions.create(
                # Use gpt-4o-turbo for analysis
                model="gpt-4.1-mini", 
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                    # Pass the full chapter text
                    {"role": "user", "content": f"Chapter Text to analyze: {chapter_text[:10000]}"} # Limit length if needed
                ],
                response_format={ "type": "json_object" }
            )
            
            result = json.loads(response.choices[0].message.content)
            # Ensure we only return max 3 images, sorted by rank
            images = sorted(result.get("images", []), key=lambda x: x.get('rank', 99))
            return images[:3]
        except Exception as e:
            print(f"Error analyzing chapter imagery: {e}")
            return []

    def generate_image_prompts(self, scene: dict):
        """Generate two complementary prompts for a key scene"""
        system_prompt = """
        You are an expert in classical Chinese art and philosophy.

        Create two artistic, creative, and spiritual interpretations of the following scene from Zhuangzi.
        
        Style guidelines for both interpretations:
        - Use warm sepia and amber tones, like aged paper
        - Create dreamy, misty atmospheres with soft edges
        - Absolutely NO text
        - Focus on the essential elements only
        - Use negative space generously
        - Create ethereal, contemplative compositions
        
        First interpretation:
        - Include the key symbolic object/element clearly but delicately
        - Set in misty, traditional Chinese landscape elements
        - Use subtle ink-wash effects and soft gradients
        
        Second interpretation:
        - More abstract, focusing on the essence rather than form
        - Transform the concrete elements into flowing, suggestive shapes
        - Inspired by the energy and movement of calligraphy
        
        Return your response in this exact JSON format:
        {
            "naturalistic": "your naturalistic interpretation here",
            "abstract": "your abstract interpretation here"
        }
        """
        
        try:
            response = self.client.chat.completions.create(
                 # Use gpt-4o-turbo for prompt generation
                model="gpt-4o-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    # Explicitly ask for JSON format in the user prompt
                    {"role": "user", "content": f"Scene to interpret: {scene['image']}\nPhilosophical significance: {scene['significance']}\n\nPlease provide the two interpretations in the specified JSON format."}
                ],
                response_format={ "type": "json_object" }
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Add style consistency reminders
            naturalistic = result.get("naturalistic", "") + ". Style: Render in warm sepia tones with misty, dreamlike atmosphere. No text or human figures."
            abstract = result.get("abstract", "") + ". Style: Render in amber and brown tones with flowing, ethereal qualities. No text or human figures."
            
            return naturalistic, abstract
            
        except Exception as e:
            print(f"Error generating prompts: {e}")
            # Fallback prompts based on the scene
            return (
                f"A misty landscape featuring {scene['image']} in warm sepia tones, with soft edges and ethereal atmosphere. No text or human figures.",
                f"An abstract, flowing interpretation of {scene['image']} in amber tones, inspired by Chinese calligraphy. No text or human figures."
            )

    def generate_image(self, prompt: str) -> Optional[str]:
        """Generate an image using gpt-image-1 and return its URL"""
        try:
            response = self.client.images.generate(
                # Use the gpt-image-1 model
                model="gpt-image-1",  
                prompt=prompt,
                size="1024x1024", # Check documentation for supported sizes for gpt-image-1 if needed
                quality="medium", # Supported values: 'low', 'medium', 'high', 'auto'
                n=1,
            )
            image_url = response.data[0].url
            return image_url
        except Exception as e:
            print(f"Error generating image: {e}")
            return None

    def save_image(self, image_url, output_path):
        """Save the generated image"""
        if not image_url:
            print(f"Skipping save for {output_path} due to generation error.")
            return
        try:
            response = requests.get(image_url, stream=True)
            response.raise_for_status() # Raise an exception for bad status codes
            img = Image.open(io.BytesIO(response.content))
            img.save(output_path)
            print(f"Saved image to {output_path}")
        except requests.exceptions.RequestException as e:
            print(f"Error downloading image: {e}")
        except IOError as e:
            print(f"Error saving image: {e}")

    def process_chapters(self, pdf_path, output_dir):
        """Process chapters, find top 3 images per chapter, generate paired interpretations"""
        output_path_obj = Path(output_dir)
        output_path_obj.mkdir(parents=True, exist_ok=True)
        
        # Store metadata for all generated chapter images
        all_chapter_images_metadata = []
        
        for chapter in range(1, 8):
            print(f"\n=== Processing Chapter {chapter} ===")
            
            try:
                chapter_text = self.extract_text_from_pdf(pdf_path, chapter)
                if not chapter_text:
                    print(f"Skipping Chapter {chapter} due to text extraction error.")
                    continue
                    
                # Analyze the entire chapter for top 3 images
                chapter_images = self.analyze_chapter_imagery(chapter_text)
                print(f"Found {len(chapter_images)} significant images for Chapter {chapter}")
                
                # Generate interpretations for these top images (max 3)
                for img_meta in chapter_images:
                    try:
                        rank = img_meta.get('rank', 'unknown')
                        image_desc = img_meta.get('image', 'unknown_image')
                        print(f"\n--- Generating interpretations for Chapter {chapter}, Image Rank {rank}: {image_desc} ---")
                        
                        # Generate both naturalistic and abstract prompts
                        naturalistic_prompt, abstract_prompt = self.generate_image_prompts(img_meta)
                        
                        # --- SAVE PROMPTS FIRST ---
                        # Save naturalistic prompt regardless of image success
                        try:
                            with open(output_path_obj / f"chapter_{chapter}_image_{rank}_naturalistic_prompt.txt", 'w', encoding='utf-8') as f:
                                f.write(f"Naturalistic interpretation (Rank {rank}):\n{naturalistic_prompt}")
                        except Exception as e:
                             print(f"Error saving naturalistic prompt file: {e}")

                        # Save abstract prompt regardless of image success
                        try:
                            with open(output_path_obj / f"chapter_{chapter}_image_{rank}_abstract_prompt.txt", 'w', encoding='utf-8') as f:
                                f.write(f"Abstract interpretation (Rank {rank}):\n{abstract_prompt}")
                        except Exception as e:
                             print(f"Error saving abstract prompt file: {e}")
                        # --- END SAVE PROMPTS ---

                        image_paths = {} # Store paths for metadata

                        # Generate and save naturalistic version
                        naturalistic_url = self.generate_image(naturalistic_prompt)
                        if naturalistic_url:
                            nat_filename = f"chapter_{chapter}_image_{rank}_naturalistic.png"
                            self.save_image(naturalistic_url, output_path_obj / nat_filename)
                            image_paths['naturalistic'] = nat_filename
                        
                        # Generate and save abstract version
                        abstract_url = self.generate_image(abstract_prompt)
                        if abstract_url:
                            abs_filename = f"chapter_{chapter}_image_{rank}_abstract.png"
                            self.save_image(abstract_url, output_path_obj / abs_filename)
                            image_paths['abstract'] = abs_filename
                        
                        # Add metadata for this image pair
                        all_chapter_images_metadata.append({
                            'chapter': chapter,
                            'rank': rank,
                            'image_description': image_desc,
                            'significance': img_meta.get('significance', ''),
                            'location': img_meta.get('location', 0.0),
                            'naturalistic_path': image_paths.get('naturalistic'),
                            'abstract_path': image_paths.get('abstract')
                        })
                    
                    except Exception as e:
                        print(f"Error processing image rank {rank} for chapter {chapter}: {e}")
                        continue # Skip to next image if one fails
                    
            except Exception as e:
                print(f"Error processing chapter {chapter}: {e}")
                continue # Skip to next chapter if chapter analysis fails
        
        # Save metadata for web rendering
        try:
            # Rename the metadata saving function if needed, or create a new one
            self.save_chapter_images_metadata(all_chapter_images_metadata, output_path_obj / "chapter_images_metadata.json")
            print("\nSaved chapter images metadata.")
        except Exception as e:
            print(f"Error saving chapter images metadata: {e}")

    # New metadata saving function for chapter images
    def save_chapter_images_metadata(self, chapter_images_metadata: List[dict], output_path: Path):
        """Save metadata about the generated chapter images"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(chapter_images_metadata, f, ensure_ascii=False, indent=2)

def main():
    # Load environment variables from .env file
    load_dotenv()
    
    # Get API key from environment variable
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set.")
        return

    # Update the PDF filename to match your actual file
    pdf_path = Path("Complete_Works_of_Zhuangzi.pdf")
    output_dir = Path("zhuangzi_artwork")

    if not pdf_path.is_file():
        print(f"Error: PDF file not found at {pdf_path}")
        return

    generator = ZhuangziArtGenerator(api_key)
    generator.process_chapters(str(pdf_path), str(output_dir))

if __name__ == "__main__":
    main()
