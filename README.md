# KIT Germany Research: Active Learning & Surrogate Modeling (Ongoing Writing Paper)

This repository contains the ongoing research code, simulation models, and presentation assets for a study on Active Learning and Surrogate Modeling applied to Conductive Atomic Force Microscopy (CAFM) and 6-dimensional parameter spaces. The project evaluates multiple sampling and optimization techniques against Gaussian Process Regression (GPR) and Bayesian Neural Networks (BNNs).

> **Note:** This project is currently in the "Ongoing writing paper" phase. Code, datasets, and architectures are subject to evolution as the manuscript is finalized.

## Architecture Overview

\\\
Experiment Design & Sampling (6D Input Space)
    │
    ▼
┌────────────────────────────────────────────────────────┐
│  Sampling Strategies (M0 to M7)                        │
│  - M0: Random Baseline      - M4: MC Batch             │
│  - M1: Sobol Grid           - M5: Bayesian Coreset     │
│  - M2: Multi-Start Hybrid   - M6: Maximal Joint Entropy│
│  - M3: KMeans Pool          - M7: Trajectory Opt.      │
└──────────┬─────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────┐      ┌────────────────────────┐
│  Simulation Engine       │      │  CAFM Simulation       │
│  (6D Objective Function) │ ──── │  (cafm_sim_v3.py)      │
└──────────┬───────────────┘      └────────────────────────┘
           │
           ▼
┌────────────────────────────────────────────────────────┐
│  Surrogate Modeling & Uncertainty Quantification       │
│  - Gaussian Process Regression (GPR)                   │
│  - Bayesian Neural Networks (BNN)                      │
└──────────┬─────────────────────────────────────────────┘
           │
           ▼
┌────────────────────────────────────────────────────────┐
│  Analysis & Visualization Engine                       │
│  - HTML Presentation Engine (index.html)               │
│  - PDF/GIF generation (make_pdf_anim.py, export_*.py)  │
└────────────────────────────────────────────────────────┘
\\\

## System Output

The system generates extensive empirical results across all sampling methods, outputting both serialized models and visualizations:

| Method / Output | File Format | Content / Purpose |
|---|---|---|
| Method Metrics | \.pkl\ & \.csv\ | e.g., \M5_Bayesian_Coreset_results.pkl\ containing iterations, acquisition scores, and MSE. |
| Heatmaps & Parity | \.png\ | Partial dependence plots, variance heatmaps, and method comparison charts. |
| Animations | \.mp4\ / \.gif\ | Animated evolutions of GP fitting and CAFM simulations. |
| Presentation | \.html\ | A JS-driven interactive slide deck for research presentation. |

## Directory Structure

\\\
├── 6d_GP_randomVSoptimizer.ipynb   # 6D GPR active learning comparisons
├── BNN_code.ipynb                  # Bayesian Neural Network implementations
├── cafm_sim_v3.py                  # Core CAFM simulator
├── uq_analysis.py                  # Uncertainty Quantification analysis
├── lhs_generator.py                # Latin Hypercube Sampling tools
│
├── html_presentation/              # Custom HTML/JS slide rendering engine
│   └── index.html                  # Main presentation deck
│
├── *.pkl / *.csv                   # Serialized ML runs (M0 to M7 outputs)
├── *.png / *.mp4                   # Visual outputs and animations
│
├── README.md                       # Research architecture documentation
└── PROJECT.md                      # UI/Presentation deck milestones
\\\

## How to Run

### 1. Prerequisites
- Python 3.10+
- Jupyter Notebook / Lab
- Scientific libraries: \scikit-learn\, \GPyTorch\/\PyTorch\, \
umpy\, \matplotlib\
- LaTeX (for \nimate\ package PDF generation)

### 2. Install Dependencies

\\\ash
# (Assuming a standard data science environment)
pip install numpy pandas scikit-learn torch gpytorch matplotlib seaborn
\\\

### 3. Run the Experiments
1. **Surrogate Modeling**: Open and run \6d_GP_randomVSoptimizer.ipynb\ to execute the comparative active learning loop.
2. **CAFM Simulation**: Run the simulation scripts directly to generate spatial data:
   \\\ash
   python cafm_sim_v3.py
   \\\
3. **Visualization**: Run \export_cafm_gif.py\ or \make_pdf_anim.py\ to generate the figures for the paper.

### 4. View Presentation
Open \html_presentation/index.html\ in any modern web browser to view the interactive research presentation.

## Key Design Decisions

1. **Active Learning Benchmarking**: Implementing 8 distinct sampling techniques (M0-M7) allows rigorous, empirically sound comparison for surrogate model convergence on computationally expensive simulations.
2. **Multi-Model Uncertainty**: Using both GPR and BNNs ensures that uncertainty quantification (UQ) isn't biased by a single algorithm's prior assumptions, crucial for robust 6D optimization.
3. **Web-Native Presentation**: Instead of PowerPoint, the research deck is built as an HTML/JS engine (\index.html\), enabling flawless embedding of SVG animations, interactive parameter plots, and high-DPI scientific visuals directly connected to the Python output directories.
