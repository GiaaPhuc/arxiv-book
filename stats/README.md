# Thư mục Dữ liệu Thống kê (`arxiv-book/stats/`)

Thư mục này chứa các tệp thống kê gọn nhẹ (JSON/CSV) được kết xuất từ kho ngữ liệu làm việc để biên dịch tự động toàn bộ bảng biểu và đồ thị của **Milestone 1**, **Milestone 2** và **Milestone 3**:

```bash
# Milestone 1 — Kiểm chứng & xuất thống kê thu thập:
python src/crawler/validate_corpus.py --data-dir data
python src/crawler/export_data.py --data-dir data --stats-only

# Milestone 2 — Phân tích cú pháp, xuất Sharded Parquet + stats & kiểm chứng 8 bất biến:
python src/run_parse.py --data-dir data --out-dir data/parsed --stats-dir data/stats --workers 4
python src/parsing/validate_m2.py --data-dir data

# Milestone 3 — Đối sánh tham chiếu, đánh giá MRR@5 & đóng gói 6 bảng Hugging Face:
python src/run_matching.py --data-dir data --range-index 0 --auto-fraction 0.12 --export-hf --verify-hf --plot-figures
```

## 1. Bộ 4 tệp thống kê của Milestone 1 (`stats/m1/`)

Tập thống kê Milestone 1 quy mô toàn bộ `25.000` ID được đặt tại `stats/m1/` (giữ tương thích tìm kiếm lùi `stats/`).

| Tệp bắt buộc | Nguồn sinh ra | Chương sử dụng trong sách |
| :--- | :--- | :--- |
| `summary.json` | `crawler/export_data.py` (`export_stats`) | Chương 3 (Mục 3.1–3.4) & Chương 4 (Mục 4.2) |
| `papers_stats.csv` | `crawler/export_data.py` (`export_stats`) | Chương 3 (Mục 3.1, 3.4 — phân phối & phân vị tham khảo) |
| `versions_stats.csv` | `crawler/export_data.py` (`export_stats`) | Chương 3 (kiểm tra đối chiếu cấp phiên bản) |
| `performance.json` | Bản sao `data/logs/metrics.json` qua `crawler/export_data.py` | Chương 4 (Mục 4.2 Runtime & Mục 4.3 RAM/Đĩa) |
| `stats/crawl.log` *(nhật ký đối chiếu)* | Bản sao `data/logs/crawl.log` (`150.202` dòng, `14,59 MiB`, đã lọc bí mật qua `SecretRedactingFilter`) | Chương 4 (Mục 4.2.1 — liên kết GitHub đối chiếu trực tiếp thời gian chạy của cả 18 phiên Google Colab CPU-only) |

## 2. Bộ 4 tệp thống kê của Milestone 2 (`stats/m2/`)

Tập thống kê Milestone 2 (`25.000` bài báo / `41.615` phiên bản) được đặt tại `stats/m2/`. Quy ước đọc chuỗi ID `arxivid` luôn dùng `dtype={"arxivid": str}` khi nạp bằng `pandas.read_csv()`.

| Tệp bắt buộc | Nguồn sinh ra | Chương sử dụng trong sách |
| :--- | :--- | :--- |
| `stats/m2/m2_summary.json` | `parsing/export_m2.py` (`ShardedParquetExporter.close`) | Chương 7 (Mục 7.1–7.4 — độ phủ phiên bản, tỷ lệ dùng tệp `.tex`, khử trùng lặp văn bản & BibTeX tổng hợp) |
| `stats/m2/m2_papers_stats.csv` | `parsing/export_m2.py` (`PaperStats` cấp bài báo) | Chương 7 (Mục 7.2 phân phối `n_elements`; Mục 7.3 phân tầng $N=1,2,3,\ge 4$; Mục 7.4 `Field Union` từ các cột `*_before`/`*_after` & phân vị BibTeX) & Chương 8 (Mục 8.2 phân phối độ trễ cấp bài báo) |
| `stats/m2/m2_elements_kind.csv` | `parsing/export_m2.py` | Chương 7 (Mục 7.2 — phân bố 8 loại nút `kind` trên `14.879.728` phần tử duy nhất) |
| `stats/m2/m2_performance.json` | `parsing/pipeline.py` (`_save_performance`) | Chương 8 (Mục 8.2 Runtime thực thi & phân rã CPU 4 chặng trên `12` worker; Mục 8.3 RAM RSS & dung lượng Sharded Parquet) |

## 3. Bộ 4 tệp thống kê của Milestone 3 (`stats/m3/`)

Tập thống kê Milestone 3 (trích xuất từ lát cắt thực nghiệm `range_0` — `5.000` ID: `2408.11045`–`2408.16044`) được đặt tại `stats/m3/`. Quy ước đọc `m3_papers_stats.csv` luôn dùng `dtype={"arxivid": str}`.

| Tệp bắt buộc | Nguồn sinh ra | Chương sử dụng trong sách |
| :--- | :--- | :--- |
| `stats/m3/m3_summary.json` | Tổng hợp từ `matching_summary.json`, `coverage.json`, `splits.json`, `predictions.parquet` & `hf_range_0` | Chương 11 (Mục 11.1–11.3 — phễu quy mô, độ phủ Auto-Matcher, kiểm toán Gold & phân rã `splits`) & Chương 12 (Mục 12.3 hiệu năng) |
| `stats/m3/m3_evaluation.json` | Bản sao `data/matching/range_0/evaluation_results.json` từ `matching/pipeline.py` | Chương 11 (Mục 11.4 — `feature_importance_gain`) & Chương 12 (Mục 12.1–12.2 — `MRR@5` Test/Valid, 4 mô hình, Ablation M2 & metadata) |
| `stats/m3/m3_papers_stats.csv` | Tổng hợp cấp bài báo từ `predictions.parquet`, `manual_annotations.json` & `audit_auto_matcher` (`515` bài) | Chương 11 (Mục 11.2 bảng chi tiết 5 bài Manual Gold + Audit TP/FP/FN/TN; Mục 11.3 phân phối số truy vấn mỗi bài) |
| `stats/m3/m3_hf_tables.csv` | Đo đạc từ `data/hf_range_0/data/` (`papers`, `references`, `elements`, `hierarchy`, `bibtex`, `predictions`) | Chương 12 (Mục 12.3 — bảng & biểu đồ quy mô 6 bảng Sharded Parquet chuẩn Hugging Face) |

> **Lưu ý bảo mật dữ liệu:** Tuyệt đối **không** commit các bảng dữ liệu Parquet (`papers.parquet`, `references.parquet`, `data/parsed/*/*.parquet`, `data/matching/*/predictions.parquet`, `data/hf_range_*/*`), cơ sở dữ liệu `manifest.sqlite` hay bất kỳ tệp nào trong `data/papers/` vào repository sách hoặc repository mã nguồn.
