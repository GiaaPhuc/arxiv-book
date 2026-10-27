# arxiv-book — Milestone 1 (arXiv crawler)

Báo cáo Milestone 1 (tiếng Việt), build bằng [Jupyter Book v1](https://jupyterbook.org/) và GitHub Pages.

## Build cục bộ

```bash
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
jupyter-book build .
# Mở _build/html/index.html
```

## Cấu trúc

- `m1/01_overview.md` — mục tiêu, nguồn, quy ước thu thập (số thật: Phase 2).
- `m1/03_data_statistics.ipynb` — thống kê từ **số mẫu** trong `stats/` (chưa phải crawl).
- `.github/workflows/deploy-book.yml` — build và deploy Pages khi push `main`.

Repo mã crawler: https://github.com/GiaaPhuc/arxiv-pipeline

GitHub Pages (sau khi Actions deploy): https://giaaphuc.github.io/arxiv-book/
