# Project: Scientific Presentation Deck Enhancement

## Architecture
- **Presentation Deck**: A single HTML file (`d:\KIT\html_presentation\index.html`) running a custom slide-rendering engine. Slides are defined dynamically in a JS array (`slidesData`) and rendered by a DOM generation loop.
- **Assets**: Pre-generated scientific charts (PNG) and simulations (MP4) located in `d:\KIT\html_presentation\images\` and `d:\KIT\ppt_image\`.
- **Styling**: Embed CSS variables for theming, typography (`Inter`, `Newsreader`, `JetBrains Mono`), and responsive columns (`.col.text`, `.col.visual`).

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|---|---|---|---|
| M1 | Exploration & Test Setup | Analyze slide-by-slide asset needs, write automated verification script | None | DONE |
| M2 | Image & Animation Integration | Insert MP4/PNG files into slides (R1), replacing/augmenting current visuals | M1 | DONE |
| M3 | Typography & Contrast Audit | Adjust font sizes, layout, contrast across all 15 slides to prevent overflow (R2) | M2 | DONE |
| M4 | Visual Graphics Enrichment | Retain and improve high-quality SVG/CSS graphics (LHS/QMC, radar) (R3) | M3 | DONE |
| M5 | Final Verification & Audit | Run automated tests, check JS syntax, perform Forensic Audit | M4 | DONE |

## Code Layout
- `d:\KIT\html_presentation\index.html`: Main slide presentation file.
- `d:\KIT\html_presentation\images\`: Target directory for images and video files.
- `d:\KIT\html_presentation\verify_assets.py`: Programmatic verification script (BeautifulSoup/Python).

## Interface Contracts
- **Slide Data Schema**:
  ```typescript
  interface SlideData {
    cls?: string;          // CSS class for slide
    eyebrow?: string;      // Small header
    title?: string;        // Slide title
    subtitle?: string;     // Slide subtitle
    text?: string;         // HTML content for text column
    visual?: string;       // HTML/SVG content for visual column
    bodyOnly?: string;     // HTML content for full-slide layout (Slide 1)
    afterRender?: (svg: SVGElement) => void;
    afterRenderHTML?: (el: HTMLElement) => void;
  }
  ```
