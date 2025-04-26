
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
