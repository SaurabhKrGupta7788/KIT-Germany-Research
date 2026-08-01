# Challenge Report — Asset Matching & Correct File Resolution

## Challenge Summary

**Overall risk assessment**: LOW

All 7 slides requiring media assets successfully reference the correct physical paths. Programmatic checks confirm that the 10 files (8 assets + 2 posters) exist in the `html_presentation/images/` directory, are non-empty, and are referenced correctly in the HTML/JS configuration. No dummy or placeholder graphics exist in the visual slots where real assets are specified. The interactive SVGs on slides 1 & 5 are correctly configured with dynamic animation or Javascript render callbacks.

---

## Challenges

### [Low] Challenge 1: Relative Path Resolution

- **Assumption challenged**: The presentation slides assume the HTML file is served directly from the `html_presentation/` directory, and that `images/` will always be a sibling subdirectory.
- **Attack scenario**: If the slide deck is built, packaged, or deployed to another directory (e.g. `PDA-deploy-temp` or a root folder) without reproducing the exact subdirectory structure `images/`, relative path resolution will fail.
- **Blast radius**: All 7 slides with visual assets will show broken image links or unplayable video elements.
- **Mitigation**: Standardize deployment scripts to enforce asset folder bundling and verify relative paths.

### [Low] Challenge 2: Browser Video Codec & Autoplay Settings

- **Assumption challenged**: The presentation assumes that the client browser will automatically autoplay the muted simulations (`cafm_simulation.mp4` and `gp_fitting.mp4`) and supports H.264/MP4.
- **Attack scenario**: In certain restricted environments (e.g., security-hardened kiosk browsers, legacy browsers without modern video codec support), video elements might fail to initialize or play.
- **Blast radius**: Slides 3 and 7 will only show static visuals.
- **Mitigation**: The code successfully includes `poster` attributes (`cafm_poster.png` and `gp_poster.png`) and fallback text inside `<video>` elements, which acts as a robust mitigation.

### [Medium] Challenge 3: DOM Generation Timing for SVG afterRender

- **Assumption challenged**: The slide-rendering engine assumes that `data.afterRender` can immediately search the DOM for SVG elements using `el.querySelector('.col.visual svg')`.
- **Attack scenario**: If the deck-rendering code becomes asynchronous or if the slide structures are rendered virtually (e.g., using a framework like React or Vue), `el.querySelector` might return `null` at the time of calling.
- **Blast radius**: Slide 5 (LHS/QMC) and Slide 12 (Active Learning Loop) will fail to generate dynamic SVG elements, showing incomplete/empty diagrams.
- **Mitigation**: The current build engine resolves elements synchronously, and the `afterRender` invocation includes a safety check (`if(svgEl)`), but a developer console warning should be added if `svgEl` is not found.

---

## Stress Test Results

- **Slide Definition Count** → Check that exactly 15 slides are defined in `index.html` → 15 slides found → **PASS**
- **Slide 1 Radar Sweep SVG** → Check that `${radarSVG()}` is called and CSS rules for `.radar-sweep` animation exist → Found and verified → **PASS**
- **Slide 3 Simulation Video Integration** → Check reference to `images/cafm_simulation.mp4` and poster `images/cafm_poster.png` → Found and verified → **PASS**
- **Slide 5 LHS vs Sobol SVG Integration** → Check `afterRender` callback and target IDs `#lhs-dots` / `#sobol-dots` → Found and verified → **PASS**
- **Slide 7 GP Fitting Video Integration** → Check reference to `images/gp_fitting.mp4` and poster `images/gp_poster.png` → Found and verified → **PASS**
- **Slide 8 ARD Length-Scale Image** → Check reference to `images/sklearn_ard_mean_crossing_time.png` → Found and verified → **PASS**
- **Slide 9 Parity & Residual Images** → Check reference to `images/sklearn_parity_mean_crossing_time.png` and `images/sklearn_residuals_mean_crossing_time.png` → Found and verified → **PASS**
- **Slide 10 PDP Image** → Check reference to `images/sklearn_partial_dependence_mean_crossing_time.png` → Found and verified → **PASS**
- **Slide 11 Uncertainty Heatmap Image** → Check reference to `images/uncertainty_heatmap_mean_crossing_time.png` → Found and verified → **PASS**
- **Slide 14 Acquisition Comparison Image** → Check reference to `images/ultimate_3way_al_comparison.png` → Found and verified → **PASS**
- **Asset Physical Existence and Non-Empty Status** → Verify that all 10 assets are physically present in `html_presentation/images/` and size > 0 → Verified all files present with valid sizes → **PASS**

---

## Unchallenged Areas

- **Slide Visual Aesthetics & Overflows** — The layout, sizing, and typography were not visually checked on a real screen by this Challenger (out of scope for asset matching verification).
- **Active Learning Pipeline Code Execution** — The execution of `augment_active_learning.py` and real GPR hyperparameter tuning was not run (out of scope for slide asset verification).
