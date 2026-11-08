# Chương 2. Quá trình Triển khai & Công cụ Sử dụng

## 2.1. Quy trình Thu thập Đầu–Cuối (End-to-End Pipeline)

Khác với các bộ thu thập tuần tự đơn luồng truyền thống (vốn mất hơn 15 giờ và dễ bị nghẽn I/O đĩa), hệ thống `arxiv-pipeline` được thiết kế theo kiến trúc **Producer–Consumer Đa luồng (v3.4–v3.8)**. Kiến trúc này phân tách triệt để giữa tầng **Mạng arXiv** (bị ràng buộc bởi chuẩn lịch sự và giới hạn 1 kết nối duy nhất), tầng **Giải nén CPU/Đĩa** (chạy song song trên nhiều nhân) và tầng **Mạng Semantic Scholar**:

<div class="pipeline-flow" role="region" aria-label="Sơ đồ Quy trình Thu thập Đầu–Cuối">
  <div class="pf-endpoint-node pf-input">
    <span class="pf-icon">&#128196;</span>
    <span>Dải 25.000 ID (<code>src/id_ranges.csv</code>) &rarr; Khóa OS Mutex (<code>_acquire_workspace_lock</code>)</span>
  </div>
  <div class="pf-connector" aria-hidden="true">
    <svg width="20" height="26" viewBox="0 0 20 26" fill="none">
      <line x1="10" y1="0" x2="10" y2="19" stroke="currentColor" stroke-width="1.8"/>
      <path d="M5 16L10 23L15 16" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
  </div>
  <div class="pf-stage-card pf-stage-arxiv">
    <div class="pf-stage-header">
      <div class="pf-stage-title">
        <span class="pf-stage-dot"></span>
        <span>1. MainThread — arXiv Network Producer (<code>export.arxiv.org</code>)</span>
      </div>
      <span class="pf-rate-badge">1 kết nối · Start-to-Start &ge; 3,0s (3,15s + jitter)</span>
    </div>
    <div class="pf-steps-grid">
      <div class="pf-step-item">
        <span class="pf-step-num">1</span>
        <div class="pf-step-body">
          <strong>Khám phá Atom API lô 250 ID (O2 + T3)</strong>
          <span><code>/api/query</code> (250 ID) &rarr; tận dụng <code>&lt;updated&gt;</code> cho bài 2 bản &rarr; sub-batch 50 ID</span>
        </div>
      </div>
      <div class="pf-step-item">
        <span class="pf-step-num">2</span>
        <div class="pf-step-body">
          <strong>Tải dạng dòng &amp; Đệm RAM &le; 96 MiB (O3 + T5)</strong>
          <span>Khung 256/512 KiB vào <code>bytearray</code>; ngắt sớm ở 512 bytes cho <code>%PDF</code> / <code>ZIP</code></span>
        </div>
      </div>
      <div class="pf-step-item">
        <span class="pf-step-num">3</span>
        <div class="pf-step-body">
          <strong>Nối tiếp HTTP 206 Range lịch sự (T2 + v3.5)</strong>
          <span>Nghỉ <code>3,0s &rarr; 4,5s &rarr; 6,0s</code> &rarr; tối đa 4 lượt thử kèm đổi TCP socket sạch</span>
        </div>
      </div>
      <div class="pf-step-item">
        <span class="pf-step-num">4</span>
        <div class="pf-step-body">
          <strong>Fast-Defer Queue &amp; Cooldown leo thang (U1 + v3.8)</strong>
          <span>Gặp 429 &rarr; đẩy <code>deferred_ids</code>, ngủ <code>60&rarr;120&rarr;240&rarr;360&rarr;600s</code>; hồi nhịp nhanh 5,0&rarr;3,15s</span>
        </div>
      </div>
    </div>
  </div>
  <div class="pf-connector" aria-hidden="true">
    <svg width="20" height="16" viewBox="0 0 20 16" fill="none">
      <line x1="10" y1="0" x2="10" y2="16" stroke="currentColor" stroke-width="1.8" stroke-dasharray="3 3"/>
    </svg>
    <div class="pf-queue-pill">
      <span>&#8645; Đẩy gói nguồn vào hàng đợi giải nén (<code>extract_queue</code> — hạn mức RAM 192 MiB)</span>
    </div>
    <svg width="20" height="22" viewBox="0 0 20 22" fill="none">
      <line x1="10" y1="0" x2="10" y2="15" stroke="currentColor" stroke-width="1.8"/>
      <path d="M5 12L10 19L15 12" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
  </div>
  <div class="pf-stage-card pf-stage-extract">
    <div class="pf-stage-header">
      <div class="pf-stage-title">
        <span class="pf-stage-dot"></span>
        <span>2. Pool extract-worker (2 luồng) — CPU &amp; Disk Consumer (v3.4 Extract-Turbo)</span>
      </div>
      <span class="pf-rate-badge">Đa nhân CPU · FastGzipStream 512 KiB</span>
    </div>
    <div class="pf-steps-grid">
      <div class="pf-step-item">
        <span class="pf-step-num">5</span>
        <div class="pf-step-body">
          <strong>Giải nén 1-pass luồng lớn (E1)</strong>
          <span><code>_FastGzipStream</code> 512 KiB; kiểm tra trailer CRC ở tầng C (<code>zlib</code>)</span>
        </div>
      </div>
      <div class="pf-step-item">
        <span class="pf-step-num">6</span>
        <div class="pf-step-body">
          <strong>Lọc .tex, .bib &amp; .bbl + Cache thư mục (U4 + E2)</strong>
          <span>Bỏ ảnh nhị phân; giữ thêm <code>.bbl</code> cho M2; cache <code>created_dirs</code> giảm 98% syscall</span>
        </div>
      </div>
      <div class="pf-step-item">
        <span class="pf-step-num">7</span>
        <div class="pf-step-body">
          <strong>Cài đặt Fast-Path &amp; Ghi Manifest sau cùng (E5)</strong>
          <span>Ghi <code>.vK.part/meta.json</code> &rarr; <code>os.replace</code> sang <code>vK/</code> &rarr; cập nhật <code>manifest.sqlite</code></span>
        </div>
      </div>
      <div class="pf-step-item">
        <span class="pf-step-num">8</span>
        <div class="pf-step-body">
          <strong>Đếm phiên bản nguyên tử (E3)</strong>
          <span><code>paper_pending_versions == 0</code> &rarr; chỉ phiên bản cuối mới đẩy bài sang <code>s2_queue</code></span>
        </div>
      </div>
    </div>
  </div>
  <div class="pf-connector" aria-hidden="true">
    <svg width="20" height="16" viewBox="0 0 20 16" fill="none">
      <line x1="10" y1="0" x2="10" y2="16" stroke="currentColor" stroke-width="1.8" stroke-dasharray="3 3"/>
    </svg>
    <div class="pf-queue-pill">
      <span>&#8645; Đẩy bài hoàn tất nguồn vào hàng đợi tham khảo (<code>s2_queue</code>)</span>
    </div>
    <svg width="20" height="22" viewBox="0 0 20 22" fill="none">
      <line x1="10" y1="0" x2="10" y2="15" stroke="currentColor" stroke-width="1.8"/>
      <path d="M5 12L10 19L15 12" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
  </div>
  <div class="pf-stage-card pf-stage-s2">
    <div class="pf-stage-header">
      <div class="pf-stage-title">
        <span class="pf-stage-dot"></span>
        <span>3. s2-worker &amp; Luồng Dịch vụ Nền (Semantic Scholar, Checkpoint, Sampler)</span>
      </div>
      <span class="pf-rate-badge">Adaptive Rate &ge; 1,1s · Background Workers</span>
    </div>
    <div class="pf-steps-grid pf-steps-3">
      <div class="pf-step-item">
        <span class="pf-step-num">9</span>
        <div class="pf-step-body">
          <strong>S2 Batch 100 ID (S1&ndash;S3)</strong>
          <span><code>POST /paper/batch</code> &rarr; fallback phân trang <code>GET .../references</code> (limit 1000)</span>
        </div>
      </div>
      <div class="pf-step-item">
        <span class="pf-step-num">10</span>
        <div class="pf-step-body">
          <strong>Lưu tham khảo &amp; Marker S2</strong>
          <span>Ghi <code>references.json</code> vào mọi <code>vK/</code> + cập nhật <code>venue</code> + ghi <code>raw.gz</code></span>
        </div>
      </div>
      <div class="pf-step-item">
        <span class="pf-step-num">11</span>
        <div class="pf-step-body">
          <strong>Checkpoint nền &amp; Đo RAM O(1)</strong>
          <span>Nén streaming <code>.tar.gz</code> nền (<code>skip_if_unchanged</code>) + <code>ResourceSampler</code> đo RSS 5s/lần</span>
        </div>
      </div>
    </div>
  </div>
  <div class="pf-connector" aria-hidden="true">
    <svg width="20" height="26" viewBox="0 0 20 26" fill="none">
      <line x1="10" y1="0" x2="10" y2="19" stroke="currentColor" stroke-width="1.8"/>
      <path d="M5 16L10 23L15 16" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
  </div>
  <div class="pf-endpoint-node pf-output">
    <span class="pf-icon">&#10003;</span>
    <span>Kiểm chứng toàn vẹn (<code>validate_corpus.py</code>) &rarr; Xuất Parquet, <code>summary.json</code> &amp; <code>cross_version_dedup</code> (<code>export_data.py</code>)</span>
  </div>
</div>

### Bước 1 — Khám phá mục bài báo và lịch sử phiên bản (`discovery.py` — O2 + T3)

1. **Tra cứu theo lô 250 ID gốc (T3):** Bộ thu thập gửi tham số `id_list` gồm tối đa **250 định danh** mỗi lượt tới `https://export.arxiv.org/api/query` (giảm 5 lần số request Atom API so với lô 50 ID trước đây). Phản hồi Atom XML trả về định danh kèm hậu tố phiên bản mới nhất (ví dụ `http://arxiv.org/abs/2408.11047v3`), cho phép suy ra chính xác tổng số phiên bản $N$ và ngày nộp bản đầu tiên (`v1`) từ thẻ `<published>`.
2. **Tận dụng thẻ `<updated>` cho bài có 2 phiên bản (O2):** Thẻ `<updated>` trong entry Atom phản ánh ngày của phiên bản mới nhất $v_N$. Với các bài báo có đúng $N = 2$ phiên bản (chiếm gần 30% tổng số bài trên arXiv), `<updated>` chính là ngày của $v_2$, cho phép điền thẳng `revised_dates = [updated]` mà **không tốn thêm bất kỳ lượt gọi API phụ nào**! Với $N \ge 3$, hệ thống giữ `<updated>` cho bản $v_N$ và chỉ cần truy vấn bổ sung các bản trung gian $v_2 \dots v_{N-1}$.
3. **Xác nhận ID vắng mặt theo sub-batch 50 ID (T3):** Bất kỳ ID nào vắng mặt trong lô 250 được kiểm tra lại theo từng cụm nhỏ **50 ID** (`_CONFIRM_BATCH_SIZE = 50`). Chỉ khi lần kiểm tra sub-batch vẫn không tìm thấy, định danh đó mới được ghi nhận là `not_found` (với $v=1$) trong manifest mà không tạo thư mục rác trên đĩa.
4. **Truy vấn ngày sửa đổi trung gian (`fetch_revised_dates`):** Gom các định danh phiên bản trung gian (`idv2 .. idv{N-1}`) thành các lô 250 để truy xuất chính xác mốc thời gian cập nhật. Khi hoàn tất, ghi nguyên tử siêu dữ liệu bài báo vào `data/papers/<dirname>/paper.json`.

### Bước 2 — Tải gói nguồn toàn văn, đệm RAM, Range Retry & Giải nén Turbo (`source.py`, `pipeline.py`)

Với mỗi bài báo hợp lệ, `MainThread` duyệt tuần tự qua các phiên bản $v_1 \dots v_N$:

1. **Đệm RAM Zero-Copy $\le 96\text{ MiB}$ & Ngắt sớm ở 512 bytes (O3 + O5 + T5):**
   - Phiên bản được tải qua `https://export.arxiv.org/src/{id}vK` bằng luồng đọc từng khung **256 KiB** (tự động nâng lên **512 KiB** cho gói $\ge 25\text{ MiB}$). Dữ liệu được nối thẳng vào `bytearray` trong bộ nhớ RAM — **0 byte ghi xuống đĩa tạm `data/.tmp/`** với $>99{,}5\%$ bài báo.
   - Ngay ở **512 bytes đầu tiên**, bộ kiểm tra magic bytes xác định định dạng: nếu là `%PDF` hoặc kho `ZIP`, hệ thống ngắt luồng tải sớm (nếu phần còn lại $\le 64\text{ KiB}$ thì đọc nốt để tái sử dụng TCP Keep-Alive) và ghi nhận trạng thái `no_source` với `kept_bytes = 0`.
2. **Nối tiếp luồng đứt bằng `HTTP 206 Range` lịch sự (T2 + v3.5):**
   - Nếu mạng bị đứt giữa chừng (`ChunkedEncodingError`, mất kết nối), `download_source` giữ nguyên các byte đã nhận trong đệm RAM, đóng ngay socket cũ bị bóp băng thông (`client.recycle_session()`), và đợi một khoảng nghỉ lịch sự tuân thủ nghiêm quy tắc $T_{\text{End-to-Start}} \ge 3{,}0\text{ s}$ (`3,0 s \to 4,5 s \to 6,0 s`).
   - Hệ thống gửi tiếp `Range: bytes={written}-` trên một TCP socket mới, khôi phục luồng tải mà không phải tải lại từ byte 0, giới hạn tối đa **4 lượt thử / phiên bản** để tránh bão request lặp.
3. **Fast-Defer Queue & Cooldown leo thang bảo vệ IP (U1 + v3.8):**
   - Khi gặp HTTP `429` ở lượt chính, pipeline lập tức nhả socket, đẩy ngay bài đó vào hàng đợi `deferred_ids` (bỏ hoàn toàn cơ chế đứng chờ 15 s tại chỗ gây kẹt luồng) và kích hoạt chế độ Cooldown leo thang thông minh: **`60 s &rarr; 120 s &rarr; 240 s &rarr; 360 s &rarr; 600 s`**. Bộ điều nhịp nới trần thích ứng lên `5,0 s` (`+0,50 s`), nhưng thu hẹp nhanh `-0,75 s` sau mỗi chuỗi 2 lượt `GET 200` sạch để lập tức lấy lại nhịp tối đa khi mạng thông thoáng. Định kỳ sau mỗi **300 ID thực tải**, hệ thống chủ động nghỉ 60 s để tản nhiệt IP và xóa bộ đếm trượt của CDN Fastly. Toàn bộ các bài trong `deferred_ids` được tự động quét vét sạch ở cuối dải.
4. **Giải nén 1-pass luồng lớn qua `_FastGzipStream` 512 KiB (E1):**
   - Ngay khi tải xong byte cuối, `MainThread` đẩy gói dữ liệu sang `extract_queue` (có van điều tiết trần RAM `extract_max_queue_bytes = 192 MiB` chống tràn bộ nhớ) và nhả ngay `RateLimiter` để tải tiếp gói sau.
   - Pool gồm **2 luồng `extract-worker`** lấy gói từ hàng đợi và mở luồng giải nén bằng `_FastGzipStream`: cắt các khối zero-copy **512 KiB** từ `memoryview` truyền thẳng vào `zlib.decompressobj(16 + zlib.MAX_WBITS)`, kiểm tra header gzip và trailer CRC32/ISIZE hoàn toàn ở tầng mã C (nhanh gấp 3–5 lần so với `gzip.GzipFile` mặc định của CPython).
5. **Trích xuất chọn lọc `.tex`, `.bib` và `.bbl` (U4) + Cache thư mục cha (E2):**
   - Kiểm tra an toàn: từ chối tuyệt đối path traversal (`..`, đường dẫn tuyệt đối, thiết bị Windows `CON`/`NUL`), chống zip-bomb (`max_extract_bytes = 2 GiB`).
   - Bỏ qua mọi tệp hình ảnh nhị phân (.png, .pdf, .eps...) và tệp tạm (.aux, .log...); **chỉ giữ lại các tệp `.tex`, `.bib` và `.bbl` (tệp bibliography đã biên dịch phụ trợ — quy chuẩn U4)**.
   - Áp dụng bộ nhớ đệm thư mục cha `created_dirs` để chỉ gọi syscall `mkdir` và kiểm tra `is_relative_to` đúng 1 lần cho mỗi thư mục mới, loại bỏ hơn 95% chi phí I/O hệ thống tệp.
   - Vừa ghi vào `.vK.part/tex/`, vừa băm mã `SHA-256` song song. Ghi đè an toàn nếu gặp tệp trùng tên trong cùng một gói tar (như `JSSC.bib`).
6. **Cài đặt Fast-Path nguyên tử & Ghi Manifest sau cùng (E3 + E5):**
   - Ghi `.vK.part/meta.json` rồi hoán đổi nguyên tử `part.replace(final)` sang `vK/`. Ghi `manifest.sqlite` ở bước sau cùng để đảm bảo tính bất biến khi có sự cố mất nguồn.
   - Bộ đếm nguyên tử `paper_pending_versions[arxiv_id]`: hai phiên bản $v_1$ và $v_2$ của cùng một bài có thể được 2 worker giải nén song song trên 2 nhân CPU; chỉ worker nào hoàn tất phiên bản cuối cùng (`pending == 0`) mới đẩy bài sang `s2_queue`.

### Bước 3 — Thu thập siêu dữ liệu tham khảo (`s2.py` — S1–S3, U2)

1. **Gom lô 100 bài/lô (`_collect_s2_batch` — S1):** Luồng `s2-worker` lấy job từ `s2_queue`, chờ gom trong cửa sổ 0,35–45 s để đạt lô tối đa **100 bài báo** gửi tới `POST https://api.semanticscholar.org/graph/v1/paper/batch`. Phương pháp gom lô giúp giảm số lượt gọi mạng Semantic Scholar đi 100 lần so với truy vấn đơn lẻ.
2. **Phân trang dự phòng khi danh sách tham khảo bị cắt (S1):** Sau khi nhận batch, hệ thống kiểm tra điều kiện `referenceCount > len(references)`. Với những bài tổng quan có danh sách trích dẫn dài bị API lô cắt bớt, hệ thống tự động kích hoạt truy vấn phân trang `GET /graph/v1/paper/ARXIV:{id}/references?offset=&limit=1000` cho tới khi thu thập đủ 100% trích dẫn.
3. **Lưu trữ nguyên tử & Chế độ độc lập `--s2-only` (U2):** Ghi danh sách `references.json` vào **mọi thư mục phiên bản $v_1 \dots v_N$** của bài báo (`s2_scope = "paper"`), cập nhật trường `venue` vào `paper.json`, và ghi tệp nén `s2_references.raw.json.gz` làm marker hoàn tất. Khi cần cào bù trích dẫn mà không chạm vào mạng arXiv, cờ CLI `--s2-only` cho phép quét nhanh các thư mục bài trên đĩa và hoàn tất 5.000 ID chỉ trong 3–6 phút.

---

## 2.2. Tổng hợp Công cụ, Thư viện & Kiến trúc Module

Bảng dưới đây đối chiếu bộ công cụ kỹ thuật thực tế được triển khai với các giải pháp trong "hộp công cụ" của đề bài:

| Hạng mục | Công cụ / Thư viện sử dụng | Vai trò & Đánh giá kỹ thuật so với giải pháp khác |
| :--- | :--- | :--- |
| **Khám phá bài báo** | **arXiv Atom API** (`/api/query`) + `xml.etree.ElementTree` | Tra cứu theo lô 250 ID gốc (T3) kết hợp tối ưu `<updated>` (O2) và sub-batch 50 ID xác nhận missing. Khám phá 5.000 ID chỉ tốn ~30 request (~1,5 phút). Không dùng OAI-PMH hay Kaggle do hai công cụ này thiết kế cho quét toàn kho và không hỗ trợ tra cứu ngày sửa đổi chi tiết theo dải ID rời rạc. |
| **Tải gói mã nguồn** | **`export.arxiv.org/src/`** + `requests` (`urllib3`) | 1 kết nối đơn qua `_SingleConnAdapter` (`TCP_NODELAY = 1`, bảo toàn Linux `tcp_rmem` auto-tuning tới 6 MiB, xoay vòng session mỗi 120–400 req). Đệm RAM `bytearray` $\le 96\text{ MiB}$ (O3 + T5), ngắt sớm 512 bytes PDF/ZIP (O5), nối tiếp `HTTP 206 Range` lịch sự (T2). |
| **Giải nén & Lọc TeX** | **`_FastGzipStream`** + `tarfile` + `hashlib` | Luồng giải nén 512 KiB với kiểm tra CRC32 ở tầng C (`zlib.decompressobj`), cache thư mục cha `created_dirs` (E2). Trích xuất chọn lọc chỉ giữ **`.tex`, `.bib` và `.bbl`** (U4), ghi đè POSIX tar an toàn. |
| **Trích xuất tham khảo** | **Semantic Scholar Graph API** (`requests` + `S2_API_KEY`) | Batch 100 ID (`POST /paper/batch`) kết hợp phân trang `limit=1000`; bộ điều nhịp thích ứng $\ge 1{,}1\text{ s}$ + jitter; hỗ trợ chạy độc lập `--s2-only` (U2). |
| **Quản lý trạng thái & Chịu lỗi** | `sqlite3` (WAL mode) + `msvcrt`/`fcntl` | Khóa tiến trình cấp hệ điều hành `_acquire_workspace_lock` (chống chạy trùng 2 crawler trên cùng thư mục `data/`), sổ trạng thái manifest ghi sau cùng, lưu mốc cooldown liên tiến trình `rate_state.json` (U3). |
| **Sao lưu nền & Chống thoái lui** | `checkpoint.py` (`tarfile`, `gzip`) | Chụp ảnh nóng SQLite qua `Connection.backup()`, nén streaming `.tar.gz` ở nền song song với lúc ngủ cooldown 429, kèm `shrink guard` và bỏ qua nén khi dữ liệu không đổi (`skip_if_unchanged=True`). |
| **Đo lường & Phân tích phiên** | `psutil`, `time.perf_counter`, `pyarrow`, `pandas`, `jupyter-book` | Luồng daemon `ResourceSampler` đo RAM RSS mỗi 5 s (truy xuất $O(1)$), bộ lọc bí mật `SecretRedactingFilter`, xuất Parquet chuẩn hóa, bộ tổng hợp đa phiên Colab `summarize_sessions()` bóc tách thời gian thực và thời gian chờ phạt. |

Mã nguồn trong repository [`GiaaPhuc/arxiv-pipeline`](https://github.com/GiaaPhuc/arxiv-pipeline) được tổ chức phân tầng chặt chẽ và bảo vệ bằng **261 bài kiểm thử đơn vị (unit tests pass 100%)** với `pytest` và fixtures ngoại tuyến:

| Nhóm chức năng | Các module trong `src/` | Trách nhiệm kỹ thuật chính |
| :--- | :--- | :--- |
| **Định danh & Hợp đồng dữ liệu** | `crawler/models.py`, `crawler/ids.py`, `crawler/config.py` | Hợp đồng dữ liệu bất biến (`SCHEMA_VERSION = 1`), chuẩn hóa định danh mới/cũ, mở rộng dải `id_ranges.csv` thành 25.000 ID, nạp cấu hình môi trường. |
| **Giao tiếp mạng & Điều nhịp** | `crawler/http.py`, `crawler/discovery.py`, `crawler/source.py`, `crawler/s2.py` | Quản lý phiên HTTP, bộ điều nhịp Start-to-Start $3{,}15\text{ s} + \text{jitter}$, адаптивные границы $5{,}0\text{ s}$, lưu trạng thái cooldown `rate_state.json`, khám phá Atom lô 250, tải đệm RAM 96 MiB, Range 206 retry, giải nén turbo và S2 batch 100 ID. |
| **Điều phối, Hàng đợi & Bền bỉ** | `crawler/pipeline.py`, `crawler/manifest.py`, `crawler/checkpoint.py`, `run_crawl.py` | Điều phối Producer–Consumer đa luồng, pool 2 luồng `extract-worker`, `s2-worker`, hàng đợi `extract_queue` (trần RAM 192 MiB), `deferred_ids`, khóa hệ điều hành OS mutex, checkpoint nền `skip_if_unchanged`, chế độ `--s2-only`. |
| **Đo lường, Kiểm định & Xuất bảng** | `crawler/metrics.py`, `corpus.py`, `validate_corpus.py`, `crawler/export.py`, `export_data.py` | Lấy mẫu RAM $O(1)$, che bí mật nhật ký, kiểm tra 5 bất biến toàn vẹn, xuất 2 bảng Parquet cho Hugging Face, thống kê `cross_version_dedup` và tổng hợp đa phiên `benchmark_summary`. |
| **Cầu nối Milestone 2** | `parsing/models.py`, `parsing/pipeline.py`, `run_parse.py` | Khóa hợp đồng dữ liệu M2 (Phase 0), khung điều phối phân tích cú pháp đa nhân đọc trực tiếp cây `.tex`/`.bib`/`.bbl` từ kho M1. |

---

## 2.3. Chính sách Lịch sự Máy chủ, Chịu lỗi & Kiểm chứng Dữ liệu

Vận hành thu thập quy mô lớn trên Google Colab đòi hỏi sự cân bằng tuyệt đối giữa **chuẩn lịch sự máy chủ học thuật** và **khả năng chịu lỗi tự động 100%**:

1. **Chuẩn lịch sự Start-to-Start $\ge 3{,}0\text{ s}$ & Cơ chế Tản nhiệt IP thích ứng (`http.py`):**
   - Bộ điều nhịp `RateLimiter` duy trì nhịp cơ sở **Start-to-Start $3{,}15\text{ s}$** kèm **Jitter ngẫu nhiên $0 \dots 0{,}30\text{ s}$** trên 1 kết nối duy nhất tới `export.arxiv.org` (sàn cứng $\ge 3{,}0\text{ s}$, tuân thủ nghiêm ngặt chính sách arXiv [[1, 2]](#tai-lieu-tham-khao)). Sàn nghỉ hậu tải `min_idle_gap = 1{,}50\text{ s}$` (sau các bài nặng tải $\ge 4\text{ MiB}$) đảm bảo socket có thời gian tản nhiệt, kết hợp xoay vòng `recycle_session()` mỗi 120 request để làm sạch trạng thái trên CDN.
   - Khi gặp HTTP `429`, hệ thống **không đứng chờ 15 s tại chỗ** và **bỏ hoàn toàn cơ chế gửi dồn "0s extra wait"**: bài báo được đẩy ngay vào `deferred_ids` và pipeline ngủ **Cooldown leo thang thông minh: `60 s &rarr; 120 s &rarr; 240 s &rarr; 360 s &rarr; 600 s`**. Sau khi thức dậy, nhịp thích ứng nâng lên trần an toàn `5,0 s` nhưng hồi phục nhanh `-0,75 s` sau mỗi chuỗi 2 bài `GET 200` sạch để sớm lấy lại nhịp đỉnh `3,15 s`. Định kỳ sau mỗi **300 ID thực tải**, pipeline chủ động giải nhiệt 60 s để xóa bộ đếm trượt của Fastly. Tuyệt đối không kích hoạt ngủ phạt sau các bài tải thành công (`ok`/`no_source`).
2. **Nối tiếp luồng tải HTTP 206 Range lịch sự & Bảo toàn byte tải dở (`source.py`):**
   - Khi gặp sự cố đứt stream mạng (`ChunkedEncodingError`, mất kết nối), pipeline bảo toàn nguyên vẹn số byte đã nhận trong RAM (hoặc tệp `.resume.part`), đóng socket cũ, chờ lịch sự $T_{\text{End-to-Start}} \ge 3{,}0\text{ s}$ (`3,0 s \to 4,5 s \to 6,0 s`) rồi gửi header `Range: bytes={written}-` trên socket mới. Cơ chế này giới hạn cứng tối đa 4 lượt thử / phiên bản, loại bỏ hoàn toàn bão request lặp và tiết kiệm hàng chục GiB băng thông tải lại.
3. **Khóa tiến trình cấp hệ điều hành & Lưu Cooldown liên tiến trình (`pipeline.py`, `http.py`):**
   - Hàm `_acquire_workspace_lock` sử dụng cơ chế khóa tệp cấp nhân hệ điều hành (`msvcrt.locking` trên Windows, `fcntl.flock` trên Linux) tại thư mục tạm hệ thống, ngăn chặn triệt để lỗi người dùng mở trùng 2 tiến trình crawler ghi đè lên cùng thư mục `data/`.
   - File `data/logs/rate_state.json` lưu trữ mốc thời gian phạt còn dư (`arxiv_cooldown_until`, `s2_cooldown_until`); nếu tiến trình bị khởi động lại trong lúc đang chịu cooldown, crawler mới tự động chờ hết thời gian phạt trước khi gửi bất kỳ request nào.
4. **Lưu trữ hai tầng chống nghẽn FUSE & Sao lưu nền thông minh (`checkpoint.py`):**
   - Mọi thao tác đọc/ghi diễn ra trên ổ SSD cục bộ của máy ảo. Định kỳ sau mỗi `backup_every_ids` ID mới (hoặc khi ngủ cooldown 429), luồng `checkpoint-worker` chụp snapshot SQLite bằng `Connection.backup()` và nén streaming sang `arxiv-data.tar.gz` ở nền song song, hoàn toàn không chặn luồng tải chính.
   - **Shrink Guard & Skip Unchanged:** Bản backup mới được bảo vệ bởi tệp sidecar `.meta.json` lưu chữ ký tiến độ `(final_pairs, s2_done)` — tuyệt đối không bao giờ ghi đè lùi dữ liệu nếu ít cặp hơn, và tự động bỏ qua 100% chi phí I/O nén lại khi dữ liệu không thay đổi (`skip_if_unchanged=True`).
5. **Kiểm chứng toàn vẹn hậu thu thập (`validate_corpus.py`) & Hợp đồng dữ liệu đa Milestone:**
   - Trình kiểm định độc lập quét toàn bộ kho để xác nhận 5 bất biến: *(i)* đủ thư mục phiên bản liên tục `v1..vN`; *(ii)* không tồn tại tệp lạ ngoài siêu dữ liệu chuẩn và `.tex`/`.bib`/`.bbl`; *(iii)* khớp 100% dung lượng và mã băm `SHA-256` với `meta.json`; *(iv)* manifest nhất quán với đĩa và không còn bản ghi `pending`; *(v)* hai bảng Parquet tuân thủ đúng khóa không rỗng.
   - **Ghi nhận về đặc thù dữ liệu thượng nguồn và chuẩn bị cho Milestone 2:**
     1. *Phạm vi phiên bản trên S2 (`s2_scope = "paper"`):* Semantic Scholar lập chỉ mục danh sách tham khảo ở cấp bài báo gốc (`ARXIV:<base_id>`) thay vì từng phiên bản riêng biệt; do đó danh sách tham khảo phản ánh phiên bản mới nhất được S2 lập chỉ mục.
     2. *Bài báo chưa bóc tách được tham khảo trên S2:* Một tỷ lệ nhỏ bài báo mới hoặc có bố cục PDF đặc thù trả về danh sách rỗng từ S2 sẽ được đối soát trực tiếp với mã nguồn `.tex`/`.bib` ở Milestone 2.
     3. *Giữ lại tệp biên dịch sẵn `.bbl` (quy chuẩn U4):* Khác với quy định ban đầu chỉ giữ `.tex` và `.bib`, nhóm đã cập nhật chính sách trích xuất giữ lại các tệp `.bbl` (danh mục tài liệu tham khảo đã được LaTeX biên dịch hoàn chỉnh) nhằm cung cấp thêm căn cứ đối sánh trích dẫn quan trọng cho bộ phân tích cú pháp ở Milestone 2.
