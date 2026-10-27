# M1 — Tổng quan thu thập

> **Khung báo cáo Milestone 1.** Các con số thống kê và hiệu năng ở chương sau là **số mẫu**, chưa phải kết quả crawl 25.000 ID (Phase 2). Số thật sẽ thay sau go/no-go.

## Mục tiêu

Nhóm thu thập **mọi phiên bản** (v1…vN) của từng bài trong dải arXiv ID được giao, giữ siêu dữ liệu bài và tham khảo từ Semantic Scholar (S2), chỉ lưu nguồn `.tex`/`.bib` sau khi trích từ gói `/src/`. Dữ liệu làm việc nằm cục bộ; Milestone 1 **không nộp corpus**, chỉ repo mã và sách này.

## Nguồn và phạm vi

| Nguồn | Cách dùng |
| --- | --- |
| `export.arxiv.org` | API `id_list` (lô 50 ID gốc) để khám phá phiên bản; `/src/{id}vN` để tải gói nguồn |
| Semantic Scholar | Một lần mỗi bài trên ID gốc: `paper/arXiv:{id}`, phân trang references bằng `offset` |
| OAI-PMH, Kaggle | Không dùng để thu hoạch (chỉ tham khảo công cụ) |

Phạm vi ID: **5 dải**, **25.000** ID (tháng 6–8/2024), mỗi thành viên một dải trách nhiệm; **crawl đủ chạy trên một máy** sau Phase 1.

## Vì sao chờ ≥ 3 giây (arXiv)

Theo [hướng dẫn API arXiv](https://info.arxiv.org/help/api/user-manual.html), client phải tránh gửi yêu cầu dồn dập. Nhóm dùng **một kết nối** tới `export.arxiv.org` và chờ **ít nhất 3 giây tính từ lúc yêu cầu trước kết thúc** (cùng limiter cho API và `/src/`). S2 tách host, ≥ 1 yêu cầu/giây, xử lý 429 bằng backoff.

## Gói nguồn và `no_source`

- Nhận diện loại gói: xem **mã HTTP trước**, rồi magic bytes (`tar.gz`, gzip đơn, PDF `%PDF`, zip `PK`).
- Chỉ **trích** `.tex` và `.bib`, giữ cây thư mục tương đối; không sửa nội dung.
- Bản **chỉ có PDF** (hoặc zip/docx không có TeX): trạng thái **`no_source`**, vẫn có `meta.json` và siêu dữ liệu bài — **không bỏ bài** (ví dụ đầu dải 3: `2408.01045v1`).
- 404 → `not_found`; 403/429 → dừng crawl và báo nhóm.

## Hai bảng `papers` và `references`

Xuất từ corpus cục bộ (`export_tables`), schema khóa trong `models.py`:

| Bảng | Một dòng là | Cột chính |
| --- | --- | --- |
| **`papers`** | Một **bài** (ID gốc) | `arxiv_id`, `title`, `authors`, `submission_date`, `revised_dates`, `venue` |
| **`references`** | Một **tham khảo có arXiv ID** | `arxiv_id` (bài đang xét), `ref_arxiv_id`, `ref_title`, `ref_authors`, `ref_submission_date`, `ref_s2_id` |

Khác biệt quan trọng: `references` **chỉ** giữ dòng có `ref_arxiv_id` (phục vụ Milestone 3). Tham khảo không có arXiv ID vẫn nằm trong `references.json` trên đĩa nhưng **không** vào bảng xuất. Mỗi bài gọi S2 **một lần** ở mức paper; references gắn với phiên bản đại diện khi xuất.

## Kiểm tra sau crawl (`validate_corpus.py`)

Validator (repo mã) kiểm tra trên thư mục `data/`:

- Đủ thư mục `v1…vN` theo `num_versions`, không thiếu phiên bản giữa chừng.
- Dưới `papers/` chỉ có metadata và `.tex`/`.bib` (không file lạ).
- `kept_bytes` ≤ `raw_uncompressed_bytes`; `sha256` khớp file trên đĩa.
- (Khi có) `manifest.sqlite` và parquet trong `data/stats/` nhất quán với trên.

## Số liệu báo cáo (chưa crawl)

| Chỉ số (§8 kế hoạch) | Giá trị M1 |
| --- | --- |
| Số bài thu thập thành công | *chưa crawl* |
| Tỷ lệ thành công (theo trạng thái) | *chưa crawl* |
| Kích thước TB trước/sau bỏ ảnh | *chưa crawl* |
| Số tham khảo TB / tỷ lệ siêu dữ liệu S2 | *chưa crawl* |
| Thời gian wall, RAM, đĩa (Colab CPU) | *chưa crawl* |

Repo mã: [GiaaPhuc/arxiv-pipeline](https://github.com/GiaaPhuc/arxiv-pipeline).
