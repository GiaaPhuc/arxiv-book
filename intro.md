# Kho Ngữ liệu Khoa học arXiv — Báo cáo Dự án

```{admonition} Thông tin Dự án & Liên kết Nộp bài Chính thức
:class: note
- **Môn học:** Nhập môn Khoa học Dữ liệu (*Introduction to Data Science* — Chương trình Chuẩn, ngôn ngữ báo cáo: Tiếng Việt).
- **Repository mã nguồn pipeline:** [`https://github.com/GiaaPhuc/arxiv-pipeline`](https://github.com/GiaaPhuc/arxiv-pipeline)
- **Báo cáo trực tuyến (Jupyter Book / GitHub Pages):** <https://giaaphuc.github.io/arxiv-book/>
- **Nguyên tắc liêm chính dữ liệu:** Toàn bộ bảng tổng hợp và biểu đồ định lượng tại Chương 3–4 (Milestone 1), Chương 7–8 (Milestone 2) và Chương 11–12 (Milestone 3) được sinh tự động bằng Python ngay trong quá trình biên dịch sách từ thư mục `stats/` (không sử dụng ảnh chụp màn hình tĩnh và không nhúng mã nguồn cài đặt của pipeline vào sách).
```

## Cấu trúc Quyển Báo cáo & Chiến lược Vận hành Liên hoàn

Cuốn sách trình bày toàn diện thiết kế kỹ thuật, quy trình triển khai, thống kê định lượng và đánh giá hiệu năng của hệ thống xây dựng **Kho Ngữ liệu Khoa học arXiv** quy mô **25.000 định danh** (`2406.07938` – `2408.16044`, tháng `06–08/2024`). Cấu trúc sách được tổ chức tách bạch theo **hai phần cốt lõi bắt buộc** tương ứng với **Milestone 1** và **Milestone 2**, kèm **Phụ lục Mở rộng — Milestone 3** hoàn thiện trọn vẹn chuỗi dự án:

1. **Chương I — Milestone 1: Thu thập Dữ liệu (`m1/01` – `m1/04`):** Thu thập toàn bộ các phiên bản ($v_1 \dots v_N$) của 25.000 bài báo qua `export.arxiv.org`, loại bỏ hình ảnh nhị phân chỉ giữ nguyên bản `.tex`, `.bib`, `.bbl` và làm giàu siêu dữ liệu tham khảo qua **Semantic Scholar Academic Graph API** trên nền kiến trúc **`arxiv-pipeline v3.18`**.
2. **Chương II — Milestone 2: Phân tích Cú pháp & Chuẩn hóa (`m2/01` – `m2/04`):** Xử lý LaTeX đa tệp thuần CPU, chuẩn hóa toán học và tách câu ngữ cảnh, chuyển đổi `.bib`/`.bbl`/`\bibitem`, khử trùng lặp hai tầng xuyên phiên bản theo *"Thứ tự Vàng"* và kiểm định 8 bất biến trên ba bảng Sharded Parquet (`elements`, `hierarchy`, `bibtex`).
3. **Phụ lục Mở rộng — Milestone 3: Đối sánh Tham chiếu & Hugging Face (`m3/01` – `m3/04`):** Phân giải thực thể trích dẫn không dùng LLM/pretrained với 21 đặc trưng đa chiều (tận dụng cấu trúc AST của Milestone 2), xếp hạng `LightGBM LambdaMART` đánh giá qua `MRR@5` hai mẫu số và đóng gói 6 bảng ZSTD Parquet tương thích Hugging Face `datasets` (minh họa hoàn chỉnh trên phân vùng `range_0`: `2408.11045`–`2408.16044`).

**Chiến lược vận hành tập trung toàn nhóm (Quyết định D8):** Nhóm gộp cả **5 dải (`5 × 5.000 = 25.000` arXiv ID)** — lấy nguyên vẹn mọi công bố trong dải mà không lọc theo danh mục hay chuyên ngành — để thu thập và phân tích chung trên môi trường **Google Colab CPU-only** (một tiến trình tuần tự duy nhất có khóa workspace mutex). Cách tiếp cận này giúp tiết kiệm tài nguyên tính toán, tránh nhân bản truy vấn lên `export.arxiv.org` và Semantic Scholar, bảo toàn tính nhất quán của toàn bộ kho dữ liệu; đến cuối Milestone 3 mới tách theo từng dải cá nhân `range_0..range_4` để đóng gói công bố lên Hugging Face.

---

## Thành viên Nhóm & Phân công Vai trò (A–E)

Dự án được thực hiện bởi nhóm **5 thành viên**, phân công theo 5 vai kỹ thuật xuyên suốt từ Milestone 1 đến Milestone 3:

| Vai | Họ và tên | Trọng tâm Milestone 1 | Trọng tâm Milestone 2 | Trọng tâm Milestone 3 |
| :---: | :--- | :--- | :--- | :--- |
| **A** | **Võ Gia Phúc** *(Leader)* | Điều phối pipeline (`pipeline.py`), HTTP/rate limits (`http.py`), SQLite manifest (`manifest.py`), sao lưu (`checkpoint.py`), đo lường (`metrics.py`), tiền kiểm (`preflight.py`) | Hợp đồng dữ liệu chung (`parsing/models.py`), CLI `run_parse.py`, điều phối đa tiến trình (`parsing/pipeline.py`) & profiling | Hợp đồng 21 đặc trưng (`matching/models.py`), Stage-1 blocking & đặc trưng tương đối (`features.py`), điều phối `matching/pipeline.py`, CLI `run_matching.py`, đóng gói 6 bảng Hugging Face (`export_hf.py`) |
| **B** | **Trần Thanh Sơn** | Tiện ích dải ID (`ids.py`), khám phá Atom API & OAI-PMH (`discovery.py`), tích hợp Semantic Scholar (`s2.py`) | Mở rộng macro & dọn lệnh trình bày (`parsing/cleaner.py`), chuẩn hóa toán học (`math_normalizer.py`), tách câu ngữ cảnh (`sentence_splitter.py`) | Tiền xử lý thực thể TeX/Unicode & tách tác giả (`matching/cleaner.py`), 15 đặc trưng từ vựng/thực thể/thời gian/mỏ neo & TF-IDF ký tự cục bộ (`lexical_features.py`) |
| **C** | **Phạm Trường Quỳnh** | Fixture lưu trữ tổng hợp (`conftest.py`), tải dòng `/src/` & giải nén chọn lọc `.tex`/`.bib`/`.bbl` (`source.py`) | Thu thập đa tệp & khử comment (`gathering.py`), dựng cây phân cấp & tách mục tham khảo (`hierarchy.py`) | CLI gán nhãn thủ công tương tác, chia tập cấp bài báo, Cohen's Kappa (`labelling.py`), bộ đối sánh tự động 3 tầng & kiểm toán P/R/F1 (`auto_matcher.py`) |
| **D** | **Trần Nguyễn Lâm Gia Thụ** | Giao diện đọc kho dữ liệu (`corpus.py`), xuất bảng Parquet/CSV & thống kê tổng hợp (`export.py`, `export_data.py`) | Trích xuất BibTeX/BibLaTeX & `.bbl`/`\bibitem` (`bib_extractor.py`), khử trùng lặp 2 tầng xuyên phiên bản (`dedup.py`), xuất Sharded Parquet (`export_m2.py`) | Huấn luyện có trọng số theo nhóm truy vấn (`train_ranker.py`), 3 mô hình baseline & `LightGBM LambdaMART` kèm hậu xử lý Top-5 (`ranker.py`) |
| **E** | **Thân Nguyễn Quang Triệu** | Kiểm định 5 bất biến kho ngữ liệu hậu thu thập (`crawler/validate_corpus.py`), xây dựng báo cáo Jupyter Book (`arxiv-book`) | Kiểm định 8 bất biến Parquet & độ bao phủ phiên bản (`parsing/validate_m2.py`), chương thống kê & hiệu năng M2 trên sách | Chỉ mục trích dẫn cây AST M2 (`hierarchy_features.py`), đánh giá `MRR@5` hai mẫu số (`evaluation.py`) & sinh biểu đồ Poster 300 DPI (`plots.py`) |
