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

## 3. Checklist Hoàn thiện Khi Đã Có Tệp Trong `arxiv-book/stats/`

Hiện tại sách được thiết kế **chống gãy build (graceful fallback)**: khi chưa có bộ tệp thống kê 25.000 ID trong `stats/`, lệnh `jupyter-book build .` vẫn biên dịch thành công 100% và hiển thị thẻ nhắc `⏳ Đang chờ tệp thống kê trong arxiv-book/stats/`.

Ngay khi đợt chạy 25.000 ID trên Google Colab CPU hoàn tất, thực hiện đúng 3 bước sau:

1. **Chép 4 tệp thống kê vào `arxiv-book/stats/`:**
   - `summary.json`
   - `papers_stats.csv`
   - `versions_stats.csv`
   - `performance.json`
   *(Có thể xóa 2 tệp mẫu cũ `sample_papers.csv` và `sample_versions.csv`).*
   $\rightarrow$ **Toàn bộ 6 khối bảng tổng hợp và biểu đồ tại Chương 3 & Chương 4 sẽ tự động sinh số liệu và đồ thị thật 100%** mà không cần sửa bất kỳ dòng code Python nào.

2. **Thay thế các hộp ghi chú `pending-stats` (`⏳`) bằng câu nhận xét chốt số liệu 25.000 ID:**
   - `m1/03_data_statistics.md` — **Mục 3.1:** Nhận xét `papers_success`, `success_rate_papers`, `papers_with_tex` và `ids_not_found`.
   - `m1/03_data_statistics.md` — **Mục 3.2:** Nhận xét tỷ lệ phần trăm `ok` vs `no_source` và số phiên bản trung bình $\bar{V}$.
   - `m1/03_data_statistics.md` — **Mục 3.3:** Nhận xét số byte trung bình trước/sau khi lọc ảnh và mức tiết kiệm dung lượng.
   - `m1/03_data_statistics.md` — **Mục 3.4:** Nhận xét số tham khảo trung bình/trung vị và 3 tỷ lệ Semantic Scholar `(a)`, `(b)`, `(c)`.
   - `m1/04_performance.md` — **Mục 4.1:** Đối chiếu dòng CPU Xeon thực tế từ lệnh `!lscpu` trên phiên Colab cuối cùng.
   - `m1/04_performance.md` — **Mục 4.2:** Chốt nhận xét tổng thời gian chạy đầu–cuối, tổng thời gian khám phá và thời gian trung bình xử lý mỗi bài báo.
   - `m1/04_performance.md` — **Mục 4.3:** Chốt nhận xét RAM đỉnh/trung bình (`MiB`) và dung lượng đĩa tối đa/cuối cùng (`GiB`).

3. **Kiểm tra đóng băng:**
   - Chạy `jupyter-book build .` và xác nhận không còn hộp nhắc `⏳` nào trên trang HTML trước khi `git push origin main` để GitHub Actions xuất bản lên GitHub Pages.
