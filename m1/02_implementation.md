# Chương 2. Quá trình Triển khai & Công cụ Sử dụng

## 2.1. Quy trình Thu thập Đầu–Cuối (End-to-End Pipeline)

Khác với các bộ thu thập tuần tự đơn luồng truyền thống (vốn mất hơn 15 giờ và dễ bị nghẽn I/O đĩa), hệ thống `arxiv-pipeline` được thiết kế theo kiến trúc **Producer–Consumer Đa luồng Tối ưu** (phiên bản v3.10 Clean Lean Turbo / v3.11). Kiến trúc này phân tách độc lập thành **5 nhóm luồng** chuyên trách: tầng **Mạng arXiv** (`MainThread` — Network Producer, tuân thủ nghiêm ngặt 1 kết nối duy nhất tới `export.arxiv.org`), tầng **Giải nén CPU/Đĩa** (Pool `extract-worker` 2 luồng), tầng **Mạng Semantic Scholar** (`s2-worker`), luồng **Sao lưu nền** (`checkpoint-worker`) và daemon **Đo đạc viễn trắc** (`resource-sampler`). Nhờ đó, hệ thống hoàn tất trọn vẹn dải 5.000 ID trong **~6,4 – 7,4 giờ** (tốc độ trung bình **~3,25s / lần tải** với gói thông thường, 0% lỗi 429 từ phía crawler):

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
      <span class="pf-rate-badge">1 kết nối · Start-to-Start &ge; 3,0s (3,15s + jitter) · Sàn nghỉ socket &ge; 3,05s</span>
    </div>
    <div class="pf-steps-grid">
      <div class="pf-step-item">
        <span class="pf-step-num">1</span>
        <div class="pf-step-body">
          <strong>Khám phá Atom API &amp; Bù ngày OAI-PMH</strong>
          <span><code>/api/query</code> (lô 250 ID) &rarr; tận dụng <code>&lt;updated&gt;</code> cho bài 2 bản &rarr; bù ngày OAI-PMH <code>arXivRaw</code> &rarr; kiểm tra thiếu lô 50 ID</span>
        </div>
      </div>
      <div class="pf-step-item">
        <span class="pf-step-num">2</span>
        <div class="pf-step-body">
          <strong>Tải dạng dòng &amp; Đệm RAM Zero-Copy</strong>
          <span>Khung 256/512 KiB vào <code>bytearray</code> (&le; 96 MiB); ngắt sớm ở 512B cho <code>%PDF</code>/<code>ZIP</code>; đo timing thuần socket wire</span>
        </div>
      </div>
      <div class="pf-step-item">
        <span class="pf-step-num">3</span>
        <div class="pf-step-body">
          <strong>Paced Streaming &amp; Thử lại Range tại chỗ</strong>
          <span>Paced Streaming 4,5 MiB/s cho gói &gt; 512 KiB; đệm nghỉ 3,15s (&ge;2MB); Range Resume tại chỗ (nghỉ 12–14s); nạp hồi 12s mỗi 50MB</span>
        </div>
      </div>
      <div class="pf-step-item">
        <span class="pf-step-num">4</span>
        <div class="pf-step-body">
          <strong>Hoãn tải thông minh &amp; Cooldown khóa trần</strong>
          <span>Đứt stream lưu <code>.part</code> defer 0s; cách ly lỗi stream; Cooldown leo thang <code>120&rarr;180&rarr;240s</code>; Clean Lean Turbo tắt ngủ định kỳ</span>
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
        <span>2. Pool extract-worker (2 luồng) — CPU &amp; Disk Consumer (Giải nén &amp; Lọc)</span>
      </div>
      <span class="pf-rate-badge">Đa nhân CPU · FastGzipStream 512 KiB · Bộ nhớ đệm thư mục cha</span>
    </div>
    <div class="pf-steps-grid">
      <div class="pf-step-item">
        <span class="pf-step-num">5</span>
        <div class="pf-step-body">
          <strong>Giải nén 1-pass tốc độ cao</strong>
          <span><code>_FastGzipStream</code> 512 KiB buffer; giải mã zlib và kiểm tra trailer CRC32 ở tầng C</span>
        </div>
      </div>
      <div class="pf-step-item">
        <span class="pf-step-num">6</span>
        <div class="pf-step-body">
          <strong>Lọc mã nguồn chọn lọc &amp; Cache thư mục</strong>
          <span>Chỉ giữ <code>.tex</code>, <code>.bib</code>, <code>.bbl</code>; bỏ ảnh nhị phân &amp; file rác; chống path traversal; giảm 98% syscall</span>
        </div>
      </div>
      <div class="pf-step-item">
        <span class="pf-step-num">7</span>
        <div class="pf-step-body">
          <strong>Ghi nguyên tử &amp; Cập nhật Manifest sau cùng</strong>
          <span>Ghi <code>.vK.part/</code> &rarr; băm SHA-256 song song &rarr; <code>os.replace</code> sang <code>vK/</code> &rarr; cập nhật <code>manifest.sqlite</code> sau cùng</span>
        </div>
      </div>
      <div class="pf-step-item">
        <span class="pf-step-num">8</span>
        <div class="pf-step-body">
          <strong>Điều phối bài hoàn tất nguyên tử</strong>
          <span>Bộ đếm <code>paper_pending_versions == 0</code> &rarr; chỉ khi toàn bộ phiên bản xong mới đẩy bài sang <code>s2_queue</code></span>
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
      <span class="pf-rate-badge">Adaptive Rate &ge; 1,1s · Gom lô 25 bài · Luồng ngầm độc lập</span>
    </div>
    <div class="pf-steps-grid pf-steps-3">
      <div class="pf-step-item">
        <span class="pf-step-num">9</span>
        <div class="pf-step-body">
          <strong>Gom lô S2 &amp; Bisection chia đôi</strong>
          <span><code>POST /paper/batch</code> (25 bài); chia đôi lô đệ quy khi 413/5xx; fallback phân trang <code>limit=1000</code></span>
        </div>
      </div>
      <div class="pf-step-item">
        <span class="pf-step-num">10</span>
        <div class="pf-step-body">
          <strong>Lưu trữ &amp; Dự phòng cục bộ (.bib/.bbl)</strong>
          <span>Khi S2 404 &rarr; bóc tách <code>.bib/.bbl</code> cục bộ; lưu <code>references.json</code> vào mọi <code>vK/</code>; hỗ trợ <code>--skip-s2</code></span>
        </div>
      </div>
      <div class="pf-step-item">
        <span class="pf-step-num">11</span>
        <div class="pf-step-body">
          <strong>Sao lưu nền an toàn &amp; Đo viễn trắc</strong>
          <span><code>checkpoint-worker</code> snapshot SQLite, nén <code>.tar.gz</code> (shrink guard, <code>skip_if_unchanged</code>) + <code>ResourceSampler</code> đo RAM/Đĩa</span>
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
    <span>Kiểm chứng toàn vẹn (<code>validate_corpus.py</code> &amp; <code>audit_corpus.py</code>) &rarr; Xuất Parquet, <code>summary.json</code> &amp; <code>cross_version_dedup</code> (<code>export_data.py</code>)</span>
  </div>
</div>

### Bước 1 — Khám phá bài báo và lịch sử phiên bản qua Atom API & OAI-PMH (`discovery.py`)

1. **Tra cứu theo lô 250 định danh gốc:** Bộ thu thập duyệt danh sách ID theo từng chunk 500 ID (khớp với cấu hình sao lưu `backup_every_ids`) và gửi tham số `id_list` gồm tối đa **250 định danh** mỗi lượt tới `https://export.arxiv.org/api/query` (giảm 5 lần số request Atom API so với lô 50 ID ban đầu). Phản hồi Atom XML trả về định danh kèm hậu tố phiên bản mới nhất (ví dụ `http://arxiv.org/abs/2408.11047v3`), cho phép suy ra chính xác tổng số phiên bản $N$ và ngày nộp bản đầu tiên (`v1`) từ thẻ `<published>`.
2. **Tận dụng thẻ `<updated>` cho bài có 2 phiên bản:** Thẻ `<updated>` trong entry Atom phản ánh ngày của phiên bản mới nhất $v_N$. Với các bài báo có đúng $N = 2$ phiên bản (chiếm gần 30% tổng số bài trên arXiv), `<updated>` chính là ngày của $v_2$, cho phép điền thẳng `revised_dates = [updated]` mà **không tốn thêm bất kỳ lượt gọi API phụ nào**! Với $N \ge 3$, hệ thống giữ `<updated>` cho bản $v_N$ và truy vấn bổ sung các bản trung gian $v_2 \dots v_{N-1}$.
3. **Bù ngày trung gian qua OAI-PMH (`--enable-oai-dates`):** Với các bài báo có $N \ge 3$ phiên bản, nếu Atom API vẫn khuyết ngày sửa đổi của các bản trung gian $v_2 \dots v_{N-1}$, khi cờ `--enable-oai-dates` được kích hoạt, crawler tự động truy vấn OAI-PMH (`arXivRaw`) để bóc tách ngày nộp chính thức của các bản $v_2 \dots v_N$, đảm bảo nguyên tắc toàn vẹn dữ liệu: `len(paper.revised_dates) == paper.num_versions - 1`.
4. **Xác nhận định danh vắng mặt theo nhóm nhỏ 50 ID:** Bất kỳ ID nào vắng mặt trong lô 250 được kiểm tra lại theo từng cụm nhỏ **50 ID** (`_CONFIRM_BATCH_SIZE = 50`). Chỉ khi lần kiểm tra này vẫn không tìm thấy, định danh đó mới được ghi nhận là `not_found` (với $v=1$) trong manifest mà không tạo thư mục rác trên đĩa.
5. **Lưu trữ nguyên tử:** Ghi nguyên tử siêu dữ liệu bài báo vào `data/papers/<dirname>/paper.json`.

### Bước 2 — Tải gói nguồn, điều tiết lưu lượng và giải nén tối ưu (`source.py`, `pipeline.py`)

Với mỗi bài báo hợp lệ, `MainThread` duyệt tuần tự qua các phiên bản $v_1 \dots v_N$:

1. **Đệm RAM Zero-Copy $\le 96\text{ MiB}$ & Ngắt sớm ở 512 bytes:**
   - Phiên bản được tải qua `https://export.arxiv.org/src/{id}vK` bằng luồng đọc từng khung **256 KiB** (tự động nâng lên **512 KiB** cho gói $\ge 25\text{ MiB}$). Dữ liệu được nối thẳng vào `bytearray` trong bộ nhớ RAM — **0 byte ghi xuống đĩa tạm `data/.tmp/`** với $>99{,}5\%$ bài báo. Chỉ những gói hiếm hoi $>96\text{ MiB}$ mới tự động tràn ra tệp đệm tạm trên đĩa.
   - Ngay ở **512 bytes đầu tiên**, bộ kiểm tra magic bytes xác định định dạng: nếu phát hiện chữ ký `%PDF` hoặc kho `ZIP`, hệ thống ngắt luồng tải sớm và ghi nhận trạng thái `no_source` với `kept_bytes = 0` (tiết kiệm hơn 95% băng thông cho bài PDF).
   - **Bấm giờ truyền tải thuần socket wire (`download_seconds`):** Thời gian tải được bấm giờ chuẩn xác bên trong vòng lặp đọc socket `iter_content`, tách rời hoàn toàn khỏi thời gian chờ của bộ điều nhịp `RateLimiter`. Nhờ đó, việc đánh giá độ trễ đường truyền phản ánh trung thực tốc độ mạng thực tế, triệt tiêu hoàn toàn sai số timing và ngăn chặn triệt để hiện tượng khóa vòng phản hồi (latch feedback loop) gây nghẽn nhịp.
2. **Điều tiết lưu lượng Paced Streaming 4,5 MiB/s & Phân cấp đệm nghỉ theo dung lượng:**
   - **Điều tiết Paced Streaming (4,5 MiB/s):** Với các gói nhỏ $\le 512\text{ KiB}$ (~75–80% kho bài), crawler đọc trực tiếp với tốc độ tối đa không độ trễ. Khi dung lượng vượt ngưỡng $512\text{ KiB}$, tốc độ đọc socket được điều tiết ở mức **$4{,}5\text{ MiB/s}$** (`_MAX_SUSTAINED_STREAM_BPS`, cấu hình qua biến môi trường `CRAWLER_MAX_STREAM_MBPS`). Mức $4{,}5\text{ MiB/s}$ vừa đủ nhanh để bài 20 MB tải xong trong ~4 giây (thay vì 15 giây), vừa đủ mượt để bảo vệ Token Bucket băng thông của CDN Fastly không bị tràn buffer.
   - **Gói thông thường (< 2 MiB, ~85% kho bài):** Chạy theo nhịp cơ sở (Start-to-Start $3{,}15\text{ s}$, sàn nghỉ socket End-to-Start $3{,}05\text{ s}$).
   - **Phản ứng trễ mạng (TTFB v3.10 Clean Lean Turbo):** Khi thời gian chờ header phản hồi `last_header_elapsed >= 3.5s`, crawler xoay vòng TCP session để làm mới kết nối tránh nghẽn socket, **tuyệt đối không gọi `note_429()`** trên mã `200 OK` (không tự phạt chính mình, giữ nguyên nhịp 3,15s).
   - **Gói trung bình & lớn ($\ge 2\text{ MiB}$ hoặc truyền socket $\ge 2{,}5\text{ s}$ hoặc có nối Range):** Nghỉ đệm lịch sự chuẩn `3,15 s` End-to-Start (xóa bỏ hình phạt ngủ 6,0s thừa thãi của bản cũ).
   - **Nạp hồi băng thông trượt (Mỗi 50 MiB):** Sau mỗi 50 MiB dữ liệu tải thực qua mạng (`_BANDWIDTH_WINDOW_MAX_BYTES = 50 MiB`), crawler tự động xoay vòng socket (`recycle_session()`) và nghỉ `12,0 s` để làm mới hạn mức burst của CDN Fastly khi gặp chùm bài khổng lồ liên tiếp.
3. **Thử lại Range tại chỗ cho file lớn & Bảo toàn byte tải dở (In-Place Multi-Slice Resume):**
   - **Thử lại Range tại chỗ cho file lớn (In-Place Multi-Slice Resume v3.9.9 / v3.11.1):** Khi gặp sự cố đứt stream trên file lớn ($\ge 1\text{ MiB}$), crawler tự động xoay vòng session mới (`recycle_session()`), áp dụng đệm nghỉ an toàn $\ge \mathbf{12{,}0\text{ s} - 14{,}0\text{ s}}$ (`_HEAVY_STREAM_BREAK_BONUS = 9.0s`) để token bucket Fastly CDN edge sạc đầy, sau đó gửi ngay `Range: bytes={written}-` (`HTTP 206 Partial Content`). Nhờ đó các file khổng lồ 20–40 MB hoàn tất sau 2 slice ngay tại chỗ trong ~13,5s mà không bị Fastly trả 429 hay dồn toa sang cuối dải.
   - **Bảo toàn byte tải dở (Zero-Loss Range Resume):** Toàn bộ byte tải được lưu an toàn trong `.resume-{id}-v{version}.part`. **Tuyệt đối không xóa `.part` khi gặp HTTP 429** (429 là giới hạn tần suất/băng thông, không phải từ chối Range); chỉ xóa `.part` khi nhận mã 403 (cấm truy cập) hoặc 416 (dải byte không hợp lệ).
   - **Tách bạch đứt stream khỏi chuỗi phạt 429 (v3.9.7 / v3.11.1):** Đứt luồng do socket Fastly ngắt kết nối (`ChunkedEncodingError`) sau khi đã thử lại tại chỗ được lưu an toàn vào `.part` và **defer bài báo về cuối dải (0s chờ phạt)**, tiếp tục cào ngay bài tiếp theo (`need_cd = False`). Nếu request Range dở dang gặp mã 429, hệ thống nhận diện `is_stream_break` để cách ly: chỉ ngủ breather cố định 60s, **tuyệt đối không tăng `arxiv_429_streak` leo thang**. Chỉ khi có $\ge 2$ bài liên tiếp bị đứt stream thì hệ thống mới ngủ breather cố định 60s để ổn định mạng mà không tăng streak.
   - **Quét vét cuối dải (`deferred_ids`):** Sau khi hoàn tất danh sách chính, crawler duyệt lại các bài trong hàng đợi hoãn (tối đa **5 vòng**), tiếp tục tải phần còn lại qua `HTTP 206 Range` khi endpoint phía arXiv đã nguội hoàn toàn.
4. **Xử lý HTTP 429 & Cooldown leo thang có khóa trần:**
   - Tuyệt đối **không phạt gói thành công 200 OK**.
   - Khi gặp mã HTTP `429` trên `/src/`: đẩy ngay bài báo vào `deferred_ids`, đóng socket cũ qua `recycle_session()`.
   - Ngủ **Cooldown leo thang có giới hạn: `120 s &rarr; 180 s &rarr; 240 s`** (khóa trần tối đa 240 giây, loại bỏ hoàn toàn các mức ngủ sâu kéo dài 600s).
   - **Tự động hạ bậc phạt:** Sau **6 bài liên tiếp tải thành công (200 OK)**, mức phạt streak mới được hạ 1 bậc.
   - **Tản nhiệt chủ động (v3.10 Clean Lean Turbo):** Đặt mặc định `arxiv_proactive_cooldown_every_ids = 0` (tắt tự động ngủ 60s định kỳ; crawler chỉ ngủ khi arXiv THỰC SỰ trả về HTTP 429 hoặc khi được cấu hình rõ). Việc này xóa bỏ hơn 40 phút ngủ tự nguyện lãng phí trên dải 5.000 ID.
5. **Giải nén 1-pass luồng lớn qua `_FastGzipStream` 512 KiB:**
   - Ngay khi tải xong byte cuối, `MainThread` đẩy gói dữ liệu sang `extract_queue` (van điều tiết trần RAM `extract_max_queue_bytes = 192 MiB`, `maxsize = 8` chống tràn bộ nhớ) và nhả ngay `RateLimiter` để tải tiếp gói sau.
   - Pool gồm **2 luồng `extract-worker`** lấy gói từ hàng đợi và mở luồng giải nén bằng `_FastGzipStream`: cắt các khối zero-copy **512 KiB** từ `memoryview` truyền thẳng vào `zlib.decompressobj(16 + zlib.MAX_WBITS)`, kiểm tra header gzip và trailer CRC32/ISIZE hoàn toàn ở tầng mã C (nhanh gấp 3–5 lần so với `gzip.GzipFile` mặc định của CPython).
6. **Trích xuất chọn lọc mã nguồn & Bộ nhớ đệm thư mục cha:**
   - Kiểm tra an toàn: từ chối tuyệt đối path traversal (`..`, đường dẫn tuyệt đối, ký tự điều khiển hệ thống, thiết bị Windows `CON`/`NUL`), chống zip-bomb (`max_extract_bytes = 2 GiB`).
   - Lọc tệp nghiêm ngặt: **chỉ trích xuất các tệp có đuôi `.tex`, `.bib` và `.bbl`** (tệp danh mục tham khảo đã biên dịch phụ trợ). Bỏ qua toàn bộ ảnh (`.png`, `.pdf`, `.eps`), video và tệp nhị phân nhằm tối ưu dung lượng lưu trữ.
   - Áp dụng bộ nhớ đệm thư mục cha `created_dirs` để chỉ gọi syscall `mkdir` và kiểm tra `is_relative_to` đúng 1 lần cho mỗi thư mục mới, loại bỏ hơn 95% chi phí I/O hệ thống tệp.
   - Vừa ghi vào `.vK.part/tex/`, vừa băm mã `SHA-256` song song. Ghi đè an toàn nếu gặp tệp trùng tên trong cùng một gói tar (như `JSSC.bib`).
7. **Cài đặt nguyên tử hai pha & Ghi Manifest sau cùng:**
   - Ghi `.vK.part/meta.json` rồi hoán đổi nguyên tử `part.replace(final)` sang `vK/`. Ghi `manifest.sqlite` ở bước sau cùng để đảm bảo tính bất biến khi có sự cố mất nguồn.
   - Bộ đếm nguyên tử `paper_pending_versions[arxiv_id]`: hai phiên bản $v_1$ và $v_2$ của cùng một bài có thể được 2 worker giải nén song song trên 2 nhân CPU; chỉ worker nào hoàn tất phiên bản cuối cùng (`pending == 0`) mới đẩy bài sang `s2_queue`.

### Bước 3 — Thu thập siêu dữ liệu tham khảo học thuật (`s2.py`)

1. **Gom lô thông minh & Giới hạn nhịp độ:** Luồng `s2-worker` gom tối đa **25 bài báo** (mặc định, cấu hình qua `--s2-batch-size`) từ `s2_queue` trong cửa sổ chờ 45 giây. Giới hạn tần suất tối thiểu **1,1 giây / request** (End-to-Start) qua `AdaptiveRateLimiter`, gửi tới `POST https://api.semanticscholar.org/graph/v1/paper/batch` kèm `x-api-key` (tự che giấu trong nhật ký qua `SecretRedactingFilter`).
2. **Chia đôi lô tự động (Bisection):** Khi gặp mã lỗi `HTTP 413 Payload Too Large` hoặc `5xx` trên mẻ có $\ge 2$ bài, hệ thống tự động chia đôi danh sách ($N/2$) và gửi đệ quy nhằm cô lập các bài chứa danh sách trích dẫn quá lớn mà không làm thất bại cả mẻ.
3. **Phân trang dự phòng khi danh sách tham khảo bị cắt:** Nếu trường `referenceCount` lớn hơn số lượng trích dẫn trả về trong batch, hệ thống tự động kích hoạt truy vấn phân trang `GET /graph/v1/paper/ARXIV:{id}/references?offset=&limit=1000` cho tới khi thu thập đủ 100% trích dẫn.
4. **Dự phòng trích dẫn cục bộ (Dual-Engine Reference Fallback):** Với các bài Semantic Scholar chưa lập chỉ mục (`HTTP 404`), khi kích hoạt cờ `--enable-bib-fallback`, worker tự động đọc và trích xuất danh sách trích dẫn từ các tệp `.bib` và `.bbl` có sẵn trong thư mục mã nguồn bài viết (hoặc chạy làm giàu ngoại tuyến qua `src/enrich_references.py`).
5. **Lưu trữ đồng bộ & Tách luồng linh hoạt (`--skip-s2` / `--s2-only`):** Ghi danh sách `references.json` vào **mọi thư mục phiên bản $v_1 \dots v_N$** của bài báo (`s2_scope = "paper"`), cập nhật trường `venue` vào `paper.json`, và nén file gốc thành `s2_references.raw.json.gz` (hoặc đánh dấu `source: local_bib`) làm marker hoàn tất. Hỗ trợ cờ `--skip-s2` để bỏ qua hoàn toàn truy vấn S2 trong luồng cào chính, ưu tiên tối đa thông lượng tải arXiv và để dành việc bù trích dẫn sau qua chế độ `--s2-only`.

---

## 2.2. Tổng hợp Công cụ, Thư viện & Kiến trúc Module

Bảng dưới đây đối chiếu bộ công cụ kỹ thuật thực tế được triển khai với các giải pháp trong "hộp công cụ" của đề bài:

| Hạng mục | Công cụ / Thư viện sử dụng | Vai trò & Đánh giá kỹ thuật so với giải pháp khác |
| :--- | :--- | :--- |
| **Khám phá bài báo** | **arXiv Atom API** (`/api/query`) + **OAI-PMH** (`arXivRaw`) + `xml.etree.ElementTree` | Tra cứu theo lô 250 ID gốc kết hợp tối ưu thẻ `<updated>` cho bài 2 bản, bù ngày trung gian $v_2 \dots v_N$ qua OAI-PMH (`--enable-oai-dates`) và kiểm tra nhóm nhỏ 50 ID xác nhận missing. Khám phá 5.000 ID chỉ tốn ~30 request (~1,5 phút). Không dùng Kaggle do chỉ chứa snapshot tĩnh và không hỗ trợ tra cứu ngày sửa đổi theo dải ID rời rạc. |
| **Tải gói mã nguồn** | **`export.arxiv.org/src/`** + `requests` (`urllib3`) | 1 kết nối đơn qua `_SingleConnAdapter` (`TCP_NODELAY = 1`, bảo toàn Linux `tcp_rmem` auto-tuning tới 6 MiB, xoay vòng session mỗi 120 req). Nhịp Start-to-Start $3{,}15\text{ s}$ + jitter $0..0{,}20\text{ s}$, sàn nghỉ socket End-to-Start $3{,}05\text{ s}$, điều tiết **Paced Streaming $4{,}5\text{ MiB/s}$**, đệm nghỉ $3{,}15\text{ s}$, **thử lại Range tại chỗ cho file lớn ($\ge 1\text{ MiB}$) với đệm sạc $12\text{–}14\text{ s}$**, nạp hồi băng thông trượt $50\text{ MiB}$, phản ứng TTFB không tự phạt, Clean Lean Turbo tắt ngủ định kỳ, Hot-Stream Defer, Cooldown leo thang $120 \rightarrow 180 \rightarrow 240\text{ s}$ có trần và đo `download_seconds` thuần wire. |
| **Giải nén & Lọc TeX** | **`_FastGzipStream`** + `tarfile` + `hashlib` | Luồng giải nén 512 KiB với kiểm tra CRC32 ở tầng C (`zlib.decompressobj`), cache thư mục cha `created_dirs`. Trích xuất chọn lọc chỉ giữ **`.tex`, `.bib` và `.bbl`**, băm SHA-256 song song, hoán đổi nguyên tử hai pha và ghi đè POSIX tar an toàn. |
| **Trích xuất tham khảo** | **Semantic Scholar Graph API** (`requests` + `S2_API_KEY`) | Batch mặc định **25 ID** (`POST /paper/batch`) kết hợp tự động chia đôi lô (Bisection) khi gặp lỗi 413/5xx, phân trang `limit=1000`; bộ điều nhịp thích ứng $\ge 1{,}1\text{ s}$ (End-to-Start); dự phòng trích dẫn cục bộ từ `.bib`/`.bbl` khi S2 404 (`--enable-bib-fallback`); hỗ trợ cờ tách luồng `--skip-s2` và chế độ bù offline/online `--s2-only`. |
| **Quản lý trạng thái & Chịu lỗi** | `sqlite3` (WAL mode) + `msvcrt`/`fcntl` | Khóa tiến trình cấp hệ điều hành `_acquire_workspace_lock` (chống chạy trùng 2 crawler trên cùng thư mục `data/`), sổ trạng thái manifest ghi sau cùng, lưu mốc cooldown liên tiến trình `rate_state.json`. |
| **Sao lưu nền & Chống thoái lui** | `checkpoint.py` (`tarfile`, `gzip`) | Chụp ảnh nóng SQLite qua `Connection.backup()`, nén streaming `.tar.gz` ở nền song song với lúc ngủ cooldown 429 hoặc định kỳ mỗi 1.000 ID, kèm `shrink guard` và bỏ qua nén khi dữ liệu không đổi (`skip_if_unchanged=True`). |
| **Đo lường & Phân tích phiên** | `psutil`, `time.perf_counter`, `pyarrow`, `pandas`, `jupyter-book` | Luồng daemon `ResourceSampler` đo RAM RSS mỗi 5 s (truy xuất $O(1)$), bộ lọc bí mật `SecretRedactingFilter`, xuất Parquet chuẩn hóa, bộ tổng hợp đa phiên Colab `summarize_sessions()` bóc tách thời gian thực và thời gian chờ phạt. |

Mã nguồn trong repository [`GiaaPhuc/arxiv-pipeline`](https://github.com/GiaaPhuc/arxiv-pipeline) được tổ chức phân tầng chặt chẽ và bảo vệ bằng **hơn 390 bài kiểm thử đơn vị (unit tests pass 100%)** với `pytest` và fixtures ngoại tuyến:

| Nhóm chức năng | Các module trong `src/` | Trách nhiệm kỹ thuật chính |
| :--- | :--- | :--- |
| **Định danh & Hợp đồng dữ liệu** | `crawler/models.py`, `crawler/ids.py`, `crawler/config.py` | Hợp đồng dữ liệu bất biến (`SCHEMA_VERSION = 1`), chuẩn hóa định danh mới/cũ, mở rộng dải `id_ranges.csv` thành 25.000 ID, nạp cấu hình môi trường. |
| **Giao tiếp mạng & Điều nhịp** | `crawler/http.py`, `crawler/discovery.py`, `crawler/source.py`, `crawler/s2.py` | Quản lý phiên HTTP, bộ điều nhịp Start-to-Start $3{,}15\text{ s} + \text{jitter}$, sàn nghỉ socket End-to-Start $3{,}05\text{ s}$, lưu trạng thái cooldown `rate_state.json`, khám phá Atom lô 250 + OAI-PMH bù ngày, tải đệm RAM 96 MiB, Paced Streaming 4,5 MiB/s, đo timing thuần wire, In-Place Range Resume, Clean Lean Turbo và S2 batch 25 ID kèm bisection. |
| **Điều phối, Hàng đợi & Bền bỉ** | `crawler/pipeline.py`, `crawler/manifest.py`, `crawler/checkpoint.py`, `run_crawl.py` | Điều phối Producer–Consumer đa luồng (5 nhóm luồng), pool 2 luồng `extract-worker`, `s2-worker`, hàng đợi `extract_queue` (trần RAM 192 MiB), `deferred_ids` (tối đa 5 pass), khóa hệ điều hành OS mutex, checkpoint nền `skip_if_unchanged`, chế độ `--skip-s2` và `--s2-only`. |
| **Đo lường, Kiểm định & Xuất bảng** | `crawler/metrics.py`, `corpus.py`, `validate_corpus.py`, `audit_corpus.py`, `enrich_references.py`, `crawler/export.py`, `export_data.py` | Lấy mẫu RAM $O(1)$, che bí mật nhật ký, kiểm tra 5 bất biến toàn vẹn, kiểm toán corpus vs manifest (`audit_corpus.py`), làm giàu trích dẫn offline từ `.bib/.bbl` (`enrich_references.py`), xuất 2 bảng Parquet cho Hugging Face, thống kê `cross_version_dedup` và tổng hợp đa phiên `benchmark_summary`. |
| **Cầu nối Milestone 2** | `parsing/models.py`, `parsing/gathering.py`, `parsing/hierarchy.py`, `parsing/pipeline.py`, `run_parse.py` | Khóa hợp đồng dữ liệu M2 (Phase 0), hiện thực hóa Phase 1C: gom nguồn thông minh khử comment (`gathering.py`), dựng cây phân cấp tài liệu (`hierarchy.py`) và khung điều phối phân tích cú pháp đa nhân. |

````{admonition} Lệnh Vận hành Nhanh của Pipeline Thu thập (Quick Reference)
:class: tip

```bash
# 1. Chạy thử nghiệm Pilot (30 ID đầu dải)
python src/run_crawl.py --ranges src/id_ranges.csv --limit 30 --data-dir data --auto-resume-rate-limit

# 2. Chạy thu thập thực tế toàn bộ dải ID (kèm sao lưu định kỳ, tự vượt 429 & bù trích dẫn/ngày)
python src/run_crawl.py \
  --ranges src/id_ranges.csv \
  --data-dir data \
  --backup-dir /path/to/drive/arxiv-data.tar.gz \
  --backup-every-ids 1000 \
  --auto-resume-rate-limit \
  --enable-bib-fallback \
  --enable-oai-dates

# 3. Cào bù trích dẫn Semantic Scholar hoặc làm giàu offline từ .bib/.bbl
python src/run_crawl.py --ranges src/id_ranges.csv --data-dir data --s2-only --enable-bib-fallback
python src/enrich_references.py --data-dir data

# 4. Kiểm toán kho dữ liệu trên đĩa vs manifest và kiểm tra toàn vẹn xuất thống kê
python src/audit_corpus.py --data-dir data --output data/stats/audit_report.json
python src/validate_corpus.py --data-dir data
python src/export_data.py --data-dir data --out-dir data/stats
```
````

---

## 2.3. Chính sách Lịch sự Máy chủ, Chịu lỗi & Kiểm chứng Dữ liệu

Vận hành thu thập quy mô lớn trên Google Colab đòi hỏi sự cân bằng tuyệt đối giữa **chuẩn lịch sự máy chủ học thuật** và **khả năng chịu lỗi tự động 100%**:

1. **Chuẩn lịch sự Start-to-Start $\ge 3{,}0\text{ s}$, Sàn nghỉ socket $3{,}05\text{ s}$ & Tản nhiệt IP thích ứng (`http.py`, `pipeline.py`):**
   - Bộ điều nhịp `RateLimiter` duy trì nhịp cơ sở **Start-to-Start $3{,}15\text{ s}$** kèm **Jitter ngẫu nhiên $0 \dots 0{,}20\text{ s}$** trên 1 kết nối duy nhất tới `export.arxiv.org`.
   - **Sàn nghỉ socket (End-to-Start):** `arxiv_min_idle_gap = 3{,}05\text{ s}`. Bất kể gói trước tải nhanh hay chậm, crawler **luôn đảm bảo socket nghỉ tối thiểu 3,05s** từ thời điểm đóng socket trước đến khi gửi request tiếp theo. Do $3{,}05\text{ s} > 3{,}00\text{ s}$, crawler tuyệt đối không bao giờ vi phạm quy định $\ge 3\text{ s}$ của arXiv kể cả sau các gói tải siêu nhanh. Khi dính 429 hoặc cảnh báo nhiệt, sàn nghỉ tự động co giãn tỷ lệ theo khoảng nghỉ để socket luôn có khoảng đệm làm nguội thực tế.
   - **Phân cấp đệm nghỉ theo dung lượng (Tránh cạn Token Bucket):** Gói thông thường (< 2 MiB, ~85% kho bài) tuân thủ nhịp cơ sở. Gói trung bình & lớn ($\ge 2\text{ MiB}$ hoặc truyền socket $\ge 2{,}5\text{ s}$ hoặc có nối Range) áp dụng đệm nghỉ lịch sự chuẩn `3,15 s` End-to-Start (xóa bỏ hình phạt 6,0s thừa thãi của bản cũ).
   - **Nạp hồi băng thông trượt (Mỗi 50 MiB):** Sau mỗi 50 MiB dữ liệu tải thực qua mạng (`_BANDWIDTH_WINDOW_MAX_BYTES = 50 MiB`), crawler chủ động xoay vòng TCP session (`recycle_session()`) và nghỉ `12,0 s` để làm mới hạn mức burst của CDN Fastly khi gặp chùm bài khổng lồ liên tiếp.
   - **Phản ứng trễ mạng (TTFB v3.10 Clean Lean Turbo):** Khi header phản hồi bị trễ `last_header_elapsed >= 3.5s`, crawler xoay vòng session làm mới TCP, **tuyệt đối không gọi `note_429()` trên mã 200 OK** (không tự phạt chính mình, giữ nguyên nhịp 3,15s).
   - **Tản nhiệt chủ động thông minh:** Đặt mặc định `arxiv_proactive_cooldown_every_ids = 0` (tắt tự động ngủ 60s định kỳ sau mỗi 300 ID; chỉ ngủ khi arXiv thực sự trả về 429), giúp xóa bỏ hơn 40 phút ngủ tự nguyện lãng phí trên dải 5.000 ID.
2. **Điều tiết Paced Streaming, Thử lại Range tại chỗ & Phục hồi sự cố đa tầng (`source.py`, `pipeline.py`):**
   - **Điều tiết Paced Streaming (4,5 MiB/s):** Với các gói tải $\ge 512\text{ KiB}$, tốc độ đọc socket được điều hòa ở mức **$4{,}5\text{ MiB/s}$** (`_MAX_SUSTAINED_STREAM_BPS`). Mức tốc độ này giúp các bài lớn 20–40 MB tải nhanh gấp 3 lần so với mức 1,5 MB/s trước đây mà vẫn triệt tiêu hoàn toàn xung nhịp bộc phát, bảo vệ Token Bucket của Fastly CDN edge không bị tràn buffer.
   - **Thử lại Range tại chỗ cho file lớn (In-Place Multi-Slice Range Resume v3.9.9 / v3.11.1):** Khi gặp sự cố đứt stream trên file lớn ($\ge 1\text{ MiB}$), crawler tự động xoay vòng session mới (`recycle_session()`), áp dụng đệm nghỉ an toàn $\ge \mathbf{12{,}0\text{ s} - 14{,}0\text{ s}}$ (`_HEAVY_STREAM_BREAK_BONUS = 9.0s`) để token bucket Fastly nạp đầy, rồi gửi ngay header `Range: bytes={written}-` (`HTTP 206 Partial Content`). Nhờ đó các bài dung lượng lớn 20–40 MB hoàn tất sau 2 slice ngay tại chỗ trong ~13,5s mà không bị Fastly trả 429 hay phải dồn toa về cuối dải.
   - **Bảo toàn byte tải dở (Zero-Loss Range Resume):** Toàn bộ byte đã tải được bảo lưu an toàn trong `.resume-{id}-v{version}.part`. **Tuyệt đối không xóa `.part` khi gặp HTTP 429** (429 là giới hạn tần suất, không phải từ chối Range); chỉ xóa khi nhận mã 403 hoặc 416.
   - **Tách bạch đứt stream khỏi chuỗi phạt 429:** Đứt luồng do socket Fastly ngắt kết nối (`ChunkedEncodingError`) sau khi đã thử lại tại chỗ được lưu an toàn vào `.part` và **defer bài báo về cuối dải (0s chờ phạt)**, tiếp tục cào ngay bài tiếp theo (`need_cd = False`). Nếu request Range dở dang gặp mã 429, hệ thống nhận diện `is_stream_break` để cách ly: chỉ ngủ breather cố định 60s, **tuyệt đối không tăng `arxiv_429_streak` leo thang**. Chỉ khi có $\ge 2$ bài liên tiếp bị đứt stream thì hệ thống mới ngủ breather cố định 60s để ổn định mạng mà không tăng streak.
   - **Xử lý HTTP 429 & Cooldown leo thang có khóa trần:** Khi gặp mã HTTP 429 trên `/src/`, bài báo được đẩy ngay vào `deferred_ids`, đóng socket cũ qua `recycle_session()`. Hệ thống ngủ **Cooldown leo thang có giới hạn: `120 s &rarr; 180 s &rarr; 240 s`** (khóa trần tối đa 240 giây, loại bỏ hoàn toàn các mức ngủ sâu kéo dài 600s). Sau khi thức dậy, hệ thống chỉ hạ 1 bậc streak sau **6 bài liên tiếp tải thành công (200 OK)**.
   - **Quét vét cuối dải (`deferred_ids`):** Sau khi hoàn tất danh sách chính, crawler duyệt lại các bài trong hàng đợi hoãn (tối đa 5 vòng), tiếp tục tải phần còn lại qua `HTTP 206 Range` khi endpoint đã nguội hoàn toàn.
3. **Cơ chế Semantic Scholar thông minh & Dự phòng trích dẫn kép (Dual-Engine Fallback):**
   - **Gom lô 25 bài & Chia đôi đệ quy (Bisection):** Sử dụng `POST /graph/v1/paper/batch` với kích thước 25 bài/lô. Khi gặp `HTTP 413 Payload Too Large` hoặc lỗi tạm thời `5xx` trên mẻ có $\ge 2$ bài, hệ thống tự động chia đôi mẻ ($N/2$) và gửi đệ quy nhằm cô lập bài báo có danh sách trích dẫn khổng lồ mà không làm thất bại cả mẻ.
   - **Phân trang trích dẫn:** Khi `referenceCount > len(references)`, hệ thống tự động gọi phân trang `GET /references?limit=1000` để lấy trọn vẹn 100% trích dẫn.
   - **Dự phòng trích dẫn nội bộ (Dual-Engine Reference Fallback):** Khi Semantic Scholar chưa lập chỉ mục bài báo (`HTTP 404`), crawler tự động bóc tách trích dẫn từ các tệp `.bib` và `.bbl` có sẵn trong thư mục mã nguồn bài viết khi kích hoạt cờ `--enable-bib-fallback` (hoặc chạy ngoại tuyến qua `src/enrich_references.py`).
   - **Tách luồng linh hoạt (`--skip-s2` / `--s2-only`):** Hỗ trợ cờ `--skip-s2` để bỏ qua hoàn toàn truy vấn S2 trong luồng cào chính trong giờ cao điểm nhằm dồn băng thông cào gói arXiv nhanh nhất, và để dành việc bù trích dẫn sau qua chế độ `--s2-only`.
4. **Khóa tiến trình cấp hệ điều hành OS Mutex & Checkpoint nền thông minh (`pipeline.py`, `checkpoint.py`):**
   - Hàm `_acquire_workspace_lock` sử dụng cơ chế khóa tệp cấp nhân hệ điều hành (`msvcrt.locking` trên Windows, `fcntl.flock` trên Linux) tại thư mục tạm hệ thống, ngăn chặn triệt để lỗi người dùng mở trùng 2 tiến trình crawler ghi đè lên cùng thư mục `data/`.
   - File `data/logs/rate_state.json` lưu trữ mốc thời gian phạt còn dư (`arxiv_cooldown_until`, `s2_cooldown_until`) giúp bảo toàn trạng thái phạt liên tiến trình.
   - Luồng `checkpoint-worker` chụp snapshot SQLite bằng `Connection.backup()` và nén streaming sang `arxiv-data.tar.gz` ở nền song song (trong lúc ngủ cooldown hoặc định kỳ mỗi 1.000 ID), hoàn toàn không chặn luồng tải chính. Bản backup mới được bảo vệ bởi tệp sidecar `.meta.json` (chống thoái lui `shrink protection` và bỏ qua nén khi dữ liệu không đổi `skip_if_unchanged=True`).
5. **Kiểm chứng toàn vẹn hậu thu thập (`validate_corpus.py`, `audit_corpus.py`) & Hợp đồng dữ liệu đa Milestone:**
   - Trình kiểm định độc lập quét toàn bộ kho để xác nhận 5 bất biến: *(i)* đủ thư mục phiên bản liên tục `v1..vN`; *(ii)* không tồn tại tệp lạ ngoài siêu dữ liệu chuẩn và `.tex`/`.bib`/`.bbl`; *(iii)* khớp 100% dung lượng và mã băm `SHA-256` với `meta.json`; *(iv)* manifest nhất quán với đĩa và không còn bản ghi `pending`; *(v)* hai bảng Parquet tuân thủ đúng khóa không rỗng.
   - Module `audit_corpus.py` kiểm toán đối chiếu chi tiết giữa cây thư mục trên đĩa và bảng `version_pairs` trong `manifest.sqlite`, xuất báo cáo JSON định lượng trạng thái kho dữ liệu.
   - **Ghi nhận về đặc thù dữ liệu thượng nguồn và chuẩn bị cho Milestone 2:**
     1. *Phạm vi phiên bản trên S2 (`s2_scope = "paper"`):* Semantic Scholar lập chỉ mục danh sách tham khảo ở cấp bài báo gốc (`ARXIV:<base_id>`) thay vì từng phiên bản riêng biệt; do đó danh sách tham khảo phản ánh phiên bản mới nhất được S2 lập chỉ mục.
     2. *Dual-Engine Fallback cho bài chưa có trên S2:* Tận dụng các tệp `.bib` và `.bbl` có sẵn trong thư mục mã nguồn bài viết để trích xuất danh sách trích dẫn cho những bài S2 trả về null/404.
     3. *Giữ lại tệp danh mục tham khảo biên dịch sẵn `.bbl`:* Khác với quy định ban đầu chỉ giữ `.tex` và `.bib`, nhóm đã bổ sung chính sách trích xuất giữ lại các tệp `.bbl` (danh mục tài liệu tham khảo đã được LaTeX biên dịch hoàn chỉnh) nhằm cung cấp thêm căn cứ đối sánh trích dẫn quan trọng cho bộ phân tích cú pháp ở Milestone 2.
