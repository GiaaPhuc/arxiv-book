# Kho Ngữ liệu Khoa học arXiv — Báo cáo Dự án (`arxiv-book`)

Báo cáo trực tuyến chính thức bằng tiếng Việt của dự án môn **Nhập môn Khoa học Dữ liệu**, được biên dịch bằng [Jupyter Book v1](https://jupyterbook.org/) và xuất bản tự động qua GitHub Pages.

- **Trang báo cáo (GitHub Pages):** <https://giaaphuc.github.io/arxiv-book/>
- **Repository mã nguồn pipeline:** [`GiaaPhuc/arxiv-pipeline`](https://github.com/GiaaPhuc/arxiv-pipeline)

---

## 1. Cấu trúc Cuốn sách (Milestone 1, 2 & 3)

```text
arxiv-book/
├── _config.yml                      # Cấu hình Jupyter Book v1, thực thi notebook tự động & CSS
├── _toc.yml                         # Mục lục phân theo Part (Milestone 1, Milestone 2 & Milestone 3)
├── _static/custom.css               # Định dạng bảng biểu học thuật, sơ đồ luồng & thẻ DAG
├── requirements.txt                 # Môi trường biên dịch sách (Python 3.11)
├── stats/                           # Nơi đặt tệp thống kê JSON/CSV gọn nhẹ của M1, M2 & M3
│   ├── README.md                    # Quy định bộ tệp thống kê M1, M2 & M3
│   ├── m1/                          # Bộ 4 tệp thống kê Milestone 1 (25.000 ID — JSON/CSV)
│   ├── m2/                          # Bộ 4 tệp thống kê Milestone 2 (25.000 ID — JSON/CSV)
│   └── m3/                          # Bộ 4 tệp thống kê Milestone 3 (range_0 5.000 ID — JSON/CSV)
├── m1/                              # Phần 1 — Milestone 1: Thu thập Dữ liệu
│   ├── 01_overview.md               # Chương 1: Tổng quan, phạm vi 25.000 ID & lược đồ 2 bảng M1
│   ├── 02_implementation.md         # Chương 2: Pipeline thu thập, công cụ & chịu lỗi Colab
│   ├── 03_data_statistics.md        # Chương 3: Thống kê & phân tích dữ liệu thu thập (MyST Notebook)
│   └── 04_performance.md            # Chương 4: Hiệu năng bộ thu thập Runtime, RAM & Đĩa (MyST Notebook)
├── m2/                              # Phần 2 — Milestone 2: Phân tích Cú pháp & Chuẩn hóa
│   ├── 01_parsing_hierarchy.md      # Chương 5: Lược đồ 3 bảng M2, thu thập đa tệp & cây phân cấp thích ứng
│   ├── 02_standardization_dedup.md  # Chương 6: Chuẩn hóa nội dung/toán, BibTeX & khử trùng lặp 2 tầng
│   ├── 03_parsing_statistics.md     # Chương 7: Thống kê phân tích cú pháp & hiệu quả khử trùng lặp (MyST Notebook)
│   └── 04_parser_performance.md     # Chương 8: Đánh giá hiệu năng bộ phân tích cú pháp (MyST Notebook)
└── m3/                              # Phần 3 — Milestone 3: Đối sánh Tham chiếu & Công bố Dữ liệu
    ├── 01_cleaning_features.md      # Chương 9: Tiền xử lý thực thể & Bộ 21 đặc trưng đa chiều (Non-LLM)
    ├── 02_labelling_ranking_hf.md   # Chương 10: Gán nhãn 2 tầng, LambdaMART & Đóng gói 6 bảng Hugging Face
    ├── 03_matching_statistics.md    # Chương 11: Thống kê gán nhãn, kiểm toán & đóng góp đặc trưng (MyST Notebook)
    └── 04_model_evaluation_hf.md    # Chương 12: Đánh giá MRR@5, Ablation M2 & kiểm chứng Hugging Face (MyST Notebook)
```

---

## 2. Hướng dẫn Biên dịch Cục bộ

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1    # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python build_book.py            # hoặc: jupyter-book build .
```

Kết quả biên dịch nằm tại `_build/html/index.html`.

---

## 3. Trạng thái Dữ liệu Hiện tại (Hoàn tất Milestone 1, 2 & 3)

- **Milestone 1 (`stats/m1/`):** Hoàn tất thu thập toàn bộ **25.000 / 25.000 ID** thuộc 5 dải (`2406.07938` – `2408.16044`) với **41.629 phiên bản** (`99,51%` thành công cấp bài báo, `99,67%` cấp phiên bản) và **3.480.899 mục tài liệu tham khảo** (trong đó `547.991` mục mang `arXiv ID`). Đã đồng bộ trong Chương 1–4.
- **Milestone 2 (`stats/m2/`):** Hoàn tất phân tích cú pháp, chuẩn hóa và khử trùng lặp cho toàn bộ **25.000 bài báo / 41.629 phiên bản** (`papers_failed = 0`), sinh ra **`14.880.359` phần tử `elements`** (giảm `34,90%` so với `22.856.948` nút trước khử trùng lặp), **`22.516.391` cạnh `hierarchy`**, và **`1.390.532` bản ghi `bibtex`** (giảm `57,76%` so với `3.292.097` bản ghi thô), lưu trên `50` shard/bảng (`898,48 MiB` đầu ra từ `23,550 GiB` mã nguồn `.tex`/`.bib` — thu gọn `26,84×`) trong **`1.688,11 s` (`28,14 phút`)** trên `12` worker song song. Đã đồng bộ trong Chương 5–8.
- **Milestone 3 (`stats/m3/`):** Hoàn tất đối sánh tham chiếu không dùng LLM/pretrained trên lát cắt thực tế **`range_0` (`2408.11045`–`2408.16044`, 5.000 ID)** với **`515` bài báo** (`5` bài Manual Gold `114` truy vấn + `510` bài Auto Silver `26.845` truy vấn; độ phủ `10,21%` toàn dải và `12,02%` tập có BibTeX; Auto-Matcher Audit đạt `Precision = 100,00%`, `Recall = 65,12%`, `F1 = 78,87%`). Mô hình `LightGBM LambdaMART` (21 đặc trưng) đạt **`MRR@5 (matchable) = 1,0000`** (`Hit@1 = 100%`, `MRR@5_all = 0,7755`) trên `test` và **`MRR@5 (matchable) = 0,7722`** (`Hit@5 = 100%`) trên `valid`, đóng gói hợp lệ **`7.693.326` dòng** trên **6 bảng ZSTD Parquet** (`185,28 MiB`, `17` shards) tương thích `datasets.load_dataset`. Đã đồng bộ trong Chương 9–12.

Quy trình tái cập nhật khi có dữ liệu mới:

1. **Chép 4 tệp thống kê tương ứng vào `arxiv-book/stats/m1/`, `stats/m2/` hoặc `stats/m3/`** — tuyệt đối không commit các tệp `.parquet`.
2. **Kiểm tra & đồng bộ câu nhận xét tại các chương liên quan** nếu số liệu thay đổi.
3. **Biên dịch & kiểm tra cục bộ:** Chạy `python build_book.py` (hoặc `jupyter-book build .`) để kiểm tra biên dịch sạch 100%, sau đó đẩy lên GitHub Pages.

---

## 4. Thành viên Thực hiện (Team)

| Vai | Họ và tên | Trọng tâm Milestone 1 | Trọng tâm Milestone 2 | Trọng tâm Milestone 3 |
| :---: | :--- | :--- | :--- | :--- |
| **A** | **Võ Gia Phúc** *(Leader)* | Điều phối pipeline (`pipeline.py`), HTTP/rate limits (`http.py`), SQLite manifest (`manifest.py`), sao lưu (`checkpoint.py`), đo lường (`metrics.py`) | Hợp đồng dữ liệu chung (`parsing/models.py`), CLI `run_parse.py`, điều phối đa tiến trình (`parsing/pipeline.py`) & profiling | Hợp đồng 21 đặc trưng (`matching/models.py`), Stage-1 blocking & đặc trưng tương đối (`features.py`), điều phối `matching/pipeline.py`, CLI `run_matching.py`, đóng gói 6 bảng Hugging Face (`export_hf.py`) |
| **B** | **Trần Thanh Sơn** | Tiện ích dải ID (`ids.py`), khám phá Atom API & OAI-PMH (`discovery.py`), tích hợp Semantic Scholar (`s2.py`) | Mở rộng macro & dọn lệnh trình bày (`parsing/cleaner.py`), chuẩn hóa toán học (`math_normalizer.py`), tách câu ngữ cảnh (`sentence_splitter.py`) | Tiền xử lý thực thể TeX/Unicode & tách tác giả (`matching/cleaner.py`), 15 đặc trưng từ vựng/thực thể/thời gian/mỏ neo & TF-IDF ký tự cục bộ (`lexical_features.py`) |
| **C** | **Phạm Trường Quỳnh** | Fixture lưu trữ tổng hợp (`conftest.py`), tải dòng `/src/` & giải nén chọn lọc `.tex`/`.bib`/`.bbl` (`source.py`) | Thu thập đa tệp & khử comment (`gathering.py`), dựng cây phân cấp & tách mục tham khảo (`hierarchy.py`) | CLI gán nhãn thủ công tương tác, chia tập cấp bài báo, Cohen's Kappa (`labelling.py`), bộ đối sánh tự động 3 tầng & kiểm toán P/R/F1 (`auto_matcher.py`) |
| **D** | **Trần Nguyễn Lâm Gia Thụ** | Giao diện đọc kho dữ liệu (`corpus.py`), xuất bảng Parquet/CSV & thống kê tổng hợp (`export.py`, `export_data.py`) | Trích xuất BibTeX/BibLaTeX & `.bbl`/`\bibitem` (`bib_extractor.py`), khử trùng lặp 2 tầng xuyên phiên bản (`dedup.py`), xuất Sharded Parquet (`export_m2.py`) | Huấn luyện có trọng số theo nhóm truy vấn (`train_ranker.py`), 3 mô hình baseline & `LightGBM LambdaMART` kèm hậu xử lý Top-5 (`ranker.py`) |
| **E** | **Thân Nguyễn Quang Triệu** | Kiểm định 5 bất biến kho ngữ liệu hậu thu thập (`crawler/validate_corpus.py`), xây dựng báo cáo Jupyter Book (`arxiv-book`) | Kiểm định 8 bất biến Parquet & độ bao phủ phiên bản (`parsing/validate_m2.py`), chương thống kê & hiệu năng M2 trên sách | Chỉ mục trích dẫn cây AST M2 (`hierarchy_features.py`), đánh giá `MRR@5` hai mẫu số (`evaluation.py`) & sinh biểu đồ Poster 300 DPI (`plots.py`) |
