# Thư mục Dữ liệu Thống kê (`arxiv-book/stats/`)

Thư mục này chứa các tệp thống kê gọn nhẹ (JSON/CSV) được kết xuất từ kho ngữ liệu làm việc trên Google Colab CPU để biên dịch tự động toàn bộ bảng biểu và đồ thị của **Milestone 1** và **Milestone 2**:

```bash
# Milestone 1 — Kiểm chứng & xuất thống kê thu thập:
python src/validate_corpus.py --data-dir data
python src/export_data.py --data-dir data --stats-only

# Milestone 2 — Phân tích cú pháp, xuất Sharded Parquet + stats & kiểm chứng 8 bất biến:
python src/run_parse.py --data-dir data --out-dir data/parsed --stats-dir data/stats --workers 2
python src/validate_m2.py --data-dir data
```

## 1. Bộ 4 tệp thống kê của Milestone 1

| Tệp bắt buộc | Nguồn sinh ra | Chương sử dụng trong sách |
| :--- | :--- | :--- |
| `summary.json` | `export_data.py` (`export_stats`) | Chương 3 (Mục 3.1–3.4) & Chương 4 (Mục 4.2) |
| `papers_stats.csv` | `export_data.py` (`export_stats`) | Chương 3 (Mục 3.1, 3.4 — phân phối & phân vị tham khảo) |
| `versions_stats.csv` | `export_data.py` (`export_stats`) | Chương 3 (kiểm tra đối chiếu cấp phiên bản) |
| `performance.json` | Bản sao `data/logs/metrics.json` qua `export_data.py` | Chương 4 (Mục 4.2 Runtime & Mục 4.3 RAM/Đĩa) |

## 2. Bộ 4 tệp thống kê của Milestone 2

| Tệp bắt buộc | Nguồn sinh ra | Chương sử dụng trong sách |
| :--- | :--- | :--- |
| `m2_summary.json` | `parsing/export_m2.py` (`ShardedParquetExporter.close`) | Chương 7 (Mục 7.1–7.4 — độ phủ phiên bản, khử trùng lặp & độ lấp đầy trường BibTeX) |
| `m2_papers_stats.csv` | `parsing/export_m2.py` (`PaperStats` cấp bài báo) | Chương 7 (phân phối theo số phiên bản $N=1,2,3,\ge 4$, lọc tệp `.tex`) & Chương 8 (phân phối thời gian theo bài) |
| `m2_elements_kind.csv` | `parsing/export_m2.py` | Chương 7 (Mục 7.2 — phân bố 8 loại nút `kind` & độ sâu cây phân cấp) |
| `m2_performance.json` | `parsing/pipeline.py` (`_save_performance`) | Chương 8 (Mục 8.2 Runtime theo chặng & Mục 8.3 RAM/Đĩa Parquet trên Colab CPU) |

> **Lưu ý bảo mật dữ liệu:** Tuyệt đối **không** commit các bảng dữ liệu Parquet (`papers.parquet`, `references.parquet`, `data/parsed/elements/*.parquet`, `hierarchy/*.parquet`, `bibtex/*.parquet`), cơ sở dữ liệu `manifest.sqlite` hay bất kỳ tệp nào trong `data/papers/` vào repository sách hoặc repository mã nguồn ở Milestone 1 và Milestone 2.
