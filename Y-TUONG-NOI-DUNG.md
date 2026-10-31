# Ý tưởng nội dung — arxiv-book (Milestone 1)

> Tài liệu **nội bộ** (không nằm trong `_toc.yml`, không build lên Pages). Tổng hợp từ việc đọc `arxiv-pipeline/` (`src/crawler/*`, `README.md`, `STATUS.md`, `data/stats/*`, `data/logs/*`, `docs/`) và đối chiếu với khung sách hiện có (`m1/01_overview.md`, `m1/03_data_statistics.ipynb`).
>
> Mục tiêu: chốt **sách kể câu chuyện gì**, **mỗi chương có gì**, **số liệu lấy ở đâu**, **còn thiếu gì** trước hạn nộp Book (**6/11/2026 23:59**, nội bộ đóng băng sáng 4/11).

---

## 1. Thông điệp chính của cuốn sách

> *"Chúng tôi thu thập **mọi phiên bản** của **25.000 bài arXiv** (tháng 6–8/2024) bằng một pipeline **lịch sự với máy chủ, chạy lại được (resume), kiểm chứng được** — chỉ giữ `.tex`/`.bib`, kèm danh sách tham khảo từ Semantic Scholar — và đây là con số, chi phí, hạn chế thật."*

Ba ý để người chấm nhớ:

1. **Đủ & đúng**: mọi `v1…vN`, không bỏ bài dù không có TeX (`no_source`).
2. **Lịch sự & bền**: ≥ 3 s/arXiv, một kết nối; S2 có batch + backoff; manifest SQLite để resume.
3. **Trung thực bằng số**: mọi hình/bảng sinh lúc build từ `stats/`, có định nghĩa chỉ số rõ ràng.

Đối chiếu tiêu chí chấm: *Báo cáo* (cả sách) · *Khám phá & tải đủ phiên bản* (ch. 2) · *Dữ liệu thu được* (ch. 3) · *Hiệu năng* (ch. 4).

---

## 2. Hiện trạng (đọc từ repo)

| Thành phần | Trạng thái | Nhận xét |
| --- | --- | --- |
| `m1/01_overview.md` | ✅ Có | Còn số "*chưa crawl*"; chưa nói rõ **batch S2** và **ba tỷ lệ tham khảo (a)(b)(c)** |
| `m1/03_data_statistics.ipynb` | 🟡 Số mẫu | Đọc `stats/sample_papers.csv` — **schema khác** với `papers_stats.csv` thật (xem §6) |
| `m1/02_implementation.md` | ⬜ Chưa | **Ưu tiên cao nhất** — viết được ngay, không cần chờ crawl |
| `m1/04_performance.ipynb` | ⬜ Chưa | Đã có `metrics.json` làm nguồn |
| `m1/05_issues_lessons.md` | ⬜ Chưa | STATUS §4 đã có sẵn nhiều sự kiện đáng đưa vào |
| `_toc.yml` | 🟡 Chỉ 2 mục | Cần mở rộng |
| Số pilot thật | ✅ 30 ID | `data/stats/summary.json` (xem §4.3) |
| Crawl 25.000 ID | ⬜ Phase 2 (T4.1) | Số cuối cùng thay sau khi xong |

---

## 3. Mục lục đề xuất

```yaml
format: jb-book
root: m1/01_overview
chapters:
  - file: m1/02_implementation
  - file: m1/03_data_statistics
  - file: m1/04_performance
  - file: m1/05_issues_lessons
```

> Tiêu đề sách trong `_config.yml` hiện là "Thu thập arXiv — Milestone 1". Vì M2 sẽ **thêm phần tiếp theo vào cùng cuốn sách**, cân nhắc đặt `m1/` như "Phần I" và để chỗ cho `m2/` (có thể dùng `parts:` trong `_toc.yml` khi tới M2).

---

## 4. Nội dung từng chương

### 4.1 `01_overview.md` — Tổng quan *(giữ + bổ sung)*

**Giữ:** mục tiêu, bảng nguồn, vì sao chờ ≥ 3 s, `no_source`, bảng `papers` vs `references`, đoạn validator.

**Bổ sung:**

- **Hộp "Tóm tắt trong 30 giây"** ở đầu trang: phạm vi (25.000 ID / 5 dải / một máy), nguồn, công cụ, link repo mã, ngày crawl, `schema_version`.
- **Sơ đồ end-to-end** (Mermaid, lấy từ README repo mã):

  ```mermaid
  flowchart LR
    R[id_ranges.csv] --> D[discovery: arXiv Atom API]
    D --> S[source: /src/idvN → .tex/.bib]
    D --> S2[S2: batch ≤100 + fallback]
    S --> F[data/papers/…]
    S2 --> F
    F --> V[validate_corpus]
    F --> X[export_data → stats/]
    X --> B[Jupyter Book]
  ```

- **Bảng 5 dải ID** — copy từ `src/id_ranges.csv` (không tự gõ lại):

  | Dải | Tháng | ID đầu | ID cuối |
  | --- | --- | --- | --- |
  | 1 | 2024-08 | 01045 | 06044 |
  | 2 | 2024-08 | 06045 | 11044 |
  | 3 | 2024-08 | 11045 | 16044 |
  | 4 | 2024-07 | 07839 | 12838 |
  | 5 | 2024-06 | 07938 | 12937 |

- **Quyết định D8**: gom 25.000 ID, một máy, resume; subset theo dải từng người chỉ tách ở cuối M3 (đây là điểm khác biệt so với "5 Colab × 5.000 ID").
- Sửa dòng "Số liệu báo cáo (chưa crawl)" → bảng số thật (hoặc pilot, ghi rõ nhãn).

---

### 4.2 `02_implementation.md` — Cách thu thập *(chương mới, quan trọng nhất)*

Mỗi mục ứng với một module trong `src/crawler/`, mỗi mục có: **vấn đề → cách giải → thư viện → trích đoạn ≤ 15 dòng + link GitHub**.

| # | Mục | Module | Ý chính cần viết |
| --- | --- | --- | --- |
| 1 | ID & dải | `ids.py` | CSV 4 cột `start_month,start_id,end_month,end_id` (gồm cả hai đầu); ID mới `YYMM.NNNNN` vs cũ `hep-th/9901001`; đệm 5 số (`2408.1045` = `2408.01045`); `not_found` ≠ `failed` |
| 2 | Khám phá phiên bản | `discovery.py` | `id_list` lô **50** ID gốc; `published` = ngày v1; `updated` = ngày bản mới nhất; ngày bản trung gian lấy bằng `id v2,v3,…`; ID vắng → hỏi lại riêng 1 lần mới ghi `not_found`. Tự gọi Atom API bằng `requests` (không dùng `arxiv.py`) để API và `/src/` **dùng chung một limiter** |
| 3 | Tải & trích nguồn | `source.py` | Xem mã HTTP **trước**, rồi magic bytes (`1f8b`+`ustar` = tar.gz, `%PDF`, `PK` = zip, gzip đơn); trích **an toàn** (chặn path traversal, tên Windows reserved); chỉ `.tex`/`.bib`, giữ cây thư mục, không sửa byte; ghi `sha256`, `kept_bytes`, `raw_uncompressed_bytes`; lệnh `\includegraphics` giữ nguyên |
| 4 | Semantic Scholar | `s2.py` | Một lần/bài trên ID gốc; `POST /graph/v1/paper/batch` (≤ 100 ID/lô, venue + refs lồng nhau); nếu `referenceCount` > số refs trả về → fallback `GET …/references?limit=1000`; ngày = `publicationDate`, không có thì `YYYY`, **không bịa**; `venue` = `journal_ref`, rỗng thì S2 (bỏ `arXiv.org`) |
| 5 | HTTP lịch sự | `http.py` | Một limiter/host: arXiv ≥ 3 s (đếm từ lúc **đóng stream**, không phải lúc có header — bug đã sửa 28/10); S2 ≥ 1,1 s, giãn thêm sau 429, giảm dần sau 50 request thành công; retry chỉ cho 5xx; 403/429 trả caller xử lý |
| 6 | Pipeline & resume | `pipeline.py`, `manifest.py` | Hai worker (arXiv ở main thread, S2 một thread), gặp nhau qua đĩa/manifest; ghi nguyên tử `.vK.part/` → `os.replace`, manifest ghi **cuối cùng**; `s2_references.raw.json.gz` là "dấu S2 xong"; resume: bỏ cặp ở trạng thái cuối, thử lại `failed`, xếp lại S2 dở; arXiv 403 → dừng, 429 → chờ `Retry-After` ≤ 4 lần rồi `StopCrawl` (exit 3) |
| 7 | Đo hiệu năng | `metrics.py` | Timer theo giai đoạn (discovery/download/extract/s2), RSS đỉnh/TB gồm tiến trình con (`psutil`), đĩa đỉnh; **cộng dồn qua các lần resume** |
| 8 | Sao lưu Colab | `checkpoint.py`, `colab_run.ipynb` | Crawl trên đĩa cục bộ `/content/data` (SQLite không hợp Drive FUSE); mirror ra Drive mỗi 1000 ID mới; snapshot SQLite an toàn khi đang chạy |
| 9 | Xuất & kiểm tra | `export.py`, `corpus.py`, `validate_corpus.py` | `export_tables` → `papers.parquet`, `references.parquet` (chỉ ref **có arXiv ID**); `export_stats` → `summary.json` + CSV; validator kiểm tra gì (đã có ở overview) |
| 10 | Công cụ | — | Bảng: Python 3.11, `requests`, `psutil`, `pandas`/`pyarrow`, stdlib `tarfile`/`gzip`/`sqlite3`/`threading`, `pytest` + `responses` (mock, **189 test**), `ruff`, `pre-commit`, GitHub Actions. Ghi một câu: OAI-PMH/Kaggle chỉ là "hộp công cụ của đề", không dùng để thu hoạch |

**Điểm nhấn trình bày:**

- Một **bảng "Trạng thái của một cặp (bài, phiên bản)"**: `ok` · `ok_no_tex` · `no_source` · `not_found` · `failed` · `corrupt` — dùng lại nhãn này ở ch. 3.
- Một **bảng spike `/src/`** (từ STATUS §1): URL → HTTP → loại gói → cách xử lý (tar.gz, PDF `2408.01045v1`, 404 `2408.00000v1`). Đây là bằng chứng thực nghiệm rất thuyết phục.
- Một hình **cây thư mục `data/`** (code block từ README).
- **Tránh** copy code dài; không nhắc phân vai A–E trong sách.

---

### 4.3 `03_data_statistics.ipynb` — Thống kê dữ liệu

**Nguồn** (copy `arxiv-pipeline/data/stats/` → `arxiv-book/stats/`): `summary.json`, `papers_stats.csv`, `versions_stats.csv`; tuỳ chọn `papers.parquet`, `references.parquet` (file lớn → ưu tiên CSV/JSON).

**Số pilot 30 ID hiện có** (chỉ để biết hình dạng dữ liệu, **không** đưa vào bản nộp như kết quả cuối):

| Chỉ số | Pilot 30 ID |
| --- | --- |
| Bài thành công / tỷ lệ | 30 / 30 (100 %) |
| Cặp (bài, phiên bản) | 57 → `ok` 51, `no_source` 6, `failed` 0 |
| Phiên bản TB / bài | 1,9 (phân phối: 1→13, 2→10, 3→5, 4→1, 5→1) |
| Bài có TeX | 27 / 30 |
| Byte TB / phiên bản: gói tải về · giải nén kèm ảnh · giữ `.tex`+`.bib` | ≈ 5,75 MB · 7,01 MB · **139 KB** (giữ ≈ **2,0 %**) |
| (a) % bài có S2 | 100 % |
| (b) % ref đủ title+authors+date (TB theo bài) | 78,0 % |
| (c) % ref có arXiv ID | 50,3 % (508 / 1.009) |
| Refs TB / bài | 33,6 |

**Bảng & hình sinh khi build** (mỗi hình một đoạn markdown giải thích *đọc hình thế nào* + *rút ra gì*):

| # | Nội dung | Gợi ý hình |
| --- | --- | --- |
| 1 | Thẻ số liệu tổng (số bài thành công, tỷ lệ) kèm `summary["definitions"]` trích nguyên văn | Bảng + `display(Markdown)` |
| 2 | Phân bố trạng thái (theo bài **và** theo cặp) | Stacked bar |
| 3 | Kích thước trước/sau bỏ ảnh | Bar log-scale 3 cột (`raw_archive`, `raw_uncompressed`, `kept`); nêu rõ *mean vs median* và đơn vị byte |
| 4 | Phân phối số phiên bản / bài | Bar `versions_per_paper` |
| 5 | Phân phối số refs / bài | Histogram (log-x nếu lệch) |
| 6 | Ba tỷ lệ siêu dữ liệu tham khảo (a)(b)(c) | 3 số cạnh nhau, **nhãn rõ** từng loại |
| 7 | Bài không TeX (`no_source`/`ok_no_tex`) | Bảng ví dụ + % |
| 8 | Nguyên nhân lỗi (`top_errors`) | Bảng top-N (hoặc "không có" nếu rỗng) |
| 9 | *(Tuỳ chọn)* so sánh theo 5 dải | Bảng lọc `papers_stats.csv` theo ID |
| 10 | *(Tuỳ chọn)* mẫu 5 dòng `papers` / `references` | `head()` từ parquet |

**Quy tắc:** notebook phải chạy được với dữ liệu thật mà **không sửa code** (đọc `summary.json`, không hard-code số); xoá output cũ trước khi commit nếu CI tự execute.

---

### 4.4 `04_performance.ipynb` — Hiệu năng *(chương mới)*

**Nguồn:** `stats/performance.json` (= `data/logs/metrics.json`).

| Hạng mục đề | Trình bày |
| --- | --- |
| Wall time end-to-end | Tổng giờ crawl 25k; ghi rõ số lần resume (`runs`) |
| Thời gian theo giai đoạn | Stacked bar từ `stage_seconds` (discovery/download/extract/s2) — *download chiếm gần như toàn bộ* do luật 3 s |
| Thời gian TB / bài | `active_seconds` / số bài thành công |
| RAM đỉnh / TB | `ram_peak_bytes`, `ram_mean_bytes` (pilot: ~39–45 MB) |
| Đĩa | `disk_peak_bytes`/`disk_final_bytes` + ngoại suy cho 25k |
| S2 | `batches`, `http_429`, `retry_wait_seconds`, `papers_ok`, `papers_not_indexed` |
| Môi trường | **Colab CPU** (không GPU), RAM/đĩa instance, ngày chạy, commit hash repo mã |

**Phần "ước lượng vs thực tế"** (rất đáng làm): STATUS ước **~40 h** chờ arXiv (47.500 request × 3 s, V̄ = 1,9) → kỳ vọng 2–3 ngày; so với wall thật sau Phase 2. Có thể kèm đường tiến độ (ID đã xong theo thời gian, từ manifest).

**So sánh định tính (tiêu chí "hiệu năng so với nhóm khác"):** batch S2 (100 ID/lô thay vì 1 request/bài), một kết nối arXiv đúng luật, resume không tải lại, chỉ lưu `.tex`/`.bib` (~2 % dung lượng).

---

### 4.5 `05_issues_lessons.md` — Vấn đề & bài học *(chương mới)*

Nhiều nội dung đã sẵn trong `STATUS.md` §4 — chọn các mục **đưa được vào báo cáo**:

| Chủ đề | Nội dung gợi ý |
| --- | --- |
| **Giới hạn tốc độ arXiv** | Lỗi đếm 3 s từ lúc có header khiến request kế đến sớm → 429 trên Colab; sửa bằng đếm đến khi đóng stream; `Retry-After` ≤ 4 lần; 429 ở API discovery trước đây dừng cả crawl |
| **Semantic Scholar** | 429 dày (pilot: 3× / 180 s; lượt 50 ID: 11× / 660 s) → batch + limiter thích ứng; ref không có arXiv ID (~50 %); indexing trễ |
| **Gói nguồn bất thường** | PDF-only trong dải (`2408.01045v1`) → `no_source`; gói tar.gz > 10 MB (`2408.11045`); ID không tồn tại |
| **Vận hành** | Colab ngắt phiên → backup Drive định kỳ; checkpoint từng tính sai vị trí sau resume (mirror cả `papers/` > 30 phút) → sửa; Windows antivirus khoá file → `failed` rồi retry; SQLite không chạy tốt trên Drive FUSE |
| **Kiểm chứng** | ≥ 20 phiên bản đối chiếu tay với trang arXiv (T4.3): bảng 3–5 dòng ví dụ (ID, vN, ngày, khớp?) |
| **Hạn chế còn lại** | Chưa pin version thư viện; `--s2-only` chưa code; tham khảo S2 gắn mức paper (không riêng từng phiên bản) |
| **Chuẩn bị M2/M3** | Corpus giữ bố cục `papers/<id>/vN/tex/`; `references.json` đầy đủ vs bảng xuất chỉ ref có arXiv ID |

Giọng văn: trung thực, có số — đây là chỗ thể hiện academic integrity.

---

## 5. Quy ước trình bày

- **Tiếng Việt**, thuật ngữ giữ nguyên tiếng Anh khi chuẩn (`resume`, `rate limit`, `batch`).
- **Mọi hình/bảng số liệu sinh khi build**, không dán ảnh chụp màn hình. Sơ đồ Mermaid/code block được phép (không chứa số liệu).
- **Mọi số** trong `01_overview` và `02_implementation` phải **khớp `summary.json`** của lần build cuối; ghi ngày crawl + số lần resume.
- Nêu rõ đơn vị (byte), phép tính (mean/median), và **định nghĩa chỉ số** (lấy từ `summary["definitions"]`).
- Trích dẫn tài liệu ngoài: arXiv API user manual, S2 Graph API docs.
- Không đưa vào sách: phân vai A–E, lịch họp, `Leader/*`, `Plans/*` nội bộ.

---

## 6. Việc cần làm / lưu ý kỹ thuật

1. **Schema không khớp:** notebook 03 đang đọc `stats/sample_papers.csv` (cột `has_tex`, `n_refs`, `kept_bytes`, …) — phải đổi sang `papers_stats.csv` / `versions_stats.csv` / `summary.json` (cột thật: `n_versions_expected`, `all_versions_recorded`, `s2_state`, `n_refs_arxiv`, `refs_complete_ratio`, `raw_archive_bytes`, …).
2. **Số liệu pilot chưa đồng bộ:** `data/papers/` hiện có **50** thư mục (`2408-11045…11094`) và `data/logs/metrics.json` (2 lần chạy, ~596 s, 11 lô S2, 11×429) **mới hơn** `data/stats/performance.json` (pilot 30 ID, 16 s). → Chạy lại `python src/export_data.py` trước khi copy sang sách, tránh lẫn hai lần đo.
3. **Dự án đang ở Phase 2:** crawl 25.000 ID (T4.1) chưa xong → viết ch. 2 và 5 trước, ch. 3–4 dùng số pilot làm khung, thay số thật khi xong.
4. **`requirements.txt` của sách:** thêm `matplotlib`, `pandas` (và `pyarrow` nếu đọc parquet), ghim phiên bản cho CI.
5. **Build sạch:** `jupyter-book build .` không cảnh báo; `execute_notebooks: auto` + `timeout: 120` đủ cho CSV/JSON, cân nhắc tăng nếu đọc parquet lớn.
6. File này đã được đưa vào `exclude_patterns` của `_config.yml` để không bị build.

---

## 7. Ý tưởng điểm cộng (không bắt buộc)

- **Timeline crawl** (số ID xong theo giờ) từ `manifest.sqlite` / `crawl.log`.
- **Plotly** histogram refs tương tác (nếu chạy ổn trên Pages).
- **Bảng "Công cụ đề gợi ý vs công cụ nhóm chọn"** (API thuần + `requests` tự viết vs `arxiv.py`/OAI-PMH/Kaggle): lý do chọn.
- **Ví dụ end-to-end một bài** (vd. `2408.11046`: 1 phiên bản, 39 refs, 33 có arXiv ID): từ `paper.json` → `meta.json` → `references.json` → một dòng trong `papers`/`references`.
- **Hộp "Tái lập"**: 4 lệnh `run_crawl` → `validate_corpus` → `export_data` → `jupyter-book build`.

---

## 8. Checklist trước khi nộp

- [ ] `_toc.yml` có đủ 5 file M1; build CI xanh, không broken link.
- [ ] Notebook 03 & 04 chạy trên **số thật**, không còn chữ "số mẫu"/"chưa crawl".
- [ ] `stats/` cùng commit với lần build cuối; không còn `sample_*.csv`.
- [ ] Ba tỷ lệ tham khảo (a)(b)(c) có nhãn + định nghĩa rõ.
- [ ] Ch. 2 mô tả đúng: batch S2, một máy 25k (D8), limiter, resume.
- [ ] Ch. 4 ghi Colab **CPU**, ngày chạy, số lần resume.
- [ ] Ch. 5 có bảng đối chiếu ≥ 20 phiên bản.
- [ ] Không còn ảnh tĩnh chụp màn hình.
- [ ] README repo sách: cách build local.
- [ ] Dán link Pages công khai + link repo mã lên Moodle.
