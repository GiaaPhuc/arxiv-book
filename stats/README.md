# Thư mục Dữ liệu Thống kê (`arxiv-book/stats/`)

Thư mục này là nơi đặt **4 tệp thống kê gọn nhẹ** được xuất từ kho ngữ liệu sau khi chạy hoàn tất pipeline thu thập 25.000 ID trên Google Colab CPU:

```bash
# Chạy bên trong repo arxiv-pipeline sau khi validate_corpus.py thành công:
python src/validate_corpus.py --data-dir data
python src/export_data.py --data-dir data --stats-only
```

## 4 tệp cần chép vào `arxiv-book/stats/`

| Tệp bắt buộc | Nguồn sinh ra | Chương sử dụng trong sách |
| :--- | :--- | :--- |
| `summary.json` | `export_data.py` (`export_stats`) | Chương 3 (Mục 3.1–3.4) & Chương 4 (Mục 4.2) |
| `papers_stats.csv` | `export_data.py` (`export_stats`) | Chương 3 (Mục 3.1, 3.4 — phân phối & phân vị tham khảo) |
| `versions_stats.csv` | `export_data.py` (`export_stats`) | Chương 3 (kiểm tra đối chiếu cấp phiên bản) |
| `performance.json` | Bản sao `data/logs/metrics.json` qua `export_data.py` | Chương 4 (Mục 4.2 Runtime & Mục 4.3 RAM/Đĩa) |

> **Lưu ý bảo mật dữ liệu:** Tuyệt đối **không** commit hai bảng `papers.parquet` và `references.parquet` hay bất kỳ tệp nào trong `data/papers/` vào repository sách hoặc repository mã nguồn ở Milestone 1. Khi đã chép đủ 4 tệp trên, có thể xóa hai tệp mẫu ban đầu (`sample_papers.csv`, `sample_versions.csv`).
