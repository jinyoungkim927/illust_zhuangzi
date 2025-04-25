from pathlib import Path
import shutil
import json
import os

def create_website(metadata_path, artwork_dir, pdf_path, output_dir):
    """Generates the HTML website structure."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    artwork_rel_dir = Path(artwork_dir).name # Get 'zhuangzi_artwork'
    
    # --- Load Metadata Safely ---
    images_metadata = []
    try:
        with open(metadata_path, 'r', encoding='utf-8') as f:
            images_metadata = json.load(f)
        print(f"Successfully loaded metadata from {metadata_path}")
    except FileNotFoundError:
        print(f"Warning: Metadata file not found at {metadata_path}. Proceeding without image data.")
    except json.JSONDecodeError:
        print(f"Warning: Metadata file {metadata_path} is corrupted. Proceeding without image data.")
    except Exception as e:
        print(f"Warning: An unexpected error occurred loading metadata: {e}. Proceeding without image data.")

    # --- Group Metadata by Chapter ---
    metadata_by_chapter = {}
    for item in images_metadata:
        chapter = item.get('chapter')
        if chapter:
            if chapter not in metadata_by_chapter:
                metadata_by_chapter[chapter] = []
            metadata_by_chapter[chapter].append(item)
            
    # Sort images within each chapter by rank
    for chapter in metadata_by_chapter:
        metadata_by_chapter[chapter].sort(key=lambda x: x.get('rank', 99))

    # --- Generate HTML Content ---
    content_html = ""
    for chapter in range(1, 8): # Assuming 7 chapters
        content_html += f'<div class="chapter" id="chapter-{chapter}">\n'
        content_html += f'  <h2>Chapter {chapter}</h2>\n'
        
        chapter_images = metadata_by_chapter.get(chapter, [])
        if not chapter_images:
             content_html += '  <p><i>No images generated or metadata found for this chapter.</i></p>\n'
        else:
            images_added_for_chapter = 0
            for item in chapter_images:
                image_pair_html = '  <div class="image-pair">\n'
                image_added = False # Flag to check if at least one image exists for this pair

                # Check and add naturalistic image
                nat_path = item.get('naturalistic_path')
                if nat_path and (Path(artwork_dir) / nat_path).exists():
                    image_pair_html += f'    <div class="image-container">\n'
                    image_pair_html += f'      <img src="{artwork_rel_dir}/{nat_path}" alt="Naturalistic interpretation of {item.get("image_description", "")}">\n'
                    image_pair_html += f'      <p><b>Naturalistic (Rank {item.get("rank", "?")}):</b> {item.get("image_description", "")}</p>\n'
                    image_pair_html += f'      <p><i>{item.get("significance", "")}</i></p>\n'
                    image_pair_html += f'    </div>\n'
                    image_added = True
                else:
                    # Optionally add a placeholder or message if image is missing
                    image_pair_html += f'    <div class="image-container placeholder">\n'
                    image_pair_html += f'      <p>Naturalistic image (Rank {item.get("rank", "?")}) for "{item.get("image_description", "")}" not found.</p>\n'
                    image_pair_html += f'      <p><i>{item.get("significance", "")}</i></p>\n'
                    image_pair_html += f'    </div>\n'


                # Check and add abstract image
                abs_path = item.get('abstract_path')
                if abs_path and (Path(artwork_dir) / abs_path).exists():
                    image_pair_html += f'    <div class="image-container">\n'
                    image_pair_html += f'      <img src="{artwork_rel_dir}/{abs_path}" alt="Abstract interpretation of {item.get("image_description", "")}">\n'
                    image_pair_html += f'      <p><b>Abstract (Rank {item.get("rank", "?")}):</b> {item.get("image_description", "")}</p>\n'
                    image_pair_html += f'      <p><i>{item.get("significance", "")}</i></p>\n'
                    image_pair_html += f'    </div>\n'
                    image_added = True
                else:
                     # Optionally add a placeholder or message if image is missing
                    image_pair_html += f'    <div class="image-container placeholder">\n'
                    image_pair_html += f'      <p>Abstract image (Rank {item.get("rank", "?")}) for "{item.get("image_description", "")}" not found.</p>\n'
                    image_pair_html += f'      <p><i>{item.get("significance", "")}</i></p>\n'
                    image_pair_html += f'    </div>\n'

                image_pair_html += '  </div>\n'
                
                # Only add the pair div if at least one image existed, or always add placeholders
                # Let's always add the div to show the description/significance even if images failed
                content_html += image_pair_html
                images_added_for_chapter += 1

            if images_added_for_chapter == 0 and chapter_images: # Metadata existed but no images found
                 content_html += '  <p><i>Image files corresponding to metadata entries were not found.</i></p>\n'


        content_html += '</div>\n'

    # --- Copy Assets ---
    # Copy artwork directory
    output_artwork_dir = output_path / artwork_rel_dir
    if Path(artwork_dir).exists():
        # Use shutil.copytree for easier directory copying
        # Ensure the destination doesn't exist before copying
        if output_artwork_dir.exists():
            shutil.rmtree(output_artwork_dir)
        shutil.copytree(artwork_dir, output_artwork_dir)
        print(f"Copied artwork from {artwork_dir} to {output_artwork_dir}")
    else:
        print(f"Warning: Artwork directory {artwork_dir} not found. Images will be missing.")
        # Create empty dir so relative paths don't break completely? Optional.
        output_artwork_dir.mkdir(exist_ok=True)


    # Copy PDF
    pdf_filename = Path(pdf_path).name # Gets just the filename: "Complete_Works_of_Zhuangzi.pdf"
    output_pdf_path = output_path / pdf_filename # Target path: ".../output/website/Complete_Works_of_Zhuangzi.pdf"
    
    # Check if the ORIGINAL PDF exists
    if Path(pdf_path).exists():
        # Copy the original PDF to the target path inside output/website
        shutil.copy(pdf_path, output_pdf_path) 
        print(f"Copied PDF from {pdf_path} to {output_pdf_path}")
    else:
        # If the original doesn't exist, print an error
        print(f"Error: PDF file {pdf_path} not found. PDF viewer will be empty.")
        pdf_filename = "" # Ensure iframe doesn't try to load it

    # --- HTML Structure ---
    html_template = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Zhuangzi: Visual Interpretations</title>
    <style>
        body {{ font-family: sans-serif; margin: 0; display: flex; height: 100vh; overflow: hidden; }}
        #sidebar {{ width: 50%; overflow-y: auto; padding: 20px; border-right: 1px solid #ccc; box-sizing: border-box; }}
        #pdf-viewer {{ width: 50%; height: 100%; }}
        .chapter {{ margin-bottom: 30px; border-bottom: 1px solid #eee; padding-bottom: 20px; }}
        .image-pair {{ display: flex; flex-wrap: wrap; gap: 20px; margin-top: 15px; }}
        .image-container {{ flex: 1; min-width: 250px; text-align: center; }}
        .image-container img {{ max-width: 100%; height: auto; border: 1px solid #ddd; margin-bottom: 5px; }}
        .image-container p {{ margin: 5px 0; font-size: 0.9em; }}
        .image-container i {{ color: #555; font-size: 0.85em; }}
        .placeholder {{ border: 1px dashed #ccc; padding: 20px; color: #777; min-height: 200px; display: flex; flex-direction: column; justify-content: center; align-items: center; }}
        h1, h2 {{ color: #333; }}
    </style>
</head>
<body>
    <div id="sidebar">
        <h1>Zhuangzi: Visual Interpretations</h1>
        <p>Exploring key visual metaphors from the Zhuangzi through AI-generated art.</p>
        {content_html}
    </div>
    <div id="pdf-viewer">
        <!-- This uses the simple filename because the PDF *should* now be in the same directory (output/website) -->
        {"<p style='padding:20px; color:red;'>PDF file not found.</p>" if not pdf_filename else f'<iframe src="{pdf_filename}" width="100%" height="100%" style="border:none;"></iframe>'}
    </div>
</body>
</html>
"""

    # --- Write HTML File ---
    index_path = output_path / "index.html"
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(html_template)
        
    print(f"\nWebsite generated successfully at {index_path}")

if __name__ == "__main__":
    # Define paths relative to this script, assuming script is in the main project dir
    script_dir = Path(__file__).parent 
    
    # Remove the "../" - look in subdirs of the script's directory
    metadata_file = script_dir / "zhuangzi_artwork" / "chapter_images_metadata.json" 
    artwork_folder = script_dir / "zhuangzi_artwork" 
    # Look for PDF directly in the script's directory
    pdf_file = script_dir / "Complete_Works_of_Zhuangzi.pdf" 
    output_folder = script_dir / "output" / "website" 

    # Ensure the paths are correct based on your structure:
    # Project Root: /Users/jinyoungkim/Desktop/Projects/zhuangzi_graphics/
    #   - create_website.py (script_dir points here)
    #   - Complete_Works_of_Zhuangzi.pdf (pdf_file points here)
    #   - zhuangzi_artwork/ (artwork_folder points here)
    #       - chapter_images_metadata.json (metadata_file points here)
    #       - *.png
    #   - output/
    #       - website/ (output_folder points here)

    create_website(metadata_file, artwork_folder, pdf_file, output_folder) 
