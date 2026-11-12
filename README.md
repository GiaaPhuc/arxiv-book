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

## 3. Trạng thái Dữ liệu Hiện tại (`15.000 / 25.000 ID`) & Quy trình Cập nhật Khi Đủ `25.000 ID`

Hiện tại thư mục `arxiv-book/stats/` đã tích hợp đầy đủ 4 tệp thống kê thực nghiệm (`summary.json`, `papers_stats.csv`, `versions_stats.csv`, `performance.json`) từ **đợt thu thập hoàn chỉnh 15.000 ID đầu tiên** (`2408.01045` – `2408.16044`, trọn vẹn Dải 1, Dải 2 và Dải 3 thuộc tháng `2024-08`, đạt `60%` tổng quy mô). Toàn bộ bảng biểu, đồ thị và nhận xét tại Chương 1, Chương 3 và Chương 4 đã được biên dịch hoàn chỉnh với dữ liệu thật 100% và ghi chú minh bạch lộ trình cập nhật.

Ngay khi tiến trình trên Google Colab CPU hoàn tất 10.000 ID còn lại (Dải 4 và Dải 5) để cán mốc **đủ 25.000 ID**, thực hiện 3 bước cập nhật cuối cùng sau:

1. **Ghi đè 4 tệp thống kê mới vào `arxiv-book/stats/`:**
   - `summary.json`
   - `papers_stats.csv`
   - `versions_stats.csv`
   - `performance.json`
   $\rightarrow$ **Toàn bộ 6 khối bảng tổng hợp và biểu đồ tại Chương 3 & Chương 4 sẽ tự động sinh lại số liệu và đồ thị của 25.000 ID** mà không cần sửa bất kỳ dòng code Python nào.

2. **Đồng bộ con số trong văn bản nhận xét từ mốc 15.000 ID sang 25.000 ID & gỡ hộp thông báo tạm thời:**
   - `m1/01_overview.md` — **Mục 1.2:** Cập nhật cột trạng thái bảng 5 dải sang hoàn tất 100% và gỡ hộp `admonition` thông báo tạm thời 15.000 ID.
   - `m1/03_data_statistics.md` — Gỡ hộp thông báo đầu chương và cập nhật con số trong câu nhận xét tại **Mục 3.1, 3.2, 3.3, 3.4** theo bảng mới.
   - `m1/04_performance.md` — Gỡ hộp thông báo đầu chương và cập nhật con số trong câu nhận xét tại **Mục 4.2, 4.3** theo bảng mới.

3. **Biên dịch & xuất bản:**
   - Chạy `jupyter-book build .` để kiểm tra biên dịch sạch 100%, sau đó `git push origin main` để GitHub Actions tự động xuất bản lên GitHub Pages.
