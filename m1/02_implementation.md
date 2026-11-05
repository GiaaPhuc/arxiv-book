# Chương 2. Quá trình Triển khai & Công cụ Sử dụng

## 2.1. Quy trình Thu thập Đầu–Cuối (End-to-End Pipeline)

Do `export.arxiv.org` và `api.semanticscholar.org` là hai dịch vụ độc lập với cơ chế giới hạn tần suất rất khác nhau, hệ thống `arxiv-pipeline` được thiết kế gồm **hai luồng công việc tách biệt theo máy chủ đích**, giao tiếp qua hàng đợi bộ nhớ (`queue.Queue`) và đồng bộ trạng thái bền vững trên đĩa qua SQLite:

```text
  [Dải 25.000 ID (src/id_ranges.csv)]
                 │
                 ▼
  ┌──────────────────────────────────────────────────────────────────────┐
  │ Luồng chính — Máy chủ export.arxiv.org (1 kết nối, nghỉ >= 3,5 giây) │
  │  1. Khám phá Atom API (/api/query, lô 50 ID) -> tìm đủ v1..vN        │
  │  2. Truy vấn ngày chỉnh sửa trung gian (idv2..idvN) -> paper.json    │
  │  3. Tải từng gói /src/{id}vK -> lọc luồng chỉ giữ .tex & .bib        │
  │  4. Ghi nguyên tử (.vK.part -> vK/) & cập nhật manifest.sqlite       │
  └───────────────────────────────┬──────────────────────────────────────┘
                                  │ Đẩy bài báo đã xong nguồn vào hàng đợi
                                  ▼
  ┌──────────────────────────────────────────────────────────────────────┐
  │ Luồng nền — Máy chủ api.semanticscholar.org (nghỉ thích ứng >= 1,1s) │
  │  5. Gom lô tối đa 100 bài -> POST /graph/v1/paper/batch              │
  │  6. Nếu danh sách tham khảo bị cắt -> phân trang GET .../references  │
  │  7. Ghi vK/references.json + đánh dấu s2_references.raw.json.gz      │
  └───────────────────────────────┬──────────────────────────────────────┘
                                  │
                                  ▼
  [Kiểm chứng toàn vẹn (validate_corpus.py) & Xuất thống kê (export_data.py)]
```

### Bước 1 — Khám phá mục bài báo và lịch sử phiên bản (`discovery.py`)

1. **Tra cứu lô 50 ID gốc:** Bộ thu thập gửi tham số `id_list` gồm 50 định danh gốc mỗi lượt tới `https://export.arxiv.org/api/query`. Phản hồi Atom XML trả về định danh kèm hậu tố phiên bản mới nhất (ví dụ `http://arxiv.org/abs/2408.11047v3`), cho phép suy ra chính xác tổng số phiên bản `num_versions = 3` và ngày nộp bản đầu tiên (`v1`) từ trường `<published>`.
2. **Xác nhận đơn lẻ tách biệt `not_found` và lỗi mạng:** Bất kỳ định danh nào vắng mặt trong phản hồi của lô 50 đều được truy vấn xác nhận riêng một lần (`id_list=<id>`). Chỉ khi lần tra cứu riêng lẻ vẫn trả về rỗng, định danh đó mới được ghi nhận là `not_found`; nếu xảy ra ngoại lệ mạng tạm thời, lô đó được giữ nguyên trạng thái chưa khám phá để tự động thử lại ở phiên chạy tiếp theo mà không gán nhãn sai.
3. **Thu thập chính xác `revised_dates` cho các bản trung gian:** Một lần gọi API theo ID gốc chỉ cho biết `<published>` (ngày phát hành `v1`) và `<updated>` (ngày của phiên bản mới nhất `vN`). Do đó, với mọi bài báo có từ `2` phiên bản trở lên, hệ thống gom tiếp các định danh có phiên bản (`idv2 .. idvN`) thành các lô 50 để truy xuất chính xác ngày phát hành `<updated>` của từng bản chỉnh sửa trung gian.

### Bước 2 — Tải gói nguồn toàn văn và trích xuất `.tex` / `.bib` (`source.py`)

1. **Tải dạng dòng từ mirror chuyên dụng:** Từng phiên bản được tải qua `https://export.arxiv.org/src/{id}vK` bằng luồng đọc từng khối `64 KiB` xuống tệp tạm cục bộ (không nạp toàn bộ gói nén vào RAM). Hệ thống tuyệt đối không gửi yêu cầu tải tự động vào trang đọc chính `arxiv.org` để tránh kích hoạt hệ thống chặn robot tự động (HTTP `403`).
2. **Nhận diện định dạng theo thứ tự an toàn:** Bộ giải nén kiểm tra mã trạng thái HTTP trước tiên (`404` $\rightarrow$ `not_found`, không đọc thân trang lỗi HTML), sau đó kiểm tra `512 byte` đầu tiên (*magic bytes*) để phân loại chính xác gói tải về:
   - Chữ ký `%PDF` $\rightarrow$ bài nộp chỉ có PDF biên dịch sẵn, ghi nhận trạng thái `no_source` (`kept_bytes = 0`).
   - Chữ ký `1f 8b` (`gzip`) có nhãn `ustar` tại byte `257..262` của header giải nén (hoặc mở được thành viên tar hợp lệ cho biến thể tar cổ điển) $\rightarrow$ kho `tar.gz` nhiều tệp; nếu không phải tar $\rightarrow$ tệp văn bản TeX đơn nén `gzip` (`gz_single`).
   - Chữ ký `PK` $\rightarrow$ kho nén `zip` (trích xuất bình thường nếu chứa `.tex`/`.bib`; nếu là tài liệu `.docx` hoặc gói không chứa TeX sẽ chuyển về `no_source` / `ok_no_tex`).
   - Gói nén bị cắt cụt hoặc hỏng cấu trúc CRC/header được cô lập thành trạng thái `corrupt` kèm thông báo lỗi chi tiết mà không làm dừng tiến trình chung.
3. **Trích xuất an toàn và đo dung lượng đối chứng:** Khi duyệt qua luồng gói nén, hệ thống từ chối mọi đường dẫn chứa `..`, đường dẫn tuyệt đối, tên thiết bị dành riêng trên Windows (`CON`, `NUL`...), liên kết tượng trưng (*symlink/hardlink*) và áp trần dung lượng giải nén `2 GiB` (chống *zip-bomb*). Dung lượng gốc của toàn bộ thành viên trong gói (bao gồm cả hình ảnh) được cộng dồn vào `raw_uncompressed_bytes`, trong khi chỉ các tệp `.tex` và `.bib` mới được ghi ra đĩa kèm kích thước và mã băm `SHA-256` lưu vào `meta.json`.

### Bước 3 — Thu thập siêu dữ liệu tham khảo (`s2.py`)

1. **Tối ưu hóa bằng Batch API kết hợp phân trang dự phòng:** Thay vì thực hiện 25.000 lượt gọi `GET` đơn lẻ dễ chạm trần giới hạn tần suất, luồng nền gom tối đa **100 bài báo/lô** gửi tới `POST https://api.semanticscholar.org/graph/v1/paper/batch` (yêu cầu các trường `venue`, `referenceCount` và `references` kèm `paperId,externalIds,title,authors,publicationDate,year`). Ngay sau khi nhận phản hồi, hệ thống kiểm tra điều kiện cắt bớt `referenceCount > len(references)`: những bài báo có danh sách tham khảo dài bị API lô cắt ngắn sẽ tự động được truy vấn bổ sung qua endpoint phân trang `GET /graph/v1/paper/ARXIV:{id}/references?offset=&limit=1000` cho tới khi thu đủ toàn bộ danh sách.
2. **Xử lý định danh và chuẩn hóa trung thực:** Các định danh arXiv trích từ `externalIds.ArXiv` được tách hậu tố phiên bản nhưng bảo toàn nguyên văn sơ đồ đánh số cũ trước năm 2007 (ví dụ `hep-th/9901001`). Trường ngày của tài liệu tham khảo ưu tiên `publicationDate` (`YYYY-MM-DD`), nếu thiếu chỉ lưu đúng năm `year` (`YYYY`) chứ không tự gán ngày giả; trường `venue` loại bỏ giá trị mặc định `"arXiv"` / `"arXiv.org"` để chỉ phản ánh nơi công bố học thuật thực sự.

---

## 2.2. Tổng hợp Công cụ, Thư viện & Kiến trúc Module

Bảng dưới đây đối chiếu bộ công cụ kỹ thuật nhóm lựa chọn với các phương án trong "hộp công cụ" mà đề bài giới thiệu:

| Hạng mục | Công cụ / Thư viện sử dụng | Vai trò & Lý do lựa chọn so với phương án khác |
| :--- | :--- | :--- |
| **Khám phá bài báo** | **arXiv Atom API** (`/api/query`) + `xml.etree.ElementTree` | Truy xuất chính xác siêu dữ liệu và hậu tố phiên bản của đúng 25.000 ID được giao theo lô 50 ID. **Không dùng OAI-PMH** (`oaipmh.arxiv.org/oai`) hay **bộ dữ liệu Kaggle JSONL** cho luồng thu thập chính vì hai phương pháp đó hướng tới quét hàng loạt toàn kho (hơn 2 triệu bài) và không thuận tiện tra cứu ngày sửa đổi chi tiết của từng phiên bản theo danh sách ID rời rạc. **Không dùng thư viện `arxiv.py` (4.x)** (vốn đã loại bỏ hàm tải nguồn và tự quản lý client riêng) để chủ động dùng chung một phiên kết nối và một bộ giới hạn tốc độ duy nhất giữa API và `/src/`. |
| **Tải gói mã nguồn** | **`export.arxiv.org/src/`** + `requests` (`urllib3`) | Duy trì kết nối HTTP bền vững (`requests.Session`), định danh rõ ràng qua `User-Agent` và đọc dữ liệu dạng dòng (`stream=True`). Không dùng tiện ích CLI `arxiv-downloader` (khó kiểm soát trạng thái resume chi tiết theo phiên bản) hay Amazon S3 `s3://arxiv/src/` (cơ chế *requester-pays* tốn phí và thiết kế cho tải hàng TB theo bó tháng). |
| **Trích xuất tham khảo** | **Semantic Scholar Academic Graph API** (`requests` + `S2_API_KEY`) | Liên kết bài báo arXiv với đồ thị trích dẫn học thuật chuẩn hóa (độ chính xác cao mà không cần phân tích cú pháp LaTeX thô ngay ở Milestone 1); khóa API đảm bảo hạn mức ổn định $\ge 1$ yêu cầu/giây. |
| **Xử lý lưu trữ & Nén** | `tarfile`, `gzip`, `zipfile`, `hashlib`, `sqlite3` (Python `3.11`) | Giải nén luồng tuần tự, kiểm chứng toàn vẹn tệp bằng `SHA-256`, quản lý trạng thái giao dịch bằng SQLite ở chế độ WAL (`Write-Ahead Logging`). |
| **Đo đạc & Báo cáo** | `psutil`, `time.perf_counter`, `pyarrow`, `pandas`, `matplotlib`, `jupyter-book` | Lấy mẫu định kỳ RAM RSS toàn hệ thống và dung lượng đĩa, xuất bảng Parquet chuẩn hóa và biên dịch báo cáo trực tuyến có bảng biểu, đồ thị sinh tự động. |

Toàn bộ mã nguồn trong repository [`GiaaPhuc/arxiv-pipeline`](https://github.com/GiaaPhuc/arxiv-pipeline) được tổ chức tách bạch theo trách nhiệm từng module dưới thư mục `src/` và kiểm chứng tự động bằng **196 bài kiểm thử đơn vị (unit tests)** dùng fixture tổng hợp ngoại tuyến (`pytest` + `responses`), không phụ thuộc mạng thật khi chạy CI:

| Nhóm chức năng | Các module trong `src/` | Trách nhiệm kỹ thuật chính |
| :--- | :--- | :--- |
| **Định danh & Hợp đồng dữ liệu** | `crawler/models.py`, `crawler/ids.py`, `crawler/config.py` | Định nghĩa cấu trúc dữ liệu bất biến (`SCHEMA_VERSION = 1`), chuẩn hóa định danh mới/cũ và mở rộng dải `id_ranges.csv` thành danh sách 25.000 ID. |
| **Giao tiếp mạng & Thu thập** | `crawler/http.py`, `crawler/discovery.py`, `crawler/source.py`, `crawler/s2.py` | Quản lý phiên HTTP, bộ điều nhịp tốc độ (`RateLimiter`, `AdaptiveRateLimiter`), khám phá phiên bản Atom XML, tải luồng gói nguồn và truy vấn lô Semantic Scholar. |
| **Điều phối, Bền bỉ & Sao lưu** | `crawler/pipeline.py`, `crawler/manifest.py`, `crawler/checkpoint.py`, `run_crawl.py` | Điều phối hai luồng arXiv + S2, ghi nguyên tử hai pha, quản lý sổ trạng thái `manifest.sqlite` và đóng gói sao lưu một tệp `arxiv-data.tar.gz` trên Colab. |
| **Đo lường, Kiểm định & Xuất bảng** | `crawler/metrics.py`, `corpus.py`, `validate_corpus.py`, `crawler/export.py`, `export_data.py` | Đo thời gian theo chặng và lấy mẫu RAM/đĩa, kiểm tra 5 bất biến toàn vẹn kho ngữ liệu, kết xuất bảng Parquet và bộ tệp thống kê `stats/`. |

---

## 2.3. Chính sách Lịch sự Máy chủ, Chịu lỗi trên Colab & Kiểm chứng Dữ liệu

Quá trình vận hành thực tế ở quy mô hàng chục nghìn phiên bản trên Google Colab đặt ra nhiều thách thức về giới hạn tần suất mạng, ngắt kết nối phiên máy ảo và tốc độ I/O đám mây. Hệ thống giải quyết triệt để bằng bốn cơ chế kỹ thuật trọng tâm:

1. **Giới hạn tốc độ chính xác đến thời điểm đóng luồng tải (`http.py`):**
   Với `export.arxiv.org`, hệ thống duy trì **một kết nối duy nhất** và đặt khoảng nghỉ tối thiểu `3,5 giây` trên Colab (dư biên an toàn so với mức quy định $\ge 3{,}0\text{ s}$ trong hướng dẫn sử dụng arXiv API [[1, 2]](#tai-lieu-tham-khao)). Đặc biệt, bộ bọc luồng `_StreamResponse` chỉ kích hoạt đồng hồ đếm nghỉ **sau khi toàn bộ dữ liệu thân gói nguồn đã tải xong và đóng stream**, khắc phục triệt để lỗi đếm sớm ngay từ lúc nhận HTTP Header (nguyên nhân dễ dẫn tới lỗi HTTP `429` khi tải các gói nguồn lớn). Nếu gặp HTTP `429` thoáng qua (do dùng chung dải IP công cộng của Colab), hệ thống tôn trọng chờ đúng thời gian `Retry-After` tối đa 4 lần; nếu gặp HTTP `403`, hệ thống dừng khẩn cấp ngay lập tức để bảo vệ máy chủ. Với Semantic Scholar, bộ điều nhịp thích ứng duy trì khoảng cách $\ge 1{,}1\text{ s}$ và tự động nhân đôi thời gian chờ khi gặp HTTP `429`.

2. **Cam kết nguyên tử hai pha & Tự động Resume (`manifest.py`, `pipeline.py`):**
   Mọi tệp JSON đều được ghi qua tệp tạm rồi hoán đổi nguyên tử bằng `os.replace()`. Từng phiên bản được giải nén hoàn chỉnh vào thư mục ẩn `.vK.part/`, đổi tên sang `vK/`, và **chỉ ghi nhận trạng thái cuối cùng vào `manifest.sqlite` ở bước sau cùng**. Khi chạy lại trên cùng thư mục dữ liệu sau sự cố mất mạng hoặc hết thời gian máy ảo Colab, các tệp tạm dở dang được dọn sạch tự động, các phiên bản đã hoàn tất (`ok`, `ok_no_tex`, `no_source`, `not_found`, `corrupt`) được bỏ qua tức thì, và chỉ các mục `pending`/`failed` hoặc bài báo chưa có tệp đánh dấu `s2_references.raw.json.gz` mới được xếp hàng xử lý tiếp.

3. **Lưu trữ hai tầng chống nghẽn Google Drive FUSE (`checkpoint.py`):**
   Thực nghiệm vận hành của nhóm trên Google Colab cho thấy việc đồng bộ trực tiếp hàng chục nghìn tệp `.tex`/`.bib` nhỏ qua thư mục Google Drive gắn bằng FUSE chịu độ trễ siêu dữ liệu rất lớn (khôi phục khoảng 35.000 tệp rời kéo dài hơn 11 giờ và dễ phát sinh lỗi khóa SQLite). Nhóm khắc phục dứt điểm bằng kiến trúc lưu trữ hai tầng: toàn bộ hoạt động đọc/ghi diễn ra trên **ổ SSD cục bộ `/content/data`** của máy ảo Colab; định kỳ sau mỗi **300 ID mới** và ngay khi thoát tiến trình, hệ thống chụp ảnh nóng `manifest.sqlite` qua `sqlite3.Connection.backup()` rồi nén toàn bộ thư mục làm việc thành **một tệp tuần tự duy nhất `arxiv-data.tar.gz`** (`compresslevel=1`, ghi qua tệp `.part` kèm `os.fsync()`, kiểm tra chữ ký header chống tệp rỗng `0-byte` và đối chiếu sidecar metadata chống ghi đè lùi tiến độ), giúp rút ngắn thời gian khôi phục phiên làm việc xuống **dưới 60 giây**.

4. **Kiểm chứng hậu thu thập (`validate_corpus.py`) & Các hạn chế khách quan từ nguồn:**
   Trước khi xuất số liệu báo cáo, trình kiểm định độc lập quét toàn bộ kho ngữ liệu để xác nhận 5 bất biến nghiêm ngặt:
   - *(i)* Đủ thư mục phiên bản liên tục `v1..vN` khớp với `num_versions` trong `paper.json`;
   - *(ii)* Không tồn tại bất kỳ tệp lạ nào ngoài siêu dữ liệu chuẩn và các tệp `.tex`/`.bib`;
   - *(iii)* Khớp 100% dung lượng (`kept_bytes` $\le$ `raw_uncompressed_bytes`) và mã băm `SHA-256` thực tế trên đĩa với `meta.json`;
   - *(iv)* Cơ sở dữ liệu `manifest.sqlite` nhất quán với đĩa và không còn bản ghi `pending`;
   - *(v)* Hai bảng `papers.parquet` và `references.parquet` tuân thủ đúng lược đồ khóa không rỗng.

```{admonition} Ghi nhận trung thực ba giới hạn khách quan từ nguồn dữ liệu bên ngoài
:class: tip
Để chuẩn bị tốt nhất cho Milestone 2 & 3, nhóm ghi nhận rõ ba đặc thù của dữ liệu thượng nguồn:
1. **Phạm vi phiên bản trên Semantic Scholar (`s2_scope = "paper"`):** Semantic Scholar lập chỉ mục danh sách tham khảo ở cấp bài báo gốc (`ARXIV:<base_id>`) thay vì tách riêng từng bản sửa đổi `v1..vN`; do đó danh sách tham khảo từ S2 phản ánh phiên bản được S2 lập chỉ mục gần nhất.
2. **Bài báo chưa bóc tách được tham khảo trên S2 (`0` tham khảo):** Một tỷ lệ nhỏ bài báo mới hoặc có bố cục PDF đặc thù được S2 nhận diện (`found`) nhưng mảng `references` trả về rỗng; các trường hợp này sẽ được đối sánh trực tiếp với mã nguồn `.tex`/`.bib` ở Milestone 2.
3. **Tệp biên dịch sẵn `.bbl`:** Một số tác giả nộp tệp `.bbl` thay vì `.bib` gốc; tuân thủ chặt chẽ quy định chỉ trích xuất `.tex` và `.bib` ở Milestone 1, các tệp `.bbl` không đưa vào kho làm việc (các mục `\bibitem` nội tuyến nằm trực tiếp trong tệp `.tex` vẫn được giữ nguyên đầy đủ).
```
