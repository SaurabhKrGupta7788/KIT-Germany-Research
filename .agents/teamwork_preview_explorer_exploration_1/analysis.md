# Presentation Deck Analysis and Modification Strategy

This document details the analysis of the presentation deck located at `html_presentation/index.html`, matches pre-generated visual assets, examines the relationship with `generate_html.py`, proposes styling improvements for readability on large screens, and designs a validation script.

---

## 1. Structural Evaluation of `index.html`

### 1.1 General Architecture
Unlike standard Reveal.js presentations (which the generator script `generate_html.py` is configured to build), the actual file `html_presentation/index.html` uses a **custom-built, lightweight HTML/CSS/JS presentation engine**. 
* **State Management**: Slides are defined as JavaScript objects pushed into a global array `slidesData`.
* **Rendering Engine**: A `buildSlide` JS function iterates over `slidesData` at load time, compiles the HTML structure for each slide, appends them to a container `#deck`, and updates a progress indicator in the footer.
* **Transition Logic**: Navigation keys (arrows, space) and touch swipes trigger a `show(idx)` function. It adds/removes CSS classes (`active` and `prev`) to control visibility, opacity, and horizontal translations (`transform: translateX`).
* **Typesetting**: MathJax 3 is loaded via CDN (`tex-mml-chtml.min.js`) and run dynamically after each slide transition via `MathJax.typesetPromise([slideEls[idx]])`.

### 1.2 Custom Slide Data Schema
The slides in `slidesData` follow a specific schema:
```javascript
slidesData.push({
  cls: 'string',            // Optional. Additional CSS class for the slide container.
  eyebrow: 'string',        // Required. Text displayed at the very top (category/section).
  bodyOnly: 'string',       // Optional. Full-width HTML content (used for Title slide).
  title: 'string',          // Optional. Slide main heading.
  subtitle: 'string',       // Optional. Slide subheading.
  text: 'string',           // Optional. Textual column HTML (typically bullets with class "bullet").
  visual: 'string',         // Optional. Visual column HTML (typically inline SVGs).
  afterRender: function,     // Optional. Post-render callback receiving the visual column's SVG root.
  afterRenderHTML: function  // Optional. Post-render callback receiving the slide's DOM element.
});
```

### 1.3 Style Rules and Palette
* **Theme**: A professional LaTeX-Beamer-inspired Light Theme.
* **Colors**:
  * Primary Text (`--ink`): `#2b2b2b` (dark gray).
  * Background (`--paper`): `#ffffff` (pure white).
  * Content Blocks (`--paper-2`): `#f4f4f8` (light grayish-blue).
  * Headings (`--blue-deep`): `#2c3e50` (dark slate blue).
  * Subtitles/Accents (`--blue-mid`): `#34495e` (mid slate blue).
  * Highlights (`--blue-bright`): `#3498db` (bright blue).
  * Warnings/Alerts (`--danger`): `#e74c3c` (red).
  * Warnings/Alerts (`--amber`): `#e67e22` (amber).
* **Typography**:
  * Headings: `Newsreader` (serif font). Title sizes are dynamically set via `clamp(30px, 3.4vw, 46px)`.
  * Body/Accents: `Inter` (sans-serif) for general text, `JetBrains Mono` for badges, metadata, and formulas.
  * Bullet Points: Sized at `16px` with a line-height of `1.5` and bullet subtext at `14.5px`.
  * Equation Boxes (`.eq-box`): Sized at `15px` with a border accent.
* **Layout**:
  * Split screen by default using `.content` (flexbox) with a `.col.text` (flex 1.05, scrollable overflow-y) and `.col.visual` (flex 1).

---

## 2. Media Matching Analysis (R1)

The directory `html_presentation/images` contains 10 assets (PNGs and MP4s), which match files in `ppt_image`. In `index.html`, several slides use JS-drawn mock SVGs which can be replaced with these high-fidelity pre-generated assets.

| Filename | Type | Matching Slide in `index.html` | Integration Strategy |
| :--- | :--- | :--- | :--- |
| `cafm_poster.png` | PNG | New Slide: **Visualizing CAFM Dynamics** | Served as the `poster` attribute for the CAFM simulation video. |
| `cafm_simulation.mp4` | MP4 | New Slide: **Visualizing CAFM Dynamics** (insert as Slide 4) | Embedded in a `<video autoplay loop muted playsinline>` tag inside the `.col.visual` column to show the crowd counterflow simulation. |
| `sklearn_ard_mean_crossing_time.png` | PNG | Slide 8: **Covariance Mechanics: Matérn 2.5 & ARD** (or new Slide 8.5) | Replaces the JS-drawn bar chart in the visual column to show the actual Automatic Relevance Determination length-scale sensitivity results. |
| `sklearn_parity_mean_crossing_time.png` | PNG | Slide 9: **Model Verification & Statistical Benchmarks** | Placed side-by-side with the residuals plot in a 2-column image layout inside `.col.visual`. |
| `sklearn_residuals_mean_crossing_time.png` | PNG | Slide 9: **Model Verification & Statistical Benchmarks** | Placed side-by-side with the parity plot in a 2-column image layout inside `.col.visual`. |
| `sklearn_partial_dependence_mean_crossing_time.png` | PNG | Slide 10: **Extracting Non-Linear Physical Insights (PDP)** | Replaces the custom JS PDP grid (`.pdp-grid` rendering 6 SVG cells) with the actual high-fidelity Matplotlib output. |
| `uncertainty_heatmap_mean_crossing_time.png` | PNG | Slide 11: **Uncertainty Quantification & Confidence Mapping** | Replaces the JS-generated HTML heatmap grid in the visual column. |
| `gp_poster.png` | PNG | New Slide: **Visualizing GP Variance Reduction** | Served as the `poster` attribute for the GP fitting video. |
| `gp_fitting.mp4` | MP4 | New Slide: **Visualizing GP Variance Reduction** (insert as Slide 13, shifting others) | Embedded in a `<video autoplay loop muted playsinline>` tag in the visual column to show how GPR variance shrinks with sequential sampling. |
| `ultimate_3way_al_comparison.png` | PNG | Slide 14: **Marathon Convergence & Time Complexity** | Replaces the JS-drawn search time bar chart in the visual column to show the benchmark results of the three acquisition optimizers. |

*Note: The remaining files in `ppt_image` (e.g. `cafm_frames/` and `gp_frames/`) are frame-by-frame PNG sequences used to compile the MP4 videos and do not need to be loaded by the presentation slide deck.*

---

## 3. Relationship between `index.html` and `generate_html.py` (R3)

### 3.1 Discrepancy Analysis
There is a fundamental mismatch between `generate_html.py` and the current `index.html`:
* `generate_html.py` contains a hardcoded HTML structure that initializes **Reveal.js** and applies a **Dark Slate Theme** (`#0f172a` slate 900 background).
* The current `index.html` uses a **Custom Light Theme** slide engine with custom-drawn inline SVGs, layout elements, and MathJax configuration.
* Running `python generate_html.py` as it is currently written will **completely overwrite** `index.html`, destroying the custom light theme, the slide transitions, and the custom SVG drawings (e.g., the animated radar).

### 3.2 Modification Strategy Decision
We **must modify `generate_html.py`** to output the enhanced presentation, rather than editing `index.html` directly.
* **Reasoning**: `generate_html.py` is the single source of truth for generating the presentation deck in this workspace. If a future build process or developer runs `python generate_html.py`, any direct edits made to `index.html` will be permanently lost.
* **Implementation Plan**: Update the multiline `html_content` string inside `generate_html.py` so that it contains the updated custom light-theme slideshow engine, the matched media assets, and the enhanced responsive styling rules.

---

## 4. Concrete Style Changes for Readability & Overflow (R2)

On large screens (like projectors or high-res monitors), the slide text currently remains at fixed pixel sizes (e.g. `16px` for bullets, `15px` for math boxes), which are too small and hard to read. Furthermore, long formulas and dense layout grids (such as in Slide 15) risk overflowing their columns.

### 4.1 Resolution-Based Scaling (Global Transform)
To ensure the deck looks identical and remains fully readable on any screen resolution without overflow, we propose implementing a **zoom/scale wrapper**.
* Set `.deck` to a fixed logical resolution of `1920px` by `1080px` (a standard 16:9 canvas).
* Scale the container dynamically using a JS window resize listener:
```javascript
function scaleDeck() {
  const deck = document.getElementById('deck');
  const targetWidth = 1920;
  const targetHeight = 1080;
  const scale = Math.min(window.innerWidth / targetWidth, window.innerHeight / targetHeight);
  deck.style.transform = `translate(-50%, -50%) scale(${scale})`;
}
```
* Modify CSS:
```css
.deck {
  position: absolute;
  width: 1920px;
  height: 1080px;
  left: 50%;
  top: 50%;
  transform-origin: center center;
  overflow: hidden;
}
```

### 4.2 Responsive & Readable Typography (Fluid Alternative)
If scaling the container is not preferred, we should increase font sizes using responsive units:
* **Bullets**: Increase `.bullet` size from `16px` to `1.85vh` (approx `20px` on 1080p).
* **Line Height**: Increase `.bullet` `line-height` from `1.5` to `1.6` for readability.
* **Subtext**: Increase `.bullet .sub` from `14.5px` to `1.5vh` (approx `16px` on 1080p).
* **Padding**: Change `.slide-inner` padding from `56px 88px 40px 88px` to responsive viewport padding: `5vh 5vw 4vh 5vw`.
* **Visual columns**: Adjust image containers:
  ```css
  .img-container img {
      max-height: 52vh !important;
      width: auto;
      object-fit: contain;
  }
  ```

### 4.3 Slide-Specific Layout Optimization

#### Slide 2 & 7: Math Column Widths & Overflow
* **Problem**: The equation boxes (`.eq-box`) contain very long LaTeX expressions (e.g., the marginal log-likelihood and Langevin equations). When squeezed into a column that is only 50% of the slide width, horizontal scrolling occurs.
* **Solution**:
  1. Set the text column to a larger flex value: `.col.text { flex: 1.3; }` and the visual column to `.col.visual { flex: 0.7; }`.
  2. Reduce equation font size inside columns to `14px` or `0.85em`.
  3. Break the long formulas into multiple lines using LaTeX line breaks `\\` inside a `\begin{aligned}` environment.

#### Slide 15: Takeaways Grid Overflow
* **Problem**: The takeaways slide has 4 large closing cards in a grid layout on the left, and a radar SVG on the right. Because the cards are squeezed into a narrow column, the large amount of text causes vertical overflow.
* **Solution**:
  1. Make Slide 15 a `bodyOnly` slide, removing the duplicate radar SVG (which has already been shown twice in Slide 1 and Slide 3).
  2. Arrange the `.closing-grid` to span the full width of the slide in a clean 2x2 grid.
  3. Increase card padding and spacing:
     ```css
     .closing-grid {
       display: grid;
       grid-template-columns: 1fr 1fr;
       gap: 24px;
       width: 100%;
       margin-top: 10px;
     }
     ```

---

## 5. Design for a Python Verification Script

To verify that the presentation is error-free, we propose a Python script (`verify_deck.py`) that uses `BeautifulSoup` to scan the presentation and verify that all referenced images and videos exist on the filesystem.

### 5.1 Verification Script Logic (`verify_deck.py`)
```python
import os
import sys
from bs4 import BeautifulSoup

def verify_presentation(html_path):
    print(f"Loading presentation: {html_path}")
    if not os.path.exists(html_path):
        print(f"Error: File {html_path} does not exist!")
        return False
        
    try:
        with open(html_path, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")
    except Exception as e:
        print(f"Syntax Error: Failed to parse HTML with BeautifulSoup. Details: {e}")
        return False
        
    base_dir = os.path.dirname(os.path.abspath(html_path))
    missing_assets = []
    checked_count = 0
    
    # 1. Check images
    for img in soup.find_all("img"):
        src = img.get("src")
        if src:
            # Skip remote CDNs if any
            if src.startswith("http://") or src.startswith("https://"):
                continue
            full_path = os.path.join(base_dir, src)
            checked_count += 1
            if not os.path.exists(full_path):
                print(f"[MISSING IMAGE] Path: {src} -> Resolved: {full_path}")
                missing_assets.append(src)
            else:
                print(f"[OK] Image: {src}")

    # 2. Check videos and posters
    for video in soup.find_all("video"):
        poster = video.get("poster")
        if poster:
            full_path = os.path.join(base_dir, poster)
            checked_count += 1
            if not os.path.exists(full_path):
                print(f"[MISSING POSTER] Path: {poster} -> Resolved: {full_path}")
                missing_assets.append(poster)
            else:
                print(f"[OK] Poster: {poster}")

        # Check sources within video
        for source in video.find_all("source"):
            src = source.get("src")
            if src:
                full_path = os.path.join(base_dir, src)
                checked_count += 1
                if not os.path.exists(full_path):
                    print(f"[MISSING VIDEO] Path: {src} -> Resolved: {full_path}")
                    missing_assets.append(src)
                else:
                    print(f"[OK] Video: {src}")
                    
    print("\n--- Verification Summary ---")
    print(f"Total local assets checked: {checked_count}")
    if missing_assets:
        print(f"Status: FAILED. Missing {len(missing_assets)} assets:")
        for asset in missing_assets:
            print(f" - {asset}")
        return False
    else:
        print("Status: PASSED. All assets verified successfully.")
        return True

if __name__ == "__main__":
    target_html = "d:/KIT/html_presentation/index.html"
    success = verify_presentation(target_html)
    sys.exit(0 if success else 1)
```

### 5.2 Verification Script Execution
To execute this script, run:
```powershell
python d:/KIT/.agents/teamwork_preview_explorer_exploration_1/verify_deck.py
```
This script returns exit code `0` on success and `1` on failure, making it ideal for integration into automated build steps.
