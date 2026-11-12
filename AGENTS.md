# Instructions for AI agents

## Start here

1. **Understand repository scope:** `arxiv-book` is the official academic report website (built with [Jupyter Book v1](https://jupyterbook.org/) and published on GitHub Pages at <https://giaaphuc.github.io/arxiv-book/>) for the Introduction to Data Science project. The data collection and pipeline code lives in the sibling repository [`arxiv-pipeline`](https://github.com/GiaaPhuc/arxiv-pipeline). **Do not dump crawler or pipeline implementation source code into this book.**
2. **Read project context first:**
   - Read `README.md` for local build commands, current data status (e.g., 15.000 vs 25.000 ID sync roadmap), and repository structure.
   - Read `_toc.yml` and `_config.yml` to understand the chapter hierarchy (`parts`), active chapters, and build settings.
   - Check `stats/README.md` to understand the 4 statistical data files.
   - Consult `Y-TUONG-NOI-DUNG.md` or `BOOK-MAU-M1.md` when you need design rationale, scoring rubrics, or chapter outlines.
3. **Data contract & Single Source of Truth:**
   - The 4 files in `arxiv-book/stats/` (`summary.json`, `papers_stats.csv`, `versions_stats.csv`, `performance.json`) are the **sole source of truth** for all numbers, tables, and charts.
   - Never invent or guess metrics (IDs, versions, percentages, sizes, runtimes, memory). All numbers in narratives must match `stats/`.

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
- Avoid bulky, complex plotting logic or unnecessary dependencies outside `matplotlib` and `pandas`.
- No verbose boilerplate text or repetitive filler paragraphs.
- Charts must have clean titles, labeled axes, readable fonts, and consistent styling matching `_static/custom.css`.

### 3. Surgical changes

Touch only what you must. Clean up only your own changes.

- When updating a chapter, modify only the targeted sections.
- Do not blindly reformat existing MyST blocks, Jupytext YAML headers (`--- jupytext: ... ---`), or custom HTML components (`.corpus-tree-card`, `.pipeline-flow`).
- Preserve valid LaTeX formulas (`$...$`, `$$...$$`) and admonitions (`{admonition}`).
- If editing code cells, ensure helper functions (such as `_find_stats_dir()`) remain robust to execution from both root and subdirectories.

### 4. Goal-driven execution

Define success criteria. Verify with a clean build.

- "Update statistics for 25.000 ID" → verify `stats/` updated, tables and charts re-render, text numbers match, and pending markers (`[⏳ ...]`, `admonition`) are cleaned up.
- "Add Chapter X" → create markdown file, register in `_toc.yml`, build book, and verify rendered HTML output.
- Always verify locally before concluding any task:
  ```powershell
  .\.venv\Scripts\Activate.ps1
  jupyter-book build .
  ```
- Build must succeed with zero execution errors (`allow_errors: false`).

## Book & Data integrity rules

1. **Dynamic generation, no static fakes:**
   - All summary tables and charts in quantitative chapters (e.g., `m1/03_data_statistics.md`, `m1/04_performance.md`, and future M2/M3 chapters) **must** be generated dynamically via Python code cells (`{code-cell} ipython3`) executed during book compilation.
   - Never insert hardcoded static screenshots or fabricated markdown tables in place of data-driven charts/tables.
2. **Hidden code cells:**
   - Every analytical `{code-cell} ipython3` must include `:tags: [remove-input]` in its options. The published book must show only polished tables, figures, and narratives—never raw Python code.
3. **Data synchronization protocol:**
   - When new stats arrive from `arxiv-pipeline` (e.g. going from 15k to 25k IDs):
     1. Overwrite the 4 files in `stats/` (`summary.json`, `papers_stats.csv`, `versions_stats.csv`, `performance.json`).
     2. Rebuild the book to inspect new outputs.
     3. Synchronize textual commentary (Mục 1.2, 3.1–3.4, 4.2–4.3) to match the new numbers and remove provisional notes/admonitions.
     4. Re-run `jupyter-book build .` to confirm a clean build.
4. **MyST & Jupyter Book conventions:**
   - Use MyST admonition syntax: ````{admonition} Title \n :class: note|important|warning|tip \n Content \n ````.
   - If creating non-chapter markdown files (notes, documentation, prompt templates), always add them to `exclude_patterns` in `_config.yml` so Sphinx does not raise orphan document warnings.
5. **Multi-Milestone continuity:**
   - Follow the structure defined in `_toc.yml`: `m1/` for Milestone 1, `m2/` for Milestone 2 (parsing, BibTeX extraction, regex/AST benchmark), and `m3/` for Milestone 3 (citation linking, Hugging Face release).
   - Maintain uniform terminology and consistent styling across milestones.

## Rules & Git hygiene

- **Forbidden files in Git:** Never commit raw parquet datasets (`*.parquet`), SQLite databases (`*.sqlite*`), downloaded `.tar.gz` packages, or `data/papers/`.
- **Ignore build artifacts:** Never commit `_build/`, `_jupyter_cache/`, `.venv*`, or `__pycache__/`.
- **Execution limits:** Jupyter Book runs with `timeout: 180` and `allow_errors: false`. All code cells must execute within seconds and handle missing data gracefully.
- **Pre-commit verification:** Before finishing any task, run `jupyter-book build .` and verify that `_build/html/index.html` builds without errors or warnings.
