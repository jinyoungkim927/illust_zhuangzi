import json
from pathlib import Path
import html
import os
import shutil
import time

# Define PDF page offsets and chapter start pages (adjust if needed)
PDF_OFFSET = 37 # Number of pages before actual content starts (e.g., intro, contents)
CHAPTER_PAGES = {
    1: 1 + PDF_OFFSET,
    2: 7 + PDF_OFFSET,
    3: 19 + PDF_OFFSET,
    4: 22 + PDF_OFFSET,
    5: 34 + PDF_OFFSET,
    6: 42 + PDF_OFFSET,
    7: 55 + PDF_OFFSET
    # Add end page for last chapter if known, otherwise JS will handle it
}

def create_website(metadata_path_str: str, artwork_dir_str: str, pdf_path_str: str, output_dir_str: str):
    """Generates an interactive HTML website with PDF viewer and image display."""
    metadata_path = Path(metadata_path_str)
    artwork_dir = Path(artwork_dir_str) # This is the SOURCE artwork dir
    pdf_path = Path(pdf_path_str)
    output_dir = Path(output_dir_str) # This is the website root
    output_dir.mkdir(parents=True, exist_ok=True)

    # Define the DESTINATION artwork directory within the output website
    output_artwork_dir = output_dir / artwork_dir.name # e.g., output/website/zhuangzi_artwork
    output_artwork_dir.mkdir(exist_ok=True) # Create it if it doesn't exist

    # --- Load Metadata ---
    if not metadata_path.exists():
        print(f"Error: Metadata file not found at {metadata_path}")
        # Create a basic HTML indicating the error
        error_html = f"""<!DOCTYPE html>
<html><head><title>Error</title></head>
<body><h1>Error</h1><p>Metadata file not found at {metadata_path}</p></body></html>"""
        with open(output_dir / "index.html", "w", encoding="utf-8") as f:
            f.write(error_html)
        return

    with open(metadata_path, 'r', encoding='utf-8') as f:
        metadata = json.load(f)

    # --- Prepare Data for JavaScript AND Copy Images ---
    image_data_by_chapter = {}
    artwork_rel_dir = artwork_dir.name # Use relative path for HTML src (this is correct)
    copied_files = set() # Keep track of copied files to avoid redundant copies

    print(f"Processing metadata and copying images to {output_artwork_dir}...")
    for item in metadata:
        chapter = item.get('chapter')
        if not chapter: continue

        nat_path = item.get('naturalistic_path')
        abs_path = item.get('abstract_path')

        # Check source existence and copy if needed
        nat_exists = False
        if nat_path:
            src_nat_file = artwork_dir / nat_path
            dest_nat_file = output_artwork_dir / nat_path
            if src_nat_file.exists():
                nat_exists = True
                if dest_nat_file not in copied_files:
                    try:
                        dest_nat_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src_nat_file, dest_nat_file)
                        copied_files.add(dest_nat_file)
                    except Exception as e:
                        print(f"  Warning: Failed to copy {src_nat_file.name} to {dest_nat_file}: {e}")
                        nat_exists = False

        abs_exists = False
        if abs_path:
            src_abs_file = artwork_dir / abs_path
            dest_abs_file = output_artwork_dir / abs_path
            if src_abs_file.exists():
                abs_exists = True
                if dest_abs_file not in copied_files:
                     try:
                        dest_abs_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src_abs_file, dest_abs_file)
                        copied_files.add(dest_abs_file)
                     except Exception as e:
                        print(f"  Warning: Failed to copy {src_abs_file.name} to {dest_abs_file}: {e}")
                        abs_exists = False

        if not nat_exists and not abs_exists:
            print(f"  Skipping metadata entry for chapter {chapter}, rank {item.get('rank')} - no images found/copied.")
            continue

        if chapter not in image_data_by_chapter:
            image_data_by_chapter[chapter] = []

        image_data_by_chapter[chapter].append({
            'rank': item.get('rank'),
            'description': item.get('image_description', ''),
            'significance': item.get('significance', ''),
            'naturalistic_src': f"{artwork_rel_dir}/{nat_path}" if nat_exists else None,
            'abstract_src': f"{artwork_rel_dir}/{abs_path}" if abs_exists else None,
        })

    print(f"Finished copying images. Copied {len(copied_files)} unique files.")

    for chapter in image_data_by_chapter:
        image_data_by_chapter[chapter].sort(key=lambda x: x.get('rank', 99))

    js_image_data = json.dumps(image_data_by_chapter)
    js_chapter_pages = json.dumps(CHAPTER_PAGES)

    # --- Generate HTML ---
    output_pdf_path = output_dir / pdf_path.name
    try:
        shutil.copy(pdf_path, output_pdf_path)
        pdf_embed_src = pdf_path.name
        print(f"Copied PDF to {output_pdf_path}")
    except Exception as e:
        print(f"Warning: Could not copy PDF. Embedding might fail. Error: {e}")
        pdf_embed_src = ""

    # Generate a timestamp for cache busting
    cache_bust_param = int(time.time())

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Zhuangzi</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,700;1,400&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="style.css?v={cache_bust_param}">
</head>
<body class="dark-mode">
    <header>
        <h1>Zhuangzi</h1>
        <nav id="chapter-nav">
            <!-- Chapter buttons will be generated by JS -->
            <span>Select Chapter: </span>
        </nav>
    </header>

    <main class="container">
        <div class="pdf-pane">
            <iframe id="pdf-viewer" src="{pdf_embed_src}" width="100%" height="800px" type="application/pdf">
                <p>Your browser does not support PDFs. Please download the PDF to view it: <a href="{pdf_embed_src}">Download PDF</a>.</p>
            </iframe>
        </div>

        <div class="image-pane">
            <div class="image-pane-header">
                 <h2 id="artwork-title">Artwork (Chapter _- Rank _)</h2>
                 <div class="controls">
                     <button id="prev-image" title="Previous Image in Chapter" disabled>←</button>
                     <button id="toggle-image-style" disabled>🦋</button>
                     <button id="next-image" title="Next Image in Chapter" disabled>→</button>
                 </div>
                 <button id="theme-toggle" title="Toggle Light/Dark Mode">☀️</button>
            </div>
            <div id="image-display" data-current-chapter="" data-current-rank="">
                <div id="image-container">
                    <img id="artwork-image" src="" alt="Artwork corresponding to text selection">
                    <p id="loading-message" style="display: none;">Loading image...</p>
                    <p id="no-image-message" style="display: none;">No image available for this selection.</p>
                </div>
                <div class="description">
                    <p><b>Description:</b> <span id="artwork-description">Select a chapter to view artwork.</span></p>
                    <div id="significance-wrapper" class="toggle-section">
                        <p><i><b>Significance:</b> <span id="artwork-significance"></span></i></p>
                    </div>
                </div>
            </div>
        </div>
    </main>

    <footer>
        <p>Artwork generation and web interface by <a href="https://www.linkedin.com/in/jinkim2" target="_blank" rel="noopener noreferrer">Jin Kim</a>.</p>
    </footer>

    <!-- Embed data for JavaScript -->
    <script>
        const imageDataByChapter = {js_image_data};
        const chapterStartPages = {js_chapter_pages};
    </script>
    <script src="script.js?v={cache_bust_param}"></script>
</body>
</html>"""

    output_html_path = output_dir / "index.html"
    with open(output_html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Generated website HTML at {output_html_path}")

    # --- Create CSS file ---
    css_path = output_dir / "style.css"
    themed_css = """
:root {
    /* Color Scheme - Default Dark Mode */
    --bg-color: #1a1a1a;
    --text-color: #e0e0e0;
    --primary-color: #a8d8ff; /* Accent */
    --secondary-color: #444;
    --header-bg: #252525;
    --button-bg: #C87E41; /* Target orange/brown */
    --button-text: #FFFFFF; /* White text for contrast */
    --button-hover-bg: #b8703a; /* Darker shade for hover */
    --button-disabled-opacity: 0.5; /* Increased opacity slightly */
    --link-color: #a8d8ff;
    --pane-bg: #202020;
    --border-color: #444;
    --description-bg: #282828;
    --significance-reveal-text-color: #a0a0a0; /* Color for '(click to reveal)' */
    --image-container-bg: #303030;

    /* Fonts - Use EB Garamond for everything */
    --font-body: 'EB Garamond', serif;
    --font-ui: 'EB Garamond', serif; /* Changed from Noto Sans */
}

body.light-mode {
    /* Light Mode Overrides */
    --bg-color: #ffffff;
    --text-color: #333333;
    --primary-color: #0056b3;
    --secondary-color: #e9ecef;
    --header-bg: #f8f9fa;
    --button-bg: #C87E41; /* Same orange/brown */
    --button-text: #FFFFFF; /* White text */
    --button-hover-bg: #b8703a; /* Darker shade */
    --link-color: #0056b3;
    --pane-bg: #fdfdfd;
    --border-color: #dee2e6;
    --description-bg: #f8f8f8;
    --significance-reveal-text-color: #555555;
    --image-container-bg: #f0f0f0;
}

body {
    font-family: var(--font-body);
    margin: 0;
    background-color: var(--bg-color);
    color: var(--text-color);
    /* MODIFIED: Longer transition */
    transition: background-color 0.6s, color 0.6s;
    line-height: 1.6;
    display: flex;
    flex-direction: column;
    min-height: 100vh;
}

header {
    background-color: var(--header-bg);
    padding: 10px 20px;
    border-bottom: 1px solid var(--border-color);
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-shrink: 0;
}

header h1 {
    margin: 0;
    font-family: var(--font-ui); /* Will now use EB Garamond */
    font-weight: 700; /* Make title bolder */
    font-size: 1.5em;
}

#theme-toggle {
    background: var(--button-bg);
    border: none;
    color: var(--button-text);
    padding: 4px 8px;
    border-radius: 5px;
    cursor: pointer;
    font-size: 1.1em;
    transition: background-color 0.2s;
    /* margin-left: 15px; Removed, handled by gap */
    line-height: 1;
}

#theme-toggle:hover {
    background-color: var(--button-hover-bg);
}

nav span {
    margin-right: 10px;
    font-family: var(--font-ui);
}

nav button {
    margin: 0 3px;
    padding: 4px 10px;
    cursor: pointer;
    font-family: var(--font-ui);
    background-color: var(--button-bg);
    color: var(--button-text);
    border: none;
    border-radius: 5px;
    transition: background-color 0.2s, box-shadow 0.2s;
    font-size: 0.95em;
}

nav button:hover {
    background-color: var(--button-hover-bg);
}

nav button[style*="bold"] {
    font-weight: bold;
    background-color: var(--button-hover-bg);
    color: var(--button-text);
    box-shadow: 0 0 4px var(--button-hover-bg);
}
nav button[style*="bold"]:hover {
    background-color: var(--button-hover-bg);
}


.container {
    display: flex;
    padding: 15px;
    gap: 20px;
    flex-grow: 1;
    /* Prevent container from shrinking too much */
    min-height: 0; /* Fix potential flexbox overflow issue in some browsers */
}

.pdf-pane,
.image-pane {
    flex: 1;
    background-color: var(--pane-bg);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 15px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    display: flex;
    flex-direction: column;
    /* Prevent panes from shrinking too much */
    min-width: 0; /* Fix potential flexbox overflow issue */
    min-height: 0;
}
body.dark-mode .pdf-pane,
body.dark-mode .image-pane {
    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.3);
}

.image-pane-header {
    display: flex;
    justify-content: space-between; /* Adjust as needed */
    align-items: center;
    margin-bottom: 10px;
    border-bottom: 1px solid var(--border-color);
    padding-bottom: 5px;
    gap: 10px; /* Add gap between items */
    flex-shrink: 0; /* Prevent header from shrinking */
}

.image-pane-header h2 {
    margin: 0;
    border: none;
    padding: 0;
    font-size: 1.2em;
    font-weight: 700;
    white-space: nowrap; /* Prevent title wrapping */
    flex-grow: 1; /* Allow title to take available space */
    text-align: left;
}


#image-display {
    display: flex;
    flex-direction: column;
    flex-grow: 1;
    min-height: 0; /* Allow shrinking */
}

#image-container {
    min-height: 300px; /* Adjusted slightly */
    border: 1px solid var(--border-color);
    margin-bottom: 10px;
    display: flex;
    justify-content: center;
    align-items: center;
    background-color: var(--image-container-bg);
    position: relative;
    border-radius: 4px;
    transition: background-color 0.3s;
    flex-grow: 1;
    overflow: hidden; /* Ensure image stays within bounds */
}

#artwork-image {
    /* MODIFIED: Make image smaller */
    max-width: 90%;
    max-height: 90%;
    object-fit: contain;
    display: block;
    border-radius: 3px;
}

#loading-message,
#no-image-message {
    position: absolute;
    text-align: center;
    color: var(--text-color);
    opacity: 0.7;
    font-family: var(--font-ui);
}

/* Styles for controls now within the header */
.controls {
    /* margin-bottom: 10px; Removed */
    display: flex;
    /* justify-content: space-between; Removed */
    align-items: center;
    gap: 8px; /* Space between buttons */
    flex-shrink: 0; /* Prevent controls from shrinking */
}

.controls button {
    padding: 4px 8px; /* Slightly smaller padding */
    cursor: pointer;
    font-family: var(--font-ui);
    background-color: var(--button-bg);
    color: var(--button-text);
    border: none;
    border-radius: 5px;
    transition: background-color 0.2s;
    font-size: 1.1em; /* Adjusted size */
    min-width: 35px; /* Adjusted min-width */
    text-align: center;
    line-height: 1; /* Ensure emoji fits well */
}

.controls button:hover:not(:disabled) {
    background-color: var(--button-hover-bg);
}

.controls button:disabled {
    cursor: not-allowed;
    opacity: var(--button-disabled-opacity);
    background-color: var(--secondary-color);
}

.description {
    background-color: var(--description-bg);
    padding: 10px;
    border-radius: 4px;
    border: 1px solid var(--border-color);
    flex-shrink: 0;
    /* MODIFIED: Add min-height to prevent layout shift */
    min-height: 100px; /* Adjust value as needed based on typical significance length */
    overflow-y: auto; /* Add scroll if content exceeds min-height when expanded */
}

.description p {
    margin: 5px 0;
}

.description span {
    color: var(--text-color);
}

iframe {
    border: 1px solid var(--border-color);
    border-radius: 4px;
    width: 100%;
    flex-grow: 1;
    background-color: #fff; /* Keep PDF background white */
    min-height: 300px; /* Ensure iframe has a minimum height */
}

.toggle-section {
    cursor: pointer;
    transition: max-height 0.4s ease-in-out;
    max-height: 1.5em; /* Initial collapsed height */
    overflow: hidden;
    position: relative;
    border-top: 1px dashed var(--border-color);
    margin-top: 10px;
    padding-top: 5px;
}

.toggle-section:not(.active) p {
    visibility: hidden;
    margin: 0;
}

.toggle-section::after {
    content: '(click to reveal)';
    position: absolute;
    bottom: 0;
    left: 0;
    padding-left: 0; /* Adjusted */
    font-size: 0.9em;
    font-style: italic;
    color: var(--significance-reveal-text-color);
    opacity: 1;
    display: block;
    font-family: var(--font-ui);
    pointer-events: none;
    width: 100%;
    line-height: 1.5em; /* Match max-height */
}

.toggle-section.active {
    /* Allow expansion up to content height, handled by .description overflow */
    max-height: none;
    overflow: visible; /* Let content flow naturally */
}

.toggle-section.active p {
    visibility: visible;
    margin: 5px 0;
}

.toggle-section.active::after {
    display: none;
}

footer {
    text-align: center;
    padding: 10px 20px;
    margin-top: auto; /* Push footer to bottom */
    font-size: 0.85em;
    color: var(--secondary-color);
    border-top: 1px solid var(--border-color);
    background-color: var(--header-bg);
    flex-shrink: 0;
}

footer a {
    color: var(--link-color);
    text-decoration: none;
}

footer a:hover {
    text-decoration: underline;
}
"""
    with open(css_path, "w", encoding="utf-8") as f:
        f.write(themed_css)
    print(f"Generated CSS file at {css_path}")

    # --- Create JS file (Overwrite with full script) ---
    js_path = output_dir / "script.js"
    full_js_content = """
document.addEventListener('DOMContentLoaded', () => {
    // --- DOM Elements ---
    const chapterNav = document.getElementById('chapter-nav');
    const pdfViewer = document.getElementById('pdf-viewer');
    const imageDisplay = document.getElementById('image-display');
    const artworkImage = document.getElementById('artwork-image');
    const artworkTitle = document.getElementById('artwork-title');
    const artworkDescriptionSpan = document.getElementById('artwork-description');
    const artworkSignificanceSpan = document.getElementById('artwork-significance');
    const significanceWrapper = document.getElementById('significance-wrapper');
    const toggleButtonStyle = document.getElementById('toggle-image-style');
    const prevImageButton = document.getElementById('prev-image');
    const nextImageButton = document.getElementById('next-image');
    const loadingMessage = document.getElementById('loading-message');
    const noImageMessage = document.getElementById('no-image-message');
    const themeToggleButton = document.getElementById('theme-toggle');

    // --- State ---
    let currentStyle = 'naturalistic';
    let currentTheme = localStorage.getItem('theme') || 'dark';
    let preloadedImages = {};

    // --- Initialization ---
    console.log("Initializing script...");
    applyTheme(currentTheme);

    if (typeof imageDataByChapter === 'undefined' || typeof chapterStartPages === 'undefined' || Object.keys(imageDataByChapter).length === 0) {
        console.error("Initialization failed: Missing or empty data.");
        artworkTitle.textContent = "Artwork (Error)";
        artworkDescriptionSpan.textContent = "Error loading data or no image data available. Cannot initialize.";
        prevImageButton.disabled = true;
        nextImageButton.disabled = true;
        toggleButtonStyle.disabled = true;
        themeToggleButton.disabled = true;
        while (chapterNav.children.length > 1) { chapterNav.removeChild(chapterNav.lastChild); }
        showNoImage("Error loading data or no images generated.");
        return;
    }

    populateChapterNav();
    setupEventListeners();

    const firstChapterKey = Object.keys(imageDataByChapter).sort((a, b) => parseInt(a) - parseInt(b))[0];
    if (firstChapterKey && imageDataByChapter[firstChapterKey] && imageDataByChapter[firstChapterKey].length > 0) {
        selectChapter(firstChapterKey);
    } else {
        let errorMsg = "No chapter data found or first chapter has no images.";
        console.warn(errorMsg);
        artworkTitle.textContent = "Artwork (No Data)";
        artworkDescriptionSpan.textContent = errorMsg;
        prevImageButton.disabled = true;
        nextImageButton.disabled = true;
        toggleButtonStyle.disabled = true;
        showNoImage(errorMsg);
    }


    // --- Functions ---
    function populateChapterNav() {
        const chapters = Object.keys(imageDataByChapter).sort((a, b) => parseInt(a) - parseInt(b));
        const spanElement = chapterNav.querySelector('span');
        chapterNav.innerHTML = '';
        if (spanElement) {
            chapterNav.appendChild(spanElement);
        } else {
             const defaultSpan = document.createElement('span');
             defaultSpan.textContent = "Select Chapter: ";
             chapterNav.appendChild(defaultSpan);
        }

        let hasButtons = false;
        chapters.forEach(chapterNum => {
            if (imageDataByChapter[chapterNum] && imageDataByChapter[chapterNum].length > 0) {
                const button = document.createElement('button');
                button.textContent = `Ch ${chapterNum}`;
                button.dataset.chapter = chapterNum;
                button.addEventListener('click', (e) => selectChapter(e.target.dataset.chapter));
                chapterNav.appendChild(button);
                hasButtons = true;
            } else {
                console.log(`Skipping button for Chapter ${chapterNum} as it has no image data.`);
            }
        });
        if (!hasButtons) {
             console.warn("No chapters with image data found to create buttons.");
             const noChaptersMsg = document.createElement('span');
             noChaptersMsg.textContent = " No chapters with images available.";
             noChaptersMsg.style.fontStyle = 'italic';
             chapterNav.appendChild(noChaptersMsg);
        }
    }

    function setupEventListeners() {
        console.log("Setting up event listeners...");
        toggleButtonStyle.addEventListener('click', toggleImageStyle);
        prevImageButton.addEventListener('click', showPreviousImage);
        nextImageButton.addEventListener('click', showNextImage);
        significanceWrapper.addEventListener('click', () => {
            significanceWrapper.classList.toggle('active');
        });
        themeToggleButton.addEventListener('click', toggleTheme);
        console.log("Event listeners set up.");
    }

    function selectChapter(chapterNumStr) {
        const chapterNum = chapterNumStr;
        console.log(`Selecting Chapter ${chapterNum}`);

        const chapterData = imageDataByChapter[chapterNum] || [];
        if (chapterData.length === 0) {
            console.warn(`No image data found for selected chapter ${chapterNum}.`);
            showNoImage(`No images available for Chapter ${chapterNum}.`);
            artworkTitle.textContent = `Artwork (Chapter ${chapterNum}-_)`;
            artworkDescriptionSpan.textContent = '(No data)';
            artworkSignificanceSpan.textContent = '';
            significanceWrapper.classList.remove('active');
            prevImageButton.disabled = true;
            nextImageButton.disabled = true;
            toggleButtonStyle.disabled = true;
            toggleButtonStyle.innerHTML = '🦋';
            navigatePdf(parseInt(chapterNum, 10));
            highlightChapterButton(chapterNumStr);
            return;
        }

        const ranksInChapter = chapterData.map(img => img.rank).sort((a, b) => a - b);
        const firstRank = ranksInChapter.length > 0 ? ranksInChapter[0] : 1;

        updateImageDisplay(chapterNum, firstRank);
        navigatePdf(parseInt(chapterNum, 10));
        highlightChapterButton(chapterNumStr);
        preloadChapterImages(chapterNum, firstRank);
    }

    function preloadChapterImages(chapterNum, excludeRank) {
        if (!preloadedImages[chapterNum]) {
            console.log(`Preloading images for Chapter ${chapterNum}...`);
            preloadedImages[chapterNum] = [];
            const chapterData = imageDataByChapter[chapterNum] || [];
            chapterData.forEach(imageData => {
                if (imageData.rank === excludeRank) return;

                if (imageData.naturalistic_src) {
                    const imgNat = new Image();
                    imgNat.src = imageData.naturalistic_src;
                    preloadedImages[chapterNum].push(imgNat);
                }
                if (imageData.abstract_src) {
                    const imgAbs = new Image();
                    imgAbs.src = imageData.abstract_src;
                    preloadedImages[chapterNum].push(imgAbs);
                }
            });
            console.log(`Finished preloading for Chapter ${chapterNum}.`);
        }
    }


    function highlightChapterButton(activeChapterNumStr) {
        const buttons = chapterNav.querySelectorAll('button');
        buttons.forEach(btn => {
            if (btn.dataset.chapter === activeChapterNumStr) {
                btn.style.fontWeight = 'bold';
            } else {
                btn.style.fontWeight = 'normal';
            }
        });
    }


    function updateImageDisplay(chapterNum, rank) {
        console.log(`Updating display for chapter ${chapterNum}, rank ${rank}`);
        const chapterData = imageDataByChapter[chapterNum] || [];
        let imageData = chapterData.find(img => img.rank === rank);

        imageDisplay.dataset.currentChapter = chapterNum;
        imageDisplay.dataset.currentRank = rank;

        artworkTitle.textContent = `Artwork (Chapter ${chapterNum}-${rank})`;

        if (imageData) {
            artworkDescriptionSpan.textContent = imageData.description || '(No description)';
            artworkSignificanceSpan.textContent = imageData.significance || '(No significance)';
            significanceWrapper.classList.remove('active');

            currentStyle = 'naturalistic';
            let imageSrc = imageData.naturalistic_src;
            let imageAlt = `Naturalistic interpretation (Ch ${chapterNum}-${rank}): ${imageData.description}`;

            if (!imageSrc && imageData.abstract_src) {
                console.log(`Naturalistic image missing for Ch ${chapterNum}-${rank}, using abstract.`);
                currentStyle = 'abstract';
                imageSrc = imageData.abstract_src;
                imageAlt = `Abstract interpretation (Ch ${chapterNum}-${rank}): ${imageData.description}`;
            }

            if (imageSrc) {
                console.log(`Setting image src to: ${imageSrc}`);
                let isLikelyCached = false;
                if (preloadedImages[chapterNum]) {
                   isLikelyCached = preloadedImages[chapterNum].some(img => img.src.endsWith(imageSrc));
                }

                if (!isLikelyCached) {
                   showLoading();
                } else {
                   loadingMessage.style.display = 'none';
                   noImageMessage.style.display = 'none';
                   artworkImage.style.display = 'block';
                }

                artworkImage.onload = () => showImage();
                artworkImage.onerror = () => {
                    console.error(`Failed to load image: ${imageSrc}`);
                    showNoImage(`Error loading image (Ch ${chapterNum}-${rank}). Path: ${imageSrc}`);
                }
                artworkImage.src = imageSrc;
                artworkImage.alt = imageAlt;
            } else {
                console.error(`No image source found for Ch ${chapterNum}-${rank}.`);
                showNoImage(`No image file available for Chapter ${chapterNum}-${rank}.`);
            }

            const canToggleStyle = imageData.naturalistic_src && imageData.abstract_src;
            toggleButtonStyle.disabled = !canToggleStyle;
            toggleButtonStyle.innerHTML = '🦋';

        } else {
            console.error(`No image metadata found for Chapter ${chapterNum}, Rank ${rank}.`);
            showNoImage(`No image data found for Chapter ${chapterNum}-${rank}.`);
            artworkDescriptionSpan.textContent = '(No data)';
            artworkSignificanceSpan.textContent = '';
            significanceWrapper.classList.remove('active');
            toggleButtonStyle.disabled = true;
            toggleButtonStyle.innerHTML = '🦋';
        }
        updateNavButtons(chapterNum, rank);
    }

    function updateNavButtons(currentChapter, currentRank) {
        const chapterData = imageDataByChapter[currentChapter] || [];
        const ranksInChapter = chapterData.map(img => img.rank).sort((a, b) => a - b);
        const currentIndex = ranksInChapter.indexOf(currentRank);

        prevImageButton.disabled = (currentIndex <= 0);
        nextImageButton.disabled = (currentIndex < 0 || currentIndex >= ranksInChapter.length - 1);
    }

    function showPreviousImage() {
        const currentChapter = imageDisplay.dataset.currentChapter;
        const currentRank = parseInt(imageDisplay.dataset.currentRank, 10);
        if (!currentChapter || isNaN(currentRank)) return;
        const chapterData = imageDataByChapter[currentChapter] || [];
        const ranksInChapter = chapterData.map(img => img.rank).sort((a, b) => a - b);
        const currentIndex = ranksInChapter.indexOf(currentRank);
        if (currentIndex > 0) {
            const prevRank = ranksInChapter[currentIndex - 1];
            updateImageDisplay(currentChapter, prevRank);
        }
    }

    function showNextImage() {
        const currentChapter = imageDisplay.dataset.currentChapter;
        const currentRank = parseInt(imageDisplay.dataset.currentRank, 10);
         if (!currentChapter || isNaN(currentRank)) return;
        const chapterData = imageDataByChapter[currentChapter] || [];
        const ranksInChapter = chapterData.map(img => img.rank).sort((a, b) => a - b);
        const currentIndex = ranksInChapter.indexOf(currentRank);
        if (currentIndex >= 0 && currentIndex < ranksInChapter.length - 1) {
            const nextRank = ranksInChapter[currentIndex + 1];
            updateImageDisplay(currentChapter, nextRank);
        }
    }

    function navigatePdf(chapterNum) {
        const pageNumber = chapterStartPages[chapterNum];
        if (pageNumber && pdfViewer) {
            console.log(`Navigating PDF to chapter ${chapterNum} (page ${pageNumber})`);
            try {
                const currentSrc = pdfViewer.getAttribute('src');
                let baseUrl = "";
                if (currentSrc) {
                     baseUrl = currentSrc.split('#')[0];
                } else {
                     baseUrl = pdfViewer.src.split('#')[0] || "Complete_Works_of_Zhuangzi.pdf";
                     console.warn("PDF viewer src attribute was empty, attempting fallback:", baseUrl);
                }
                const newSrc = `${baseUrl}#page=${pageNumber}`;
                if (pdfViewer.getAttribute('src') !== newSrc) {
                     pdfViewer.setAttribute('src', newSrc);
                     console.log(`Set PDF src to: ${newSrc}`);
                } else {
                     console.log("PDF src already set to the target page.");
                }
            } catch (e) {
                console.error("Error navigating PDF iframe:", e);
            }
        } else {
            console.warn(`No start page found for chapter ${chapterNum} or PDF viewer not found.`);
        }
    }

    function toggleImageStyle() {
        const chapterNum = imageDisplay.dataset.currentChapter;
        const rank = parseInt(imageDisplay.dataset.currentRank, 10);
        if (!chapterNum || isNaN(rank)) {
            console.error("Cannot toggle style: Missing chapter or rank information.");
            return;
        }
        const chapterData = imageDataByChapter[chapterNum];
        const imageData = chapterData ? chapterData.find(img => img.rank === rank) : null;
        if (!imageData || !imageData.naturalistic_src || !imageData.abstract_src) {
            console.error("Cannot toggle style: Both image styles must exist.");
            toggleButtonStyle.disabled = true;
            return;
        }
        currentStyle = (currentStyle === 'naturalistic') ? 'abstract' : 'naturalistic';
        const newSrc = (currentStyle === 'naturalistic') ? imageData.naturalistic_src : imageData.abstract_src;
        const newAlt = (currentStyle === 'naturalistic') ? `Naturalistic interpretation (Ch ${chapterNum}-${rank}): ${imageData.description}` : `Abstract interpretation (Ch ${chapterNum}-${rank}): ${imageData.description}`;
        console.log(`Toggling to ${currentStyle} style. New src: ${newSrc}`);
        showLoading();
        artworkImage.onload = () => showImage();
        artworkImage.onerror = () => {
             console.error(`Failed to load image: ${newSrc}`);
             showNoImage(`Error loading ${currentStyle} image.`);
        }
        artworkImage.src = newSrc;
        artworkImage.alt = newAlt;
    }

    // --- Theme Functions ---
    function applyTheme(theme) {
        console.log(`Applying theme: ${theme}`);
        if (theme === 'light') {
            document.body.classList.add('light-mode');
            document.body.classList.remove('dark-mode');
            themeToggleButton.textContent = '🌙';
            currentTheme = 'light';
        } else {
            document.body.classList.remove('light-mode');
            document.body.classList.add('dark-mode');
            themeToggleButton.textContent = '☀️';
            currentTheme = 'dark';
        }
        console.log(`Body classes: ${document.body.className}`);
    }

    function toggleTheme() {
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        console.log(`Toggling theme to: ${newTheme}`);
        applyTheme(newTheme);
        localStorage.setItem('theme', newTheme);
    }

    // --- Helper Functions for Display ---
    function showLoading() {
        artworkImage.style.display = 'none';
        loadingMessage.style.display = 'block';
        noImageMessage.style.display = 'none';
    }

    function showImage() {
        artworkImage.style.display = 'block';
        loadingMessage.style.display = 'none';
        noImageMessage.style.display = 'none';
    }

    function showNoImage(message = "No image available.") {
        artworkImage.style.display = 'none';
        artworkImage.src = "";
        loadingMessage.style.display = 'none';
        noImageMessage.textContent = message;
        noImageMessage.style.display = 'block';
    }
});
"""
    # Write the full JS content, overwriting any existing file
    with open(js_path, "w", encoding="utf-8") as f:
        f.write(full_js_content)
    print(f"Generated FULL JS file at {js_path}")


# --- Main Execution Logic ---
if __name__ == "__main__":
    if len(os.sys.argv) != 5:
         print("Usage: python create_website.py <metadata_json_path> <artwork_dir_path> <pdf_path> <output_dir_path>")
         os.sys.exit(1)

    meta_path = os.sys.argv[1]
    art_dir = os.sys.argv[2]
    pdf_file = os.sys.argv[3]
    out_dir = os.sys.argv[4]

    create_website(meta_path, art_dir, pdf_file, out_dir) 
