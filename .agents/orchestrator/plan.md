# Execution Plan - Scientific Presentation Deck Enhancement

## Mission
Enhance the custom HTML/JS-based presentation deck in `d:\KIT\html_presentation\index.html` by inserting correct pre-generated media assets, adjusting typography/layout to prevent text overflow, preserving programmatic SVG animations, and verifying the changes programmatically.

## Steps and Schedule

### 1. Exploration & Requirements Extraction [DONE]
- Spawn Explorers to analyze the codebase structure, asset availability, and mismatch with `generate_html.py`.
- Formulate asset matching and responsive styling layout strategies.

### 2. Implementer Setup & Dispatch [IN_PROGRESS]
- Spawn Worker 1 to refactor `generate_html.py` to output the enhanced light theme with programmatic SVGs.
- Integrate assets: Slide 3 (CAFM simulation video), Slide 7 (GP fitting video), Slide 8 (ARD length scales image), Slide 9 (Parity and Residuals side-by-side images), Slide 10 (PDP image), Slide 11 (UQ heatmap image), Slide 14 (3-way AL comparison image + time bars), Slide 15 (Key Takeaways full-width grid).
- Apply styling fixes: viewport scaling script (1920x1080) in custom engine, relative font sizes, math equation boxes sizing.
- Adhere to the user's detailed outline for Slide 14 and 15:
  - Slide 14: Title "Benchmark Analysis: The Victory of the Hybrid Architecture", left: `ultimate_3way_al_comparison.png`, right: computation time bars, Result Table (M1 fast/missed peaks, M2 true peak/unstable, M3 hybrid/stable under 0.7s), and Emil's Paradox explanation.
  - Slide 15: Title "Key Takeaways and Future Horizons", Physical Discoveries (crossing time dictated by speed, density, flow ratio), and Next Steps (Global Variance Decomposition, Gridlock Hunting).

### 3. Automated & Visual Verification [PENDING]
- Programmatic asset existence and syntax validator script `verify_presentation.py` inside `html_presentation/`.
- Compile presentation by executing `python generate_html.py`.
- Run validation check: `python verify_presentation.py`.
- Verify responsive layout scaling and confirm no JS/MathJax console errors.

### 4. Review, Audit, and Reporting [PENDING]
- Spawn Reviewers to inspect visual layout and contrast.
- Run Forensic Auditor to verify genuine implementation (development integrity mode).
- Present final report to user.
