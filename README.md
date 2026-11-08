# Kho Ngữ liệu Khoa học arXiv — Báo cáo Dự án (`arxiv-book`)

Báo cáo trực tuyến chính thức bằng tiếng Việt của dự án môn **Nhập môn Khoa học Dữ liệu**, được biên dịch bằng [Jupyter Book v1](https://jupyterbook.org/) và xuất bản tự động qua GitHub Pages.

- **Trang báo cáo (GitHub Pages):** <https://giaaphuc.github.io/arxiv-book/>
- **Repository mã nguồn pipeline:** [`GiaaPhuc/arxiv-pipeline`](https://github.com/GiaaPhuc/arxiv-pipeline)

---

## 1. Cấu trúc Cuốn sách (Milestone 1)

```text
arxiv-book/
├── _config.yml                 # Cấu hình Jupyter Book v1, thực thi notebook tự động & CSS
├── _toc.yml                    # Mục lục phân theo Part (sẵn sàng mở rộng sang Milestone 2 & 3)
├── _static/custom.css          # Định dạng bảng biểu học thuật & nhãn chờ dữ liệu
├── requirements.txt            # Môi trường biên dịch sách (Python 3.11)
├── stats/                      # Nơi đặt 4 tệp thống kê xuất từ export_data.py
│   └── README.md               # Quy định 4 tệp cần chép vào stats/
└── m1/
    ├── 01_overview.md          # Chương 1: Tổng quan, phạm vi 25.000 ID & lược đồ 2 bảng
    ├── 02_implementation.md    # Chương 2: Pipeline đầu–cuối, công cụ & cơ chế chịu lỗi Colab
    ├── 03_data_statistics.md   # Chương 3: Thống kê & phân tích dữ liệu (MyST Notebook, ẩn code)
    └── 04_performance.md       # Chương 4: Đánh giá hiệu năng Runtime, RAM & Đĩa (MyST Notebook, ẩn code)
```

---

## 2. Hướng dẫn Biên dịch Cục bộ

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1    # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
jupyter-book build .
```

Kết quả biên dịch nằm tại `_build/html/index.html`.

---

## 3. Trạng thái Dữ liệu Hiện tại (Snapshot 5.000 ID Dải 1) & Quy trình Cập nhật 25.000 ID

Hệ thống pipeline thu thập trong `arxiv-pipeline` (phiên bản **v3.8**: kiến trúc đa luồng Producer–Consumer, đệm RAM Zero-Copy 96 MiB, giải nén `_FastGzipStream` 512 KiB giữ `.tex`/`.bib`/`.bbl`, điều nhịp Start-to-Start 3,15 s + jitter, phục hồi nhanh 429 và cơ chế Fast-Defer + Cooldown leo thang) đã hoàn tất thu thập trọn vẹn **5.000 ID thuộc Dải 1 (`2408.11045` – `2408.16044`)**, bao gồm 8.200 phiên bản và 206.813 mục tài liệu tham khảo.

Toàn bộ 4 tệp thống kê tại `arxiv-book/stats/` (`summary.json`, `papers_stats.csv`, `versions_stats.csv`, `performance.json`) hiện đã được cập nhật từ snapshot 5.000 ID này và tự động đồng bộ vào toàn bộ bảng biểu, biểu đồ tại Chương 3 và Chương 4 của sách.

Tiến trình crawl đang tiếp tục chạy nối tiếp 20.000 ID còn lại (Dải 2–5). Ngay khi tiến trình crawl hoàn tất toàn bộ 25.000 ID, thực hiện 3 bước cập nhật:

1. **Chép 4 tệp thống kê mới vào `arxiv-book/stats/`:**
   - `summary.json`
   - `papers_stats.csv`
   - `versions_stats.csv`
   - `performance.json`
   $\rightarrow$ **Toàn bộ 6 khối bảng tổng hợp và biểu đồ tại Chương 3 & Chương 4 sẽ tự động sinh số liệu và đồ thị của 25.000 ID** khi biên dịch.

2. **Cập nhật nhận xét văn bản:**
   - `m1/01_overview.md` — **Mục 1.2:** Chuyển trạng thái cả 5 dải sang hoàn tất 100% và cập nhật hộp thông báo tiến độ.
   - `m1/03_data_statistics.md` — Cập nhật con số trong câu nhận xét tại **Mục 3.1, 3.2, 3.3, 3.4** theo bảng mới.
   - `m1/04_performance.md` — Cập nhật con số trong câu nhận xét tại **Mục 4.2, 4.3** theo số đo thực tế.

3. **Biên dịch & xuất bản:**
   - Chạy `jupyter-book build .` để kiểm tra biên dịch sạch 100%, sau đó đẩy lên GitHub Pages.
