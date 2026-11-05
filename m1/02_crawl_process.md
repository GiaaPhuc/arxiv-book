# M1 — Nhóm đã thu thập dữ liệu như thế nào?

## 1. Câu hỏi của dự án

Nhóm được giao xây dựng một **corpus** (kho dữ liệu làm việc) từ arXiv. Mỗi
ID arXiv có thể có nhiều lần sửa đổi, ví dụ `v1`, `v2`, `v3`. Vì vậy, mục
tiêu không chỉ là tìm bài báo, mà là:

1. tìm đúng các bài trong dải ID được giao;
2. tìm **tất cả phiên bản** của mỗi bài;
3. tải mã nguồn LaTeX nếu phiên bản có mã nguồn;
4. lấy metadata của bài và các tài liệu được trích dẫn;
5. lưu dữ liệu theo cách có thể tiếp tục sau khi máy bị ngắt.

Milestone 1 không yêu cầu nộp corpus lên Moodle. Corpus được giữ làm đầu vào
cho Milestone 2 (phân tích và chuẩn hóa LaTeX) và Milestone 3 (ghép tài liệu
tham khảo).

## 2. Phạm vi dữ liệu

Nhóm có 5 dải, tổng cộng **25.000 ID**. File `src/id_ranges.csv` của
[repo mã](https://github.com/GiaaPhuc/arxiv-pipeline) chứa các dải này. Mỗi
ID được tính cả hai đầu của dải.

Trong lần chạy hiện tại, lệnh kiểm tra kế hoạch cho kết quả:

```text
25000 ids
first 2408.11045
last 2406.12937
```

Điều này chỉ chứng minh danh sách đầu vào được mở rộng đúng; nó **không** có
nghĩa là 25.000 bài đã được crawl.

## 3. Quy trình bằng ngôn ngữ đời thường

Có thể hình dung crawler như một dây chuyền:

```{mermaid}
flowchart LR
    A["Danh sách ID"] --> B["Tìm metadata và số phiên bản"]
    B --> C["Tải từng phiên bản"]
    C --> D["Chỉ giữ .tex và .bib"]
    B --> E["Lấy references từ Semantic Scholar"]
    D --> F["Lưu JSON + file LaTeX"]
    E --> F
    F --> G["Manifest SQLite và log"]
    G --> H["Kiểm tra corpus"]
    H --> I["Xuất bảng và thống kê"]
```

### Bước 1 — Tìm bài và các phiên bản

Crawler gửi các ID gốc theo lô đến API Atom của `export.arxiv.org`. Response
cho biết metadata của bài và phiên bản mới nhất. Từ đó chương trình xác định
các phiên bản cần tải, từ `v1` đến `vN`.

Nhóm **không** thu hoạch toàn bộ arXiv. OAI-PMH và bộ dữ liệu Kaggle được
đề bài giới thiệu như các phương án tham khảo, nhưng bài này chỉ xử lý các
dải ID được giảng viên giao.

### Bước 2 — Tải mã nguồn từng phiên bản

Mỗi phiên bản được tải riêng qua endpoint `/src/` của `export.arxiv.org`.
Crawler kiểm tra mã HTTP trước khi đọc nội dung:

- `404`: ghi `not_found`;
- `403` hoặc `429`: dừng để bảo vệ máy chủ và báo nhóm;
- archive có LaTeX: trích `.tex` và `.bib`;
- PDF hoặc archive không có LaTeX: ghi `no_source`, nhưng vẫn giữ metadata;
- archive hỏng: ghi `corrupt`.

Việc “bỏ hình” được thực hiện bằng **trích chọn file**, không sửa nội dung
LaTeX. Các lệnh như `\includegraphics` vẫn được giữ trong file `.tex`; chỉ
file ảnh nhị phân không được đưa vào corpus.

### Bước 3 — Lấy tài liệu tham khảo

Với mỗi bài, nhóm gọi Semantic Scholar theo ID dạng
`arXiv:{arxiv_id}`. Danh sách references được phân trang nếu cần. Dữ liệu
thô vẫn được giữ cục bộ, kể cả references không có arXiv ID.

Khi xuất bảng dùng cho các milestone sau, chỉ references có `ref_arxiv_id`
mới được đưa vào bảng `references`. Điều này giúp Milestone 3 có một tập ứng
viên arXiv rõ ràng để ghép.

### Bước 4 — Lưu và tiếp tục sau khi bị ngắt

Mỗi bài có thư mục riêng. Một phiên bản có metadata, references và thư mục
LaTeX:

```text
data/
├── manifest.sqlite
├── logs/
│   ├── crawl.log
│   └── metrics.json
└── papers/<arxiv-id>/
    ├── paper.json
    ├── s2_references.raw.json.gz
    └── v<N>/
        ├── meta.json
        ├── references.json
        └── tex/
            ├── main.tex
            └── references.bib
```

`manifest.sqlite` là sổ trạng thái. Khi chạy lại cùng thư mục dữ liệu:

- cặp đã hoàn tất được bỏ qua;
- cặp `failed` được xếp lại để thử;
- công việc Semantic Scholar chưa hoàn tất được xếp lại;
- file đang ghi dở không được coi là file hoàn chỉnh.

Nhờ vậy, việc mất kết nối hoặc Colab hết thời gian không buộc nhóm tải lại
toàn bộ corpus.

## 4. Vì sao phải giới hạn tốc độ?

Đây là crawler có trách nhiệm, không phải chương trình gửi request càng nhanh
càng tốt:

- arXiv: tối thiểu 3 giây giữa các request, một kết nối;
- Semantic Scholar: tối thiểu 1 request mỗi giây;
- `Retry-After` được tôn trọng khi máy chủ trả `429`;
- không mở nhiều crawler trên cùng thư mục dữ liệu;
- không chạy song song nhiều crawler để “kịp deadline”.

Giới hạn này làm thời gian chạy dài, nhưng giúp giảm nguy cơ bị chặn và làm
cho kết quả có thể giải thích được trong báo cáo.

## 5. Các thành phần phần mềm

| Thành phần | Vai trò |
|---|---|
| `run_crawl.py` | Nhận tham số dòng lệnh và khởi động pipeline |
| `ids.py` | Chuẩn hóa ID và mở rộng dải ID |
| `discovery.py` | Gọi arXiv API để tìm metadata và phiên bản |
| `source.py` | Tải archive và trích `.tex`/`.bib` an toàn |
| `s2.py` | Lấy references từ Semantic Scholar |
| `http.py` | Session, User-Agent, limiter và retry |
| `manifest.py` | SQLite state và ghi nguyên tử |
| `pipeline.py` | Điều phối crawl, resume và hai luồng công việc |
| `metrics.py` | Đo wall time, RAM và disk |
| `validate_corpus.py` | Kiểm tra các bất biến của corpus |
| `export_data.py` | Xuất bảng, CSV/Parquet và thống kê |

Mã nguồn và test nằm trong [repo crawler](https://github.com/GiaaPhuc/arxiv-pipeline).
Các test HTTP đều dùng response giả; test tự động không gọi mạng thật.

## 6. Hai bảng đầu ra

### Bảng `papers`

Một dòng đại diện cho một bài:

```text
arxiv_id, title, authors, submission_date, revised_dates, venue
```

### Bảng `references`

Một dòng đại diện cho một reference có arXiv ID:

```text
arxiv_id, ref_arxiv_id, ref_title, ref_authors,
ref_submission_date, ref_s2_id
```

`arxiv_id` trong bảng thứ hai là bài đang trích dẫn. `ref_arxiv_id` là bài
được trích dẫn. Các references không có arXiv ID không bị xóa khỏi dữ liệu
thô; chúng chỉ không xuất hiện trong bảng matching.

## 7. Kiểm tra chất lượng

Sau crawl, nhóm chạy:

```bash
python src/validate_corpus.py --data-dir data
python src/export_data.py --data-dir data
```

Validator kiểm tra:

- đủ các phiên bản từ `v1` đến `vN`;
- không có file lạ ngoài metadata và `.tex`/`.bib`;
- kích thước lưu giữ không vượt kích thước raw đã giải nén;
- SHA-256 trên đĩa khớp metadata;
- manifest không còn cặp `pending`;
- các bảng export có cột bắt buộc và không giữ reference thiếu arXiv ID.

## 8. Các chỉ số cần báo cáo

Các bảng và hình trong chương này phải được tạo từ file số liệu khi build
sách. Notebook thống kê đọc các file nhỏ trong thư mục `stats/`, không đọc
toàn bộ corpus thô trực tiếp.

Các chỉ số bắt buộc:

- số bài thành công và tỷ lệ thành công;
- số phiên bản có source và số phiên bản `no_source`;
- kích thước trung bình raw trước khi bỏ file ảnh;
- kích thước trung bình sau khi chỉ giữ `.tex` và `.bib`;
- số references trung bình mỗi bài;
- tỷ lệ references lấy được metadata;
- tổng thời gian crawl và thời gian khám phá entry;
- thời gian trung bình xử lý mỗi bài;
- RAM tối đa và RAM trung bình;
- dung lượng disk tối đa;
- dung lượng output cuối cùng.

Runtime được đo theo wall time của toàn bộ hệ thống. Benchmark cuối cùng phải
chạy trên Google Colab **CPU-only**. Không có giới hạn trên về thời gian
chạy, nhưng dung lượng tối đa bị giới hạn bởi disk của Colab.

```{code-cell} python
from pathlib import Path
import json
import pandas as pd

BOOK_ROOT = Path.cwd()
if not (BOOK_ROOT / "stats").is_dir():
    BOOK_ROOT = next(
        p for p in [BOOK_ROOT, *BOOK_ROOT.parents]
        if (p / "stats").is_dir()
    )

stats_dir = BOOK_ROOT / "stats"
summary_path = stats_dir / "summary.json"
performance_path = stats_dir / "performance.json"

files = sorted(stats_dir.glob("*"))
pd.DataFrame(
    {
        "nguồn": [str(path.relative_to(BOOK_ROOT)) for path in files],
        "trạng thái": ["có trong repo sách"] * len(files),
    }
)
```

Nếu chưa có `data/logs/metrics.json`, điều đó chỉ có nghĩa là corpus/metrics
chưa được sao chép vào repo sách. Không được thay bằng số đo phỏng đoán.

```{code-cell} python
if summary_path.is_file():
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
else:
    summary = {}

if performance_path.is_file():
    performance = json.loads(performance_path.read_text(encoding="utf-8"))
else:
    performance = {}

stage_seconds = performance.get("stage_seconds", {})
resources = performance.get("resources", {})
raw_sizes = summary.get("mean_bytes_per_extracted_version", {})

def value_or_pending(value):
    return value if value is not None else "chưa crawl/export số liệu thật"

rows = [
    {"chỉ số": "Số bài thành công", "giá trị": value_or_pending(summary.get("papers_success"))},
    {"chỉ số": "Tỷ lệ bài thành công", "giá trị": value_or_pending(summary.get("success_rate_papers"))},
    {
        "chỉ số": "Kích thước raw TB / phiên bản (bytes)",
        "giá trị": value_or_pending(raw_sizes.get("raw_uncompressed_with_images")),
    },
    {
        "chỉ số": "Kích thước giữ lại TB / phiên bản (bytes)",
        "giá trị": value_or_pending(raw_sizes.get("kept_tex_bib")),
    },
    {"chỉ số": "Số references TB / bài", "giá trị": value_or_pending(summary.get("mean_refs_per_paper"))},
    {
        "chỉ số": "Tỷ lệ metadata references đầy đủ",
        "giá trị": value_or_pending(summary.get("mean_refs_complete_ratio")),
    },
    {"chỉ số": "Tổng thời gian discovery (s)", "giá trị": value_or_pending(stage_seconds.get("discovery"))},
    {
        "chỉ số": "Tổng thời gian crawl chủ động (s)",
        "giá trị": value_or_pending(performance.get("active_seconds")),
    },
    {
        "chỉ số": "RAM tối đa (bytes)",
        "giá trị": value_or_pending(resources.get("ram_peak_bytes")),
    },
    {
        "chỉ số": "RAM trung bình (bytes)",
        "giá trị": value_or_pending(resources.get("ram_mean_bytes")),
    },
    {
        "chỉ số": "Disk tối đa (bytes)",
        "giá trị": value_or_pending(resources.get("disk_peak_bytes")),
    },
    {
        "chỉ số": "Dung lượng output cuối (bytes)",
        "giá trị": value_or_pending(resources.get("disk_final_bytes")),
    },
]

pd.DataFrame(rows)
```

## 9. Trạng thái kiểm chứng của mã hiện tại

Tại thời điểm viết chương này:

- bộ test của repo crawler: **186 tests passed**;
- dry-run mở rộng đúng **25.000 ID**;
- corpus thật và `metrics.json` chưa được đưa vào repo sách;
- vì vậy các ô thống kê phía trên sẽ hiển thị trạng thái chờ số liệu cho
  đến khi nhóm chạy crawl và `export_data.py`.

Đây là cách trình bày trung thực: báo cáo giải thích được phương pháp ngay
từ bây giờ, còn kết quả định lượng chỉ được điền sau khi có bằng chứng từ
manifest, log và metrics.

## 10. README và khả năng tái lập

README của repo mã là tài liệu vận hành riêng, không thay thế báo cáo. Người
muốn chạy lại cần biết:

1. phiên bản Python;
2. các package cần cài;
3. cách đặt `CRAWLER_CONTACT` và `S2_API_KEY` mà không commit secret;
4. cách chạy `--dry-run`, pilot và full crawl;
5. cách resume sau khi bị ngắt;
6. cách validate và export.

Báo cáo này giải thích **vì sao** nhóm thiết kế như vậy và **kết quả có ý
nghĩa gì**; README giải thích **câu lệnh cụ thể để chạy lại**.
