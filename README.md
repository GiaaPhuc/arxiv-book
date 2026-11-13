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

## 3. Trạng thái Dữ liệu Hiện tại (Hoàn tất 25.000 / 25.000 ID — 5 Dải)

Hệ thống pipeline thu thập trong `arxiv-pipeline` (phiên bản **v3.14**: Quy trình 2 giai đoạn tách rời Two-Stage Decoupled Protocol `--skip-s2` / `--s2-only`, khám phá siêu dữ liệu ngoại tuyến qua Kaggle snapshot `--snapshot` trong < 60s, kiến trúc 5 nhóm luồng Producer–Consumer, đệm RAM Zero-Copy 96 MiB, **Wire-Speed Streaming** `--max-stream-mbps` 4,5 MiB/s nội địa / 12,0–18,0 MiB/s Cloud, **In-Place Resolution & Proportional Bandwidth Breather** $S / 4{,}0\text{ MiB/s}$ cho gói $\ge 2\text{ MiB}$ với trần 12,0 s và xoay session khi $\ge 30\text{ MiB}$, giải nén `_FastGzipStream` 512 KiB giữ `.tex`/`.bib`/`.bbl`, điều nhịp Start-to-Start 3,15 s + jitter, sàn nghỉ socket 3,05 s, Range Resume tại chỗ cho file lớn, nạp hồi băng thông 50 MiB, Bisection chia đôi lô S2 và Dual-Engine Reference Fallback từ `.bib/.bbl`) đã **hoàn tất thu thập trọn vẹn toàn bộ 25.000 / 25.000 ID thuộc cả 5 dải (`2406.07938` – `2408.16044`)**, bao gồm **41.629 phiên bản** (`99,51%` thành công cấp bài báo, `99,67%` cấp phiên bản) và **3.480.899 mục tài liệu tham khảo** (trong đó 547.991 mục mang `arXiv ID`).

Toàn bộ 4 tệp thống kê tại `arxiv-book/stats/` (`summary.json`, `papers_stats.csv`, `versions_stats.csv`, `performance.json`) và văn bản phân tích trong Chương 1, Chương 3 và Chương 4 đã được đồng bộ đầy đủ với bộ dữ liệu **25.000 ID hoàn chỉnh**. Quy trình tái cập nhật khi có dữ liệu mới:

1. **Chép 4 tệp thống kê M1 (hoặc bộ tệp M2) vào `arxiv-book/stats/`** (`summary.json`, `papers_stats.csv`, `versions_stats.csv`, `performance.json`) — tuyệt đối không commit các tệp `.parquet`.
2. **Kiểm tra & đồng bộ câu nhận xét tại Chương 1, Chương 3 và Chương 4** nếu số liệu thay đổi.
3. **Biên dịch & kiểm tra cục bộ:**
   - Chạy `jupyter-book build .` để kiểm tra biên dịch sạch 100%, sau đó đẩy lên GitHub Pages.
