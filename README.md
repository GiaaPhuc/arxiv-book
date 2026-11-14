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
│   ├── README.md                    # Quy định bộ tệp thống kê M1 & M2
│   ├── m1/                          # Bộ 4 tệp thống kê Milestone 1 (JSON/CSV)
│   └── m2/                          # Bộ 4 tệp thống kê Milestone 2 (JSON/CSV)
├── m1/                              # Phần 1 — Milestone 1: Thu thập Dữ liệu (giữ nguyên)
│   ├── 01_overview.md               # Chương 1: Tổng quan, phạm vi 25.000 ID & lược đồ 2 bảng M1
│   ├── 02_implementation.md         # Chương 2: Pipeline thu thập, công cụ & chịu lỗi Colab
│   ├── 03_data_statistics.md        # Chương 3: Thống kê & phân tích dữ liệu thu thập (MyST Notebook)
│   └── 04_performance.md            # Chương 4: Hiệu năng bộ thu thập Runtime, RAM & Đĩa (MyST Notebook)
└── m2/                              # Phần 2 — Milestone 2: Phân tích Cú pháp & Chuẩn hóa
    ├── 01_parsing_hierarchy.md      # Chương 5: Lược đồ 3 bảng M2, thu thập đa tệp & cây phân cấp thích ứng
    ├── 02_standardization_dedup.md  # Chương 6: Chuẩn hóa nội dung/toán, BibTeX & khử trùng lặp 2 tầng
    ├── 03_parsing_statistics.md     # Chương 7: Thống kê phân tích cú pháp & hiệu quả khử trùng lặp (MyST Notebook)
    └── 04_parser_performance.md     # Chương 8: Đánh giá hiệu năng bộ phân tích cú pháp (MyST Notebook)
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

## 3. Trạng thái Dữ liệu Hiện tại (Hoàn tất Milestone 1 & Milestone 2 — 25.000 / 25.000 ID)

- **Milestone 1 (`stats/m1/`):** Hoàn tất thu thập toàn bộ **25.000 / 25.000 ID** thuộc 5 dải (`2406.07938` – `2408.16044`) với **41.629 phiên bản** (`99,51%` thành công cấp bài báo, `99,67%` cấp phiên bản) và **3.480.899 mục tài liệu tham khảo** (trong đó `547.991` mục mang `arXiv ID`). Đã đồng bộ trong Chương 1, Chương 3 và Chương 4.
- **Milestone 2 (`stats/m2/`):** Hoàn tất phân tích cú pháp, chuẩn hóa và khử trùng lặp cho toàn bộ **25.000 bài báo / 41.629 phiên bản** (`papers_failed = 0`), sinh ra **`14.880.359` phần tử `elements`** (giảm `34,90%` so với `22.856.948` nút trước khử trùng lặp), **`22.516.391` cạnh `hierarchy`**, và **`1.390.532` bản ghi `bibtex`** (giảm `57,76%` so với `3.292.097` bản ghi thô), lưu trên `50` shard/bảng (`898,48 MiB` đầu ra từ `23,550 GiB` mã nguồn `.tex`/`.bib` — thu gọn `26,84×`) trong **`1.688,11 s` (`28,14 phút`)** trên `12` worker song song. Đã đồng bộ trong Chương 5–8.

Quy trình tái cập nhật khi có dữ liệu mới:

1. **Chép 4 tệp thống kê M1 vào `arxiv-book/stats/m1/` hoặc bộ 4 tệp thống kê M2 vào `arxiv-book/stats/m2/`** — tuyệt đối không commit các tệp `.parquet`.
2. **Kiểm tra & đồng bộ câu nhận xét tại các chương liên quan** nếu số liệu thay đổi.
3. **Biên dịch & kiểm tra cục bộ:**
   - Chạy `jupyter-book build .` (hoặc `python build_book.py`) để kiểm tra biên dịch sạch 100%, sau đó đẩy lên GitHub Pages.
