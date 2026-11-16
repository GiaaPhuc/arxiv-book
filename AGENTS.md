# Instructions for AI agents

## Start here

1. **Understand repository scope:** `arxiv-book` is the official academic report website (built with [Jupyter Book v1](https://jupyterbook.org/) and published on GitHub Pages at <https://giaaphuc.github.io/arxiv-book/>) for the Introduction to Data Science project. The data collection and pipeline code lives in the sibling repository [`arxiv-pipeline`](https://github.com/GiaaPhuc/arxiv-pipeline). **Do not dump crawler or pipeline implementation source code into this book.**
2. **Read project context first:**
   - Read `README.md` for local build commands, current data status across Milestones 1–3, and repository structure (12 chapters across `m1/`, `m2/`, and `m3/`).
   - Read `_toc.yml` and `_config.yml` to understand the chapter hierarchy (`parts`), active chapters, and build settings.
   - Check `stats/README.md` to understand the statistical data files under `stats/m1/`, `stats/m2/`, and `stats/m3/`.
   - Consult `Y-TUONG-NOI-DUNG.md` when you need design rationale or scoring rubrics.
3. **Data contract & Single Source of Truth:**
   - The lightweight JSON/CSV files under `arxiv-book/stats/m1/`, `stats/m2/`, and `stats/m3/` are the **sole source of truth** for all numbers, tables, and charts.
   - Never invent or guess metrics (IDs, versions, percentages, sizes, runtimes, memory, MRR@5). All numbers in narratives must match `stats/`.

## Authoring & Coding behavior

Guidelines to prevent common LLM writing and coding mistakes. Bias toward academic rigor, accuracy, and reproducibility.

### 1. Think before writing / coding

Don't assume. Don't hallucinate numbers. Surface tradeoffs.

- Base all analytical claims strictly on data from `stats/` or documented pipeline architecture.
- If multiple interpretations of a chart or statistic exist, explain them objectively.
- If a simpler chart or table communicates the finding more clearly, prefer simplicity.
- Maintain an academic, professional, and objective tone throughout (written in Vietnamese).

### 2. Simplicity first

Minimum code and narrative that delivers high-impact reporting. Nothing speculative.

- Keep Python code in `{code-cell}` concise, self-contained, and deterministic.
- Avoid bulky, complex plotting logic or unnecessary dependencies outside `matplotlib`, `numpy`, and `pandas`.
- No verbose boilerplate text or repetitive filler paragraphs.
- Charts must have clean titles, labeled axes, readable fonts, and consistent styling matching `_static/custom.css`.

### 3. Surgical changes

Touch only what you must. Clean up only your own changes.

- When updating a chapter, modify only the targeted sections.
- Do not blindly reformat existing MyST blocks, Jupytext YAML headers (`--- jupytext: ... ---`), or custom HTML components (`.corpus-tree-card`, `.pipeline-flow`, `.jb-dag-grid`).
- Preserve valid LaTeX formulas (`$...$`, `$$...$$`) and admonitions (`{admonition}`).
- If editing code cells, ensure helper functions (such as `_find_stats_dir()`) remain robust to execution from both root and subdirectories, and always pass `dtype={"arxivid": str}` when reading CSVs with arXiv IDs.

### 4. Goal-driven execution

Define success criteria. Verify with a clean build.

- Always verify locally before concluding any task:
  ```powershell
  .\.venv\Scripts\Activate.ps1
  python build_book.py
  ```
- Build must succeed with zero execution errors (`allow_errors: false`).

## Book & Data integrity rules

1. **Dynamic generation, no static fakes:**
   - All summary tables and charts in quantitative chapters (`m1/03_data_statistics.md`, `m1/04_performance.md`, `m2/03_parsing_statistics.md`, `m2/04_parser_performance.md`, `m3/03_matching_statistics.md`, `m3/04_model_evaluation_hf.md`) **must** be generated dynamically via Python code cells (`{code-cell} ipython3`) executed during book compilation.
   - Never insert hardcoded static screenshots or fabricated markdown tables in place of data-driven charts/tables.
2. **Hidden code cells:**
   - Every analytical `{code-cell} ipython3` must include `:tags: [remove-input]` in its options. The published book must show only polished tables, figures, and narratives—never raw Python code.
3. **Data synchronization protocol:**
   - When new stats arrive from `arxiv-pipeline`:
     1. Overwrite the 4 files in `stats/m1/`, `stats/m2/`, or `stats/m3/`.
     2. Rebuild the book to inspect new outputs.
     3. Synchronize textual commentary to match the new numbers and remove provisional notes/admonitions.
     4. Re-run `python build_book.py` to confirm a clean build.
4. **MyST & Jupyter Book conventions:**
   - Use MyST admonition syntax: ````{admonition} Title \n :class: note|important|warning|tip \n Content \n ````.
   - If creating non-chapter markdown files (notes, documentation, prompt templates), always add them to `exclude_patterns` in `_config.yml` so Sphinx does not raise orphan document warnings.
5. **Multi-Milestone continuity:**
   - Follow the structure defined in `_toc.yml`: `m1/` for Milestone 1, `m2/` for Milestone 2 (parsing, BibTeX extraction, dedup, benchmark), and `m3/` for Milestone 3 (reference matching, MRR@5 ranking, Hugging Face release).
   - Maintain uniform terminology and consistent styling across milestones.

## Rules & Git hygiene

- **Forbidden files in Git:** Never commit raw parquet datasets (`*.parquet`), SQLite databases (`*.sqlite*`), downloaded `.tar.gz` packages, or `data/papers/`.
- **Ignore build artifacts:** Never commit `_build/`, `_jupyter_cache/`, `.venv*`, or `__pycache__/`.
- **Execution limits:** Jupyter Book runs with `timeout: 180` and `allow_errors: false`. All code cells must execute within seconds and handle missing data gracefully.
- **Pre-commit verification:** Before finishing any task, run `python build_book.py` (or `jupyter-book build .`) and verify that `_build/html/index.html` builds without errors or warnings.
