# Kho Ngữ liệu Khoa học arXiv — Báo cáo Dự án (`arxiv-book`)

Báo cáo trực tuyến chính thức bằng tiếng Việt của dự án môn **Nhập môn Khoa học Dữ liệu**, được biên dịch bằng [Jupyter Book v1](https://jupyterbook.org/) và xuất bản tự động qua GitHub Pages.

- **Trang báo cáo (GitHub Pages):** <https://giaaphuc.github.io/arxiv-book/>
- **Repository mã nguồn pipeline:** [`GiaaPhuc/arxiv-pipeline`](https://github.com/GiaaPhuc/arxiv-pipeline)

---

## 1. Cấu trúc Cuốn sách (Milestone 1 & Milestone 2)

```text
arxiv-book/
├── _config.yml                      # Cấu hình Jupyter Book v1, thực thi notebook tự động & CSS
├── _toc.yml                         # Mục lục phân theo Part (Milestone 1 & Milestone 2)
├── _static/custom.css               # Định dạng bảng biểu học thuật, sơ đồ luồng & thẻ DAG
├── requirements.txt                 # Môi trường biên dịch sách (Python 3.11)
├── stats/                           # Nơi đặt tệp thống kê JSON/CSV của M1 & M2
│   └── README.md                    # Quy định bộ tệp thống kê M1 & M2 trong stats/
├── m1/                              # Phần 1 — Milestone 1: Thu thập Dữ liệu (giữ nguyên)
│   ├── 01_overview.md               # Chương 1: Tổng quan, phạm vi 25.000 ID & lược đồ 2 bảng M1
│   ├── 02_implementation.md         # Chương 2: Pipeline thu thập, công cụ & chịu lỗi Colab
│   ├── 03_data_statistics.md        # Chương 3: Thống kê & phân tích dữ liệu thu thập (MyST Notebook)
│   └── 04_performance.md            # Chương 4: Hiệu năng bộ thu thập Runtime, RAM & Đĩa (MyST Notebook)
└── m2/                              # Phần 2 — Milestone 2: Phân tích Cú pháp & Chuẩn hóa
    ├── 01_parsing_hierarchy.md      # Chương 5: Lược đồ 3 bảng M2, thu thập đa tệp & cây phân cấp thích ứng
    ├── 02_standardization_dedup.md  # Chương 6: Chuẩn hóa nội dung/toán, BibTeX & khử trùng lặp 2 tầng
    ├── 03_parsing_statistics.md     # Chương 7: Thống kê phân tích cú pháp & hiệu quả khử trùng lặp (MyST Notebook)
    └── 04_parser_performance.md     # Chương 8: Đánh giá hiệu năng bộ phân tích cú pháp trên Colab CPU (MyST Notebook)
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

Hệ thống pipeline thu thập trong `arxiv-pipeline` (phiên bản **v3.10 Clean Lean Turbo / v3.11**: kiến trúc 5 nhóm luồng Producer–Consumer, đệm RAM Zero-Copy 96 MiB, Paced Streaming 4,5 MiB/s, giải nén `_FastGzipStream` 512 KiB giữ `.tex`/`.bib`/`.bbl`, điều nhịp Start-to-Start 3,15 s + jitter, sàn nghỉ socket 3,05 s, Range Resume tại chỗ cho file lớn, nạp hồi băng thông 50 MiB, Bisection chia đôi lô S2 và Dual-Engine Reference Fallback từ `.bib/.bbl`) đã hoàn tất thu thập trọn vẹn **5.000 ID thuộc Dải 1 (`2408.11045` – `2408.16044`)**, bao gồm 8.200 phiên bản và 206.813 mục tài liệu tham khảo với tốc độ ~6,4 – 7,4 giờ / 5.000 ID và 0% lỗi 429.

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
