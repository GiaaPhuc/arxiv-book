# Chương 2. Quá trình Triển khai & Công cụ Sử dụng

## 2.1. Quy trình Thu thập Đầu–Cuối (End-to-End Pipeline)

Khác với các bộ thu thập tuần tự đơn luồng truyền thống (dễ bị nghẽn I/O đĩa hoặc mất thời gian chờ mạng vô ích), hệ thống `arxiv-pipeline` được thiết kế theo kiến trúc **Producer–Consumer Đa luồng Tối ưu** kết hợp **Quy trình 2 giai đoạn tách rời (`Two-Stage Decoupled Protocol` — kiến trúc `v3.18`)**. Trong đó, **Giai đoạn 1** ưu tiên khám phá ngoại tuyến qua Kaggle snapshot (`--snapshot` trong `< 60 s`) kết hợp `--skip-s2` để dồn toàn bộ băng thông mạng cho `export.arxiv.org` trên **1 kết nối tuần tự duy nhất** (`--http2` `httpx[http2]` hoặc HTTP/1.1 Keep-Alive): nhịp **Start-to-Start $3{,}05\text{ s} + \text{jitter } 0\dots 0{,}10\text{ s}$** kèm đệm hậu tải $0{,}25\text{ s}$, **Zero-Body `Content-Type` Header Early-Reject (`wire_bytes = 0`)**, dòng tải mượt `--max-stream-mbps = 6,0 MiB/s` và **Deficit Breather** (trần $6{,}0\text{ s}$), giải nén **Cut-Through In-Flight `O(1)` RAM (`--in-flight-extract`)** song hành cùng **Traffic-Shaping Interleaver & Leaky Byte-Budget `360 MiB / 180 s`** và **CDN-Aware Self-Healing**. Ở **Giai đoạn 2 (`--s2-only`)**, crawler chạy độc lập **Semantic Scholar High-Density Batch (`150` bài/lô)**, Auto-Bisection mở rộng (`400`/`413`/`5xx`/`>= 9.500` refs), **Save-First Isolation**, lọc false-positive `/references`, **Fast S2 Backoff (`2→4→8→15 s`) + AIMD**, và tùy chọn dự phòng `.bib/.bbl` khi S2 `404`:

<div class="pipeline-flow" role="region" aria-label="Sơ đồ Quy trình Thu thập Đầu–Cuối v3.18">
  <div class="pf-endpoint-node pf-input">
    <span class="pf-icon">&#128196;</span>
    <span>Dải 25.000 ID (<code>src/id_ranges.csv</code>) &rarr; Khóa OS Mutex (<code>_acquire_workspace_lock</code>) &amp; Preflight POP (<code>preflight.py</code>)</span>
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
        <span>1. Giai đoạn Khám phá Siêu dữ liệu &amp; Cấu trúc Phiên bản (Discovery Stage)</span>
      </div>
      <span class="pf-rate-badge">Luồng chính: --snapshot (&lt; 60s offline) &middot; Dự phòng: Atom API + OAI-PMH</span>
    </div>
    <div class="pf-steps-grid">
      <div class="pf-step-item">
        <span class="pf-step-num">1A</span>
        <div class="pf-step-body">
          <strong>Luồng chính: Có cờ <code>--snapshot</code> (Fast Path)</strong>
          <span>Đọc streaming <code>arxiv-metadata-oai-snapshot.json</code> &rarr; lọc 25.000 ID offline &lt; 60s &rarr; phân loại <code>v1</code> vs <code>v2..vN</code> &rarr; ghi sẵn <code>paper.json</code> &amp; <code>version_partition.json</code> (0 request mạng, 0% rủi ro 429)</span>
        </div>
      </div>
      <div class="pf-step-item">
        <span class="pf-step-num">1B</span>
        <div class="pf-step-body">
          <strong>Luồng dự phòng trực tuyến (Online Fallback)</strong>
          <span>Khi không có snapshot &rarr; duyệt lô 250 ID qua Atom API (<code>/api/query</code>) &rarr; tận dụng <code>&lt;updated&gt;</code> cho bài 2 bản &rarr; bù ngày trung gian <code>v2..vN</code> qua OAI-PMH <code>arXivRaw</code> (<code>--enable-oai-dates</code>) &rarr; xác nhận thiếu lô 50 ID</span>
        </div>
      </div>
    </div>
  </div>
  <div class="pf-connector" aria-hidden="true">
    <svg width="20" height="16" viewBox="0 0 20 16" fill="none">
      <line x1="10" y1="0" x2="10" y2="16" stroke="currentColor" stroke-width="1.8" stroke-dasharray="3 3"/>
    </svg>
    <div class="pf-queue-pill">
      <span>&#8645; Danh sách các cặp phiên bản (arxiv_id, version) &rarr; Hoán vị tỷ lệ vàng &amp; Hàng đợi xen kẽ bài nặng</span>
    </div>
    <svg width="20" height="22" viewBox="0 0 20 22" fill="none">
      <line x1="10" y1="0" x2="10" y2="15" stroke="currentColor" stroke-width="1.8"/>
      <path d="M5 12L10 19L15 12" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
  </div>
  <div class="pf-stage-card pf-stage-arxiv">
    <div class="pf-stage-header">
      <div class="pf-stage-title">
        <span class="pf-stage-dot"></span>
        <span>2. MainThread — Tải Gói Nguồn TeX (arXiv Network Producer — v3.15–v3.17.1)</span>
      </div>
      <span class="pf-rate-badge">1 kết nối (HTTP/2 hoặc H1.1) &middot; Start-to-Start 3,05s + jitter &middot; Idle gap 0,25s</span>
    </div>
    <div class="pf-steps-grid">
      <div class="pf-step-item">
        <span class="pf-step-num">2</span>
        <div class="pf-step-body">
          <strong>Zero-Body Header Early-Reject &amp; Keep-Alive</strong>
          <span>Ngắt PDF/ZIP từ <code>Content-Type</code> với <code>wire_bytes=0</code> (<code>RST_STREAM</code> trên HTTP/2); dự phòng 512B magic; giữ ấm TCP <code>500</code> req (xoay khi &ge;50 MiB / TTFB &ge;5s)</span>
        </div>
      </div>
      <div class="pf-step-item">
        <span class="pf-step-num">3</span>
        <div class="pf-step-body">
          <strong>Paced 6,0 MiB/s &amp; Deficit Breather</strong>
          <span><code>--max-stream-mbps 6.0</code>; bù thiếu hụt <code>max(0, S/6 - elapsed)</code> (trần 6s); bỏ ngủ cứng <code>50 MiB &rarr; 12s</code>; đo <code>download_seconds</code> &amp; <code>X-Cache</code></span>
        </div>
      </div>
      <div class="pf-step-item">
        <span class="pf-step-num">4</span>
        <div class="pf-step-body">
          <strong>Traffic-Shaping &amp; Leaky Byte-Budget</strong>
          <span>Đảo chunk &ge;16 ID; xen kẽ <code>v2..vN</code> &ge;25 MiB cách 15 bản nhẹ; ngưỡng <code>220/360 MiB / 180s</code> ngủ sau enqueue; Defensive Soft-Pacing khi <code>HIT &lt; 3,0 MiB/s</code></span>
        </div>
      </div>
      <div class="pf-step-item">
        <span class="pf-step-num">5</span>
        <div class="pf-step-body">
          <strong>Cut-Through In-Flight &amp; Range Resume</strong>
          <span><code>--in-flight-extract</code> giải nén trực tiếp socket <code>O(1)</code> RAM; đứt luồng lùi về <code>HTTP 206 Range</code> từ <code>.part</code> ở lượt deferred; Cooldown <code>120&rarr;180&rarr;240s</code></span>
        </div>
      </div>
    </div>
  </div>
  <div class="pf-connector" aria-hidden="true">
    <svg width="20" height="16" viewBox="0 0 20 16" fill="none">
      <line x1="10" y1="0" x2="10" y2="16" stroke="currentColor" stroke-width="1.8" stroke-dasharray="3 3"/>
    </svg>
    <div class="pf-queue-pill">
      <span>&#8645; Đẩy gói vào <code>extract_queue</code> (RAM &le; 192 MiB) hoặc chuyển <code>prefilled_meta</code> (Cut-Through)</span>
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
        <span>3. Pool extract-worker (2 luồng) — CPU &amp; Disk Consumer (Giải nén &amp; Ghi nguyên tử)</span>
      </div>
      <span class="pf-rate-badge">Đa nhân cục bộ &middot; _FastGzipStream 512 KiB / Cut-Through 128 KiB &middot; 0 ảnh nhị phân</span>
    </div>
    <div class="pf-steps-grid">
      <div class="pf-step-item">
        <span class="pf-step-num">6</span>
        <div class="pf-step-body">
          <strong>Giải nén 1-pass tốc độ cao</strong>
          <span><code>_FastGzipStream</code> 512 KiB (hoặc Cut-Through 128 KiB trên luồng mạng); giải mã zlib &amp; kiểm tra CRC32/ISIZE ở tầng C</span>
        </div>
      </div>
      <div class="pf-step-item">
        <span class="pf-step-num">7</span>
        <div class="pf-step-body">
          <strong>Lọc mã nguồn chọn lọc &amp; Cache thư mục</strong>
          <span>Chỉ giữ <code>.tex</code>, <code>.bib</code>, <code>.bbl</code>; bỏ ảnh nhị phân &amp; file rác; chống path traversal / tên thiết bị Windows; cache <code>created_dirs</code></span>
        </div>
      </div>
      <div class="pf-step-item">
        <span class="pf-step-num">8</span>
        <div class="pf-step-body">
          <strong>Ghi nguyên tử &amp; Cập nhật Manifest sau cùng</strong>
          <span>Ghi <code>.vK.part/</code> &rarr; băm SHA-256 song song &rarr; <code>os.replace</code> sang <code>vK/</code> &rarr; ghi <code>manifest.sqlite</code> sau cùng</span>
        </div>
      </div>
      <div class="pf-step-item">
        <span class="pf-step-num">9</span>
        <div class="pf-step-body">
          <strong>Điều phối bài hoàn tất nguyên tử</strong>
          <span>Bộ đếm <code>paper_pending_versions == 0</code> &rarr; chỉ khi toàn bộ phiên bản xong mới đẩy sang Giai đoạn 2 làm giàu</span>
        </div>
      </div>
    </div>
  </div>
  <div class="pf-connector" aria-hidden="true">
    <svg width="20" height="16" viewBox="0 0 20 16" fill="none">
      <line x1="10" y1="0" x2="10" y2="16" stroke="currentColor" stroke-width="1.8" stroke-dasharray="3 3"/>
    </svg>
    <div class="pf-queue-pill">
      <span>&#8645; Đẩy bài hoàn tất nguồn sang làm giàu trích dẫn (<code>s2_queue</code> / Giai đoạn 2 <code>--s2-only</code>)</span>
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
        <span>4. Giai đoạn 2 — s2-worker &amp; Luồng Dịch vụ Nền (v3.18 S2 High-Density, Checkpoint, Sampler)</span>
      </div>
      <span class="pf-rate-badge">AIMD &ge; 1,1s &middot; Gom lô 150 bài &middot; Save-First &middot; Backoff 2&rarr;4&rarr;8&rarr;15s</span>
    </div>
    <div class="pf-steps-grid pf-steps-3">
      <div class="pf-step-item">
        <span class="pf-step-num">10</span>
        <div class="pf-step-body">
          <strong>Lô 150 ID, Bisection &amp; Diệt False-Positive</strong>
          <span><code>POST /paper/batch</code> (150 bài, ~3,9 MB); chia đôi <code>400/413/5xx/&ge;9500 refs</code>; Save-First lưu ngay bài xong; siết <code>_references_truncated()</code></span>
        </div>
      </div>
      <div class="pf-step-item">
        <span class="pf-step-num">11</span>
        <div class="pf-step-body">
          <strong>Minh bạch 404 &amp; Dự phòng tùy chọn</strong>
          <span>S2 <code>404</code> ghi <code>not_indexed</code> để tách bạch độ phủ API; tùy chọn <code>--enable-bib-fallback</code> / <code>enrich_references.py</code> tách nguồn <code>local_bib</code></span>
        </div>
      </div>
      <div class="pf-step-item">
        <span class="pf-step-num">12</span>
        <div class="pf-step-body">
          <strong>Vét Deferred, Sao lưu &amp; Viễn trắc</strong>
          <span><code>--s2-only</code> tự vét tối đa 2 vòng + checkpoint định kỳ; <code>checkpoint-worker</code> nén <code>.tar.gz</code>; <code>ResourceSampler</code> đo RAM/Đĩa <code>O(1)</code></span>
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

### Bước 1 — Khám phá siêu dữ liệu bài báo & lịch sử phiên bản (`snapshot.py`, `discovery.py`)

Khám phá siêu dữ liệu là bước tiên quyết để xác định tính tồn tại của bài báo, các trường thư mục học thuật (tiêu đề, tác giả, ngày nộp, venue) và danh sách đầy đủ các phiên bản ($v_1 \dots v_N$) cần thu thập. Tuân thủ hướng dẫn thiết kế xem ba phương thức truy cập trong đề bài (arXiv Atom API, OAI-PMH và Kaggle Dataset) như **một hộp công cụ bổ trợ lẫn nhau**, hệ thống kết hợp ưu thế $\mathcal{O}(1)$ lượt gọi mạng của Kaggle Snapshot với Atom API và OAI-PMH cho kiểm chứng trực tuyến và khôi phục ngày sửa đổi:

1. **Luồng chính (Có cờ `--snapshot` — Khám phá ngoại tuyến qua Kaggle snapshot `snapshot.py`):**
   - **Tận dụng bộ dữ liệu chính thức arXiv Kaggle:** Thay vì gửi hàng trăm yêu cầu qua mạng, crawler kích hoạt cờ `--snapshot <path>` trỏ tới tệp `arxiv-metadata-oai-snapshot.json` (bộ siêu dữ liệu toàn diện được arXiv công bố và cập nhật định kỳ trên Kaggle).
   - **Đọc dạng dòng (Streaming JSONLines) siêu tốc:** Module `src/crawler/snapshot.py` duyệt tệp theo luồng và lọc 25.000 định danh theo dải trong **chưa đầy 60 giây** mà **không tốn một lượt gọi mạng nào** (0 request API, 0% nguy cơ gặp mã lỗi HTTP 429, triệt tiêu hoàn toàn độ trễ mạng).
   - **Trích xuất trọn vẹn lịch sử phiên bản:** Tệp snapshot Kaggle chứa sẵn toàn bộ mốc thời gian nộp của từng phiên bản trong trường `versions`, cho phép bóc tách chính xác `submission_date` của bản gốc $v_1$ và danh sách `revised_dates` của mọi bản sửa đổi $v_2 \dots v_N$ mà không lo bị khuyết ngày trung gian.
   - **Phân loại cấu trúc phiên bản & Lưu trữ nguyên tử:** Ghi sẵn tệp `data/papers/<dirname>/paper.json` theo chuẩn `PaperMeta` (`SCHEMA_VERSION = 1`) và xuất thống kê phân tầng `v1` duy nhất vs đa phiên bản ra `data/logs/version_partition.json` (trên 25.000 ID thực tế ghi nhận **14.160 bài (56,64%)** có đúng 1 phiên bản `v1` và **10.840 bài (43,36%)** đa phiên bản $v_2 \dots v_{30}$).

2. **Luồng dự phòng trực tuyến (Không có cờ `--snapshot` — Atom API & OAI-PMH `discovery.py`):**
   - **Tra cứu theo lô 250 định danh gốc:** Khi không có sẵn tệp snapshot Kaggle, crawler duyệt dải ID theo từng chunk 500 ID và gửi yêu cầu `id_list` gồm tối đa **250 định danh** mỗi lượt tới `https://export.arxiv.org/api/query` (tiết kiệm gấp 5 lần số request Atom API so với lô 50 thông thường).
   - **Tận dụng thẻ `<updated>` & Bù ngày trung gian qua OAI-PMH (`--enable-oai-dates`):** Với bài $N = 2$ phiên bản, thẻ `<updated>` trong entry Atom chính là ngày nộp của $v_2$. Với bài $N \ge 3$ phiên bản, cờ `--enable-oai-dates` kích hoạt truy vấn OAI-PMH (`https://oaipmh.arxiv.org/oai`, định dạng `arXivRaw`) để khôi phục ngày sửa đổi trung gian $v_2 \dots v_{N-1}$, bảo đảm `len(paper.revised_dates) == paper.num_versions - 1`.
   - **Xác nhận định danh vắng mặt theo nhóm nhỏ 50 ID:** Bất kỳ ID nào không xuất hiện trong lô 250 được kiểm tra lại theo cụm nhỏ **50 ID** (`_CONFIRM_BATCH_SIZE = 50`). Chỉ khi lần thứ hai này vẫn không tìm thấy, định danh đó mới được ghi nhận là `not_found` (với $v=1$) trong manifest mà không tạo thư mục rác trên đĩa.

### Bước 2 — Tải gói nguồn, điều tiết lưu lượng & giải nén tối ưu (`http.py`, `source.py`, `pipeline.py`)

Với mỗi bài báo hợp lệ, `MainThread` duyệt tuần tự từng phiên bản $v_1 \dots v_N$ qua `https://export.arxiv.org/src/{id}vK` trên **một kết nối duy nhất** (tuyệt đối không mở đa luồng tải song song lên máy chủ arXiv) và kết hợp **6 cơ chế tối ưu của `v3.15–v3.17.1`**:

1. **Transport HTTP/2 Kết nối đơn & Keep-Alive bền vững (`v3.15–v3.16`):**
   - Hỗ trợ tùy chọn `--http2` (`CRAWLER_USE_HTTP2=1`) qua `httpx[http2]` khóa nghiêm ngặt `Limits(max_connections=1, max_keepalive_connections=1)` đọc luồng wire thô bằng `iter_raw`; nếu môi trường thiếu thư viện `h2`/`httpx`, hệ thống tự động hạ cấp an toàn về HTTP/1.1 `_SingleConnAdapter(pool_connections=1, pool_maxsize=1)` với `TCP_NODELAY = 1` (bảo toàn Linux `tcp_rmem` auto-tuning tới `6 MiB`).
   - Nâng chu kỳ giữ ấm kết nối Keep-Alive từ `120` lên **`500` request** (`recycle_session()` gom tối đa `1` lần mỗi request), chỉ chủ động làm mới phiên kết nối khi gặp gói khổng lồ **`>= 50 MiB`**, khi `TTFB >= 5,0 s` (tránh tarpit kết nối, tuyệt đối không tự phạt `note_429()` trên mã `200 OK`), khi vượt ngân sách byte trượt, hoặc khi gặp lỗi đứt luồng/`429`.

2. **Zero-Body `Content-Type` Header Early-Reject (`v3.16`):**
   - Ngay khi nhận HTTP response header từ `/src/{id}vK`, nếu trường `Content-Type` khai báo `application/pdf` hoặc `application/zip` (kèm `Content-Length`), crawler ngắt bỏ luồng ngay lập tức với **`wire_bytes = 0`** (`Status.NO_SOURCE`, `early_rejected_by_header = True`). Trên kết nối HTTP/2, lệnh `.close()` phát khung `RST_STREAM` hủy riêng stream đó mà vẫn giữ nguyên kết nối TCP/TLS chung.
   - Cơ chế kiểm tra magic bytes ở **512 bytes đầu tiên** (`%PDF`, `PK`) vẫn được giữ làm lớp bảo vệ thứ hai khi máy chủ không trả `Content-Type` tường minh.

3. **Nhịp độ lai Start-to-Start `3,05 s` + Đệm hậu tải `0,25 s` & Deficit Breather (`v3.15`):**
   - *Lý giải thiết kế lai cho cả gói nhỏ lẫn gói nặng:* Trước thực nghiệm, một câu hỏi quan trọng được đặt ra là nên đo khoảng nghỉ `>= 3 s` từ lúc kết thúc tải gói trước (*End-to-Start*) hay từ lúc bắt đầu gửi request (*Start-to-Start*), và thiết kế cơ chế linh hoạt ra sao cho cả gói nhẹ lẫn gói nặng. Kết quả đối chứng trên 6 phiên chạy Colab cho thấy việc áp cứng End-to-Start `min_idle_gap = 3,05–3,25 s` lên mọi gói nhỏ cộng dồn thời gian đọc mạng vào chu kỳ chờ, làm mất thêm `~4,5 giờ / 5.000 ID` dù băng thông rất nhẹ; đồng thời cơ chế ngủ cứng `12,0 s` sau mỗi `50 MiB` gây gián đoạn không cần thiết.
   - *Thiết kế thích ứng hai chế độ hiện hành:* Hệ thống đặt nhịp chuẩn **Start-to-Start `arxiv_min_interval = 3,05 s + jitter (0..0,10 s)`** (trung bình `~3,10 s`, luôn $\ge 3{,}00\text{ s}$ theo đúng chuẩn arXiv & `arxiv.py`), đi kèm đệm hậu tải nhẹ **`arxiv_min_idle_gap = 0,25 s`** và giới hạn luồng tải mượt `--max-stream-mbps = 6,0 MiB/s` (đọc không giới hạn với `<= 512 KiB`, điều tiết mượt trên `512 KiB`):
     - *Với gói nhỏ và vừa ($\le 18\text{ MiB}$, tải xong trong $\le 2{,}80\text{ s}$):* Khoảng chờ Start-to-Start $3{,}05\text{–}3{,}15\text{ s}$ tự động đảm bảo khe nghỉ hậu tải thực tế mà không tốn thời gian chờ cộng dồn thừa.
     - *Với gói lớn tải quá nhanh hoặc khi CDN chớm nghẽn:* Hàm `_compute_proportional_breather` tự động bù đúng phần thời gian thiếu hụt:
       $$\text{breather} = \min\!\left(6{,}0,\; \max\!\left(0,\; \frac{S}{6{,}0\text{ MiB/s}} - (\text{TTFB} + \text{download\_seconds})\right)\right)$$
       Nếu đường truyền đang chậm sẵn ($\le 6{,}0\text{ MiB/s}$), breather bằng `0 s`. Khi băng thông `HIT` thuần của Fastly suy giảm dưới `3,0 MiB/s` trên $\ge 20\text{ MiB}$, crawler tự kích hoạt **Defensive Soft-Pacing** (`3,80–4,50 s` trong `50` request) — đạt trọn hiệu quả chống `429`/retry của End-to-Start trên các gói nặng.

4. **Traffic-Shaping Interleaver & Leaky Byte-Budget Governor (`v3.17–v3.17.1`):**
   - Nhằm triệt tiêu hiện tượng một chùm bài nặng `Cache MISS` liên tiếp làm cạn Token Bucket của Fastly CDN (đẩy tốc độ tụt từ `7,3 MiB/s` xuống `2,5 MiB/s`), `traffic_shaping=True` (bật mặc định, tắt bằng `--no-traffic-shaping`) phối hợp 3 lớp:
     1. *Block-Stride De-clustering:* Trong mỗi chunk $\ge 16$ ID, hoán vị thứ tự bài theo bước nhảy tỷ lệ vàng nguyên tố cùng nhau (`0,618...`) để rải đều các bài nặng nộp cùng ngày.
     2. *Heavy-Version Interleaving:* Khi bất kỳ phiên bản nào đạt $\ge 25\text{ MiB}$, các phiên bản còn lại (`v2..vN`) của bài đó được đẩy vào `heavy_interleave_queue` (trần `32`), xen tối thiểu `15` phiên bản nhẹ trước khi rút tiếp (hoặc `3` phiên bản nhẹ dưới áp lực cao khi cửa sổ byte dưới trần đỏ), và xả round-robin theo từng bài ở cuối pass.
     3. *Leaky Sliding-Window Byte-Budget (`180 s`):* Giám sát tổng byte truyền tải trong cửa sổ trượt `180 s`: ngưỡng vàng `220 MiB` tạm giữ hàng đợi bài nặng; ngưỡng đỏ `360 MiB` (chỉ áp dụng cho gói $\ge 1\text{ MiB}$) xoay session và ngủ hồi phục `10–60 s` **sau** khi đã gọi `_enqueue_extract_job()` (để pool `extract-worker` vẫn giải nén song song trong lúc luồng mạng nghỉ), rồi khấu trừ `breather * 2,0 MiB/s` từ các mẫu cũ nhất.

5. **Nối tiếp `HTTP 206 Range` tại chỗ, Cooldown khóa trần & CDN-Aware Self-Healing:**
   - Khi gặp sự cố đứt stream (`ChunkedEncodingError`) trên tệp lớn ($\ge 1\text{ MiB}$), crawler xoay session, nghỉ sạc Token Bucket `12,0–14,0 s` (`_HEAVY_STREAM_BREAK_BONUS = 9,0 s`) và gửi `Range: bytes={written}-` (`HTTP 206 Partial Content`), bảo toàn byte dở trong `.resume-{id}-v{K}.part` (tuyệt đối không xóa `.part` khi gặp `429`, chỉ xóa khi `403`/`416`). Đứt luồng chưa khắc phục được sau thử tại chỗ sẽ defer về cuối pass (`0 s` phạt nếu chưa liên tiếp) và tách riêng `is_stream_break` (breather cố định `60 s`) khỏi chuỗi phạt `arxiv_429_streak`.
   - Khi arXiv trả `HTTP 429` thật: phân loại theo độ trễ header (`TTFB >= 9,0 s` là nghẽn hàng đợi origin `http_429_queue_timeout`, ngược lại là `http_429_edge_fast`), xoay session và ngủ **Cooldown leo thang có trần: `120 s → 180 s → 240 s`** (hạ 1 bậc sau `6` bài `200 OK` liên tiếp).
   - **CDN-Aware Self-Healing:** Phân tích header `X-Cache` / `X-Served-By` tách riêng `HIT` thuần tại edge khỏi `SHIELD_HIT` và `MISS` mỗi cửa sổ `100` request; nếu `HIT` thuần giảm `< 2,0 MiB/s` qua `2` cửa sổ liên tiếp, crawler tự động ngủ hồi phục `300 s` (tối đa `3` lần/phiên qua nhánh `recovery_seconds` riêng, không đếm đúp vào `arxiv_thermal_cooldowns`).

6. **Giải nén Cut-Through In-Flight `O(1)` RAM (`--in-flight-extract`) song hành cùng Pool `extract-worker`:**
   - Giữ nghiêm ngặt **1 kết nối tuần tự duy nhất** tới `export.arxiv.org`, không bắn đa luồng mạng song song, nhưng tận dụng đa luồng cục bộ để chồng lấp khâu xử lý dữ liệu trong lúc chờ nhịp `3,05 s`:
     - *Chế độ Cut-Through In-Flight (`--in-flight-extract` — `v3.16`):* Trong lần thử đầu tiên của mỗi phiên bản, hàm `download_and_extract_source()` giải nén luồng `gzip` + `tar` 1-pass trực tiếp trên socket với bộ đệm cố định **`128 KiB`** (`O(1)` RAM, **`0 B` ghi tạm vào `.tmp/`**), lọc giữ `.tex`, `.bib`, `.bbl` và tính `SHA-256` ngay trên đường truyền vào `.vK.part/tex/`. Nếu luồng mạng bị ngắt giữa chừng trước `EOF`, thư mục staging `.vK.part` được dọn sạch, bài báo được defer về cuối pass và tự động lùi mượt về chế độ đệm `download_source()` hỗ trợ nối byte `HTTP 206 Range`.
     - *Chế độ đệm Zero-Copy + Pool 2 luồng `extract-worker`:* Với các lượt đệm qua `extract_queue` (trần RAM `192 MiB`, `maxsize = 8`; gói $\le 96\text{ MiB}$ nằm trọn trong `bytearray` RAM), bộ đọc `_FastGzipStream` cắt các lát `512 KiB` không sao chép qua `zlib.decompressobj` ở tầng C, kiểm tra an toàn đường dẫn (`..`, đường dẫn tuyệt đối, tên thiết bị Windows `CON`/`NUL`/`AUX`), kiểm tra zip-bomb (`max_extract_bytes = 2 GiB`), dùng cache thư mục cha `created_dirs` (giảm `> 95%` syscall), rồi hoán đổi nguyên tử `part.replace(final)` sang `vK/` và ghi `manifest.sqlite` ở bước cuối cùng.

### Bước 3 — Thu thập siêu dữ liệu tham khảo học thuật (`s2.py`, `pipeline.py` — `v3.18`)

Khối Semantic Scholar được nâng cấp toàn diện trong phiên bản **`v3.18`** để triệt tiêu nút thắt bão `HTTP 429` từng ghi nhận ở các phiên bản trước:

1. **Lô mật độ cao `150` bài/request & Điều nhịp AIMD (`s2.py`, `http.py`):**
   - Nâng kích thước lô mặc định `--s2-batch-size` từ `25` lên **`150` bài báo/lô** (kẹp trong khoảng `[1, 500]`). Phép đo thực tế cho thấy một lô `150` bài có dung lượng JSON phản hồi trung bình **`~3,9 MB`**, nằm an toàn dưới giới hạn `10 MB` của endpoint `POST https://api.semanticscholar.org/graph/v1/paper/batch`, qua đó **giảm `6×` tổng số HTTP request** gửi tới S2.
   - Bộ điều nhịp `AdaptiveRateLimiter` chuyển sang cơ chế **AIMD (Additive Increase / Multiplicative-like Recovery)**: giữ sàn tối thiểu **`1,1 s / request`** (End-to-Start), khi gặp `429` chỉ tăng tuyến tính `+0,4 s` (tối đa trần `3,0 s` khi có `S2_API_KEY` đã `.strip()` hoặc `8,0 s` khi ẩn danh), và hồi phục `-0,25 s` sau mỗi `5` phản hồi `200 OK` liên tiếp.
2. **Mở rộng Auto-Bisection & 10k-Ref Guard:**
   - Tự động chia đôi đệ quy danh sách ($N/2$) không chỉ khi gặp `HTTP 413 Payload Too Large` hoặc `5xx`, mà cả khi gặp **`HTTP 400`** với thông báo vượt kích thước phản hồi của S2 (`maximum size` / `exceed` / `too large` / `payload`).
   - Đồng thời, nếu tổng số tham khảo nhúng của các bài trong một lô chạm ngưỡng **`>= 9.500` refs** (`_BATCH_AGGREGATE_TRUNCATION_REFS`), hệ thống tự cắt tách phần đuôi lô để gọi lại riêng, ngăn tình trạng S2 âm thầm cắt cụt dữ liệu trả về ở ngưỡng 10.000 mục.
3. **Loại bỏ False-Positive `GET /references` & Cô lập Save-First (`Save-First Isolation`):**
   - Phân tích log thực nghiệm trên `2.000` bài báo cho thấy API S2 thường trả `referenceCount > len(references)` chỉ vì một vài trích dẫn không liên kết được (`citedPaper = null`). Bản cũ kích hoạt gọi lẻ `GET /references` cho mọi ca lệch nhỏ này, gây ra hàng nghìn request dư thừa và làm bùng phát `HTTP 429`.
   - Bản `v3.18` siết chặt điều kiện `_references_truncated()`: chỉ gọi phân trang `GET /graph/v1/paper/ARXIV:{id}/references?offset=&limit=1000` khi danh sách `references` không phải mảng hợp lệ, khi `len == 0` hoặc `len >= 500` (chạm trần nhúng 500/bài), hoặc khi **thiếu nghiêm trọng (`len < 50%` của `referenceCount` với `referenceCount >= 10`)**.
   - Kết hợp **Save-First Isolation**: ngay khi nhận phản hồi `200 OK` cho một lô hoặc nửa lô bisection, hàm `on_result` ghi ngay xuống đĩa (`references.json` và `s2_references.raw.json.gz`) toàn bộ các bài đã đủ dữ liệu, sau đó mới cô lập vét riêng các bài bị cắt (`defer_truncated`) hoặc nửa bị lỗi — tuyệt đối không làm mất tiến độ của cả lô nếu một bài phụ gặp `429`.
4. **Fast S2 Backoff, `--s2-only` Resilient Loop & Minh bạch hóa `HTTP 404`:**
   - Tách thang chờ `429` riêng cho S2 (`_s2_retry_after`: **`2 → 4 → 8 → 15 s + jitter 0,2..1,0 s`**, tôn trọng `Retry-After` trong biên `1..120 s`), ghi log snippet `429` đã che giấu khóa qua `SecretRedactingFilter`. Trong chế độ `--s2-only`, worker hỗ trợ tự động vét lại tối đa **`2` vòng deferred** (`30 s` cooldown), flush lô nhanh `0,35 s`, log tiến độ và tự kích `checkpoint-worker` định kỳ.
   - **Xử lý minh bạch bài S2 trả `HTTP 404`:** Khi Semantic Scholar trả `404` (hoặc `null` trong batch), hệ thống mặc định ghi nhận trạng thái **`not_indexed`** (`raw: {"status": 404}`) để báo cáo trung thực tỷ lệ độ phủ của S2 API. Công cụ trích xuất cục bộ từ `.bib`/`.bbl` (`--enable-bib-fallback` hoặc chạy ngoại tuyến `src/crawler/enrich_references.py`) đóng vai trò lớp dự phòng tùy chọn và được gắn nhãn tách riêng (`source: "local_bib"`) nếu sử dụng, không làm sai lệch thống kê thành công thực của S2.

---

## 2.2. Tổng hợp Công cụ, Thư viện & Kiến trúc Module

Bảng dưới đây đối chiếu bộ công cụ kỹ thuật thực tế được triển khai ở phiên bản **`v3.18`** với các giải pháp trong "hộp công cụ" của đề bài:

| Hạng mục | Công cụ / Thư viện sử dụng | Vai trò & Đánh giá kỹ thuật |
| :--- | :--- | :--- |
| **Khám phá bài báo & phiên bản** | **Kaggle Snapshot** (`--snapshot` qua `snapshot.py`) + **arXiv Atom API** / **OAI-PMH** (`discovery.py`) | **Luồng chính:** Quét tệp `arxiv-metadata-oai-snapshot.json` ngoại tuyến trong `< 60 s` cho 25.000 ID, `0` request mạng, `0%` lỗi 429, phân loại `v1` vs `v2..v30`, trích xuất trọn vẹn ngày sửa đổi trung gian.<br>**Luồng dự phòng:** Tra cứu lô 250 ID qua Atom API, tối ưu `<updated>` cho bài 2 bản, bù ngày trung gian qua OAI-PMH (`--enable-oai-dates`) và xác nhận thiếu theo lô 50 ID. |
| **Tiền kiểm POP & Đối chứng Transport** | **`crawler/preflight.py`** | Thăm dò nhanh 4 ID lạnh bằng `Range: bytes=0-4194303` (timeout `10 s / 20 s`) để chấm hạng POP/VM Colab (`Grade A/B/C`, ước lượng giờ cho 5.000 ID) và chạy A/B Benchmark HTTP/1.1 vs HTTP/2 trên các ID tách rời (`[0::2]` vs `[1::2]`). |
| **Tải gói mã nguồn** | **`export.arxiv.org/src/`** + `httpx[http2]` / `requests` | 1 kết nối đơn tuần tự (`--http2` `Limits(max_connections=1)` với `RST_STREAM` early-abort, fallback HTTP/1.1 `_SingleConnAdapter` `TCP_NODELAY=1`). Giữ ấm Keep-Alive `500` req (xoay khi gói `>= 50 MiB` hoặc `TTFB >= 5,0 s`). Nhịp **Start-to-Start `3,05 s + jitter 0..0,10 s`**, đệm hậu tải `0,25 s`, **Zero-Body `Content-Type` Header Early-Reject**, **Paced `6,0 MiB/s`**, **Deficit Breather** (trần `6,0 s`), **Traffic-Shaping Interleaver & Leaky Byte-Budget (`360 MiB / 180 s`)**, **CDN-Aware Self-Healing** (`X-Cache` tách `HIT` thuần vs `SHIELD_HIT`/`MISS`) và nối `HTTP 206 Range` tại chỗ. |
| **Giải nén & Lọc TeX** | **Cut-Through In-Flight** + **`_FastGzipStream`** + `tarfile` + `hashlib` | Hỗ trợ giải nén trực tiếp trên luồng socket `--in-flight-extract` (`128 KiB`, `O(1)` RAM, `0 B` `.tmp/`) lẫn `_FastGzipStream` `512 KiB` ở tầng C trên pool 2 luồng `extract-worker`. Chỉ giữ **`.tex`, `.bib` và `.bbl`**, băm SHA-256 song song, cache thư mục `created_dirs`, hoán đổi nguyên tử hai pha. |
| **Trích xuất tham khảo** | **Semantic Scholar Graph API** (`requests` + `S2_API_KEY`) | Lô mật độ cao mặc định **`150` ID** (`POST /paper/batch`, tự Bisection khi `400`/`413`/`5xx`/`>= 9.500` refs); siết `_references_truncated()` diệt false-positive; **Save-First Isolation**; **Fast S2 Backoff (`2→4→8→15 s`) + AIMD** (`>= 1,1 s`); `2` vòng vét deferred trong `--s2-only`; tách bạch `404` (`not_indexed`) khỏi dự phòng tùy chọn `.bib/.bbl`. |
| **Quản lý trạng thái & Chịu lỗi** | `sqlite3` (WAL mode) + `msvcrt`/`fcntl` | Khóa tiến trình cấp hệ điều hành `_acquire_workspace_lock` (chống chạy trùng 2 crawler trên cùng `data/`), sổ trạng thái manifest ghi sau cùng, lưu mốc cooldown liên tiến trình `rate_state.json`. |
| **Sao lưu nền & Chống thoái lui** | `checkpoint.py` (`tarfile`, `gzip`) | Chụp ảnh nóng SQLite qua `Connection.backup()`, nén streaming `.tar.gz` ở nền song song lúc ngủ cooldown hoặc định kỳ mỗi `1.000–2.500` ID, kèm `shrink guard` và `skip_if_unchanged=True`. |
| **Đo lường & Phân tích phiên** | `psutil`, `time.perf_counter`, `pyarrow`, `pandas`, `jupyter-book` | Luồng daemon `ResourceSampler` đo RAM RSS mỗi `5 s` ($O(1)$), bộ lọc bí mật `SecretRedactingFilter`, xuất Parquet chuẩn hóa, bộ tổng hợp đa phiên Colab `summarize_sessions()` bóc tách từng phiên chạy và viễn trắc CDN/transport. |

Mã nguồn trong repository [`GiaaPhuc/arxiv-pipeline`](https://github.com/GiaaPhuc/arxiv-pipeline) được tổ chức phân tầng chặt chẽ theo từng cột mốc và bảo vệ bằng **816 bài kiểm thử đơn vị (`319` bài M1, `334` bài M2 và `163` bài M3 trong `src/tests/{m1,m2,m3}/` — pass 100%, `0` failed/skipped)** với `pytest` và fixtures ngoại tuyến:

| Nhóm chức năng | Các module trong `src/` | Trách nhiệm kỹ thuật chính |
| :--- | :--- | :--- |
| **Định danh & Hợp đồng dữ liệu** | `crawler/models.py`, `crawler/ids.py`, `crawler/config.py` | Hợp đồng dữ liệu bất biến (`SCHEMA_VERSION = 1`), chuẩn hóa định danh mới/cũ, mở rộng dải `id_ranges.csv` thành 25.000 ID, nạp cấu hình môi trường (`v3.18` defaults). |
| **Khám phá, HTTP & Tiền kiểm** | `crawler/snapshot.py`, `crawler/discovery.py`, `crawler/http.py`, `crawler/preflight.py` | Khám phá ngoại tuyến `--snapshot` `< 60 s`, dự phòng Atom API lô 250 + OAI-PMH (`--enable-oai-dates`), transport đơn kết nối HTTP/2 (`httpx`) & HTTP/1.1 (`_SingleConnAdapter`), bộ đọc `X-Cache`/`X-Served-By`, `AdaptiveRateLimiter` AIMD và tiền kiểm POP/A-B Benchmark (`preflight.py`). |
| **Giao tiếp mạng & Điều nhịp** | `crawler/source.py`, `crawler/s2.py` | Nhịp Start-to-Start `3,05 s + jitter`, đệm hậu tải `0,25 s`, Zero-Body Header Early-Reject, Cut-Through In-Flight Extraction `O(1)` RAM, Paced Stream `6,0 MiB/s`, Deficit Breather, `HTTP 206 Range`, và S2 High-Density Batch `150` + Save-First + Bisection `400/413/5xx/10k-ref`. |
| **Điều phối, Hàng đợi & Bền bỉ** | `crawler/pipeline.py`, `crawler/manifest.py`, `crawler/checkpoint.py`, `run_crawl.py`, `notebooks/colab_crawl.ipynb` | Điều phối Producer–Consumer 5 nhóm luồng, Traffic-Shaping Interleaver & Leaky Byte-Budget `360 MiB / 180 s`, CDN Self-Healing, pool `extract-worker`, `deferred_ids` (tối đa 5 pass), OS mutex, checkpoint nền, chế độ `--skip-s2` / `--s2-only`. |
| **Đo lường, Kiểm định & Xuất bảng** | `crawler/metrics.py`, `corpus.py`, `crawler/validate_corpus.py`, `crawler/audit_corpus.py`, `crawler/enrich_references.py`, `crawler/export.py`, `crawler/export_data.py` | Lấy mẫu RAM $O(1)$, viễn trắc CDN/transport từng phiên, che bí mật nhật ký, kiểm tra 5 bất biến toàn vẹn, kiểm toán `audit_corpus.py`, xuất 2 bảng Parquet, thống kê `cross_version_dedup` và tổng hợp đa phiên `summarize_sessions()`. |
| **Cầu nối Milestone 2 & 3** | `parsing/*`, `run_parse.py`, `notebooks/colab_parse.ipynb`, `matching/*`, `run_matching.py` | Phân tích cú pháp phân cấp M2 (`elements`, `hierarchy`, `bibtex`) và kiểm toán 8 bất biến (`parsing/validate_m2.py`); đối sánh tham chiếu không dùng LLM M3 (`matching/*`, `run_matching.py`) và đóng gói 6 bảng Parquet Hugging Face (`matching/export_hf.py`). |

````{admonition} Lệnh Vận hành Nhanh của Pipeline Thu thập (Quick Reference — v3.18)
:class: tip

```bash
# 0. Tiền kiểm nhanh Fastly POP / VM Colab trước khi chạy dài (4 ID lạnh)
python src/crawler/preflight.py --ranges src/id_ranges.csv --http2

# ==============================================================================
# QUY TRÌNH 2 GIAI ĐOẠN CHUẨN v3.18 (Khuyến nghị cho Colab CPU-only)
# ==============================================================================

# Giai đoạn 1: Cào nguồn TeX tối ưu (HTTP/2 + In-Flight Extract + Traffic-Shaping)
python src/run_crawl.py \
  --ranges src/id_ranges.csv \
  --snapshot arxiv-metadata-oai-snapshot.json \
  --data-dir data \
  --backup-dir /path/to/drive/arxiv-data.tar.gz \
  --backup-every-ids 2500 \
  --auto-resume-rate-limit \
  --http2 \
  --in-flight-extract \
  --skip-s2

# Giai đoạn 2: Làm giàu trích dẫn Semantic Scholar độc lập (High-Density Batch 150)
python src/run_crawl.py \
  --ranges src/id_ranges.csv \
  --data-dir data \
  --s2-only \
  --s2-batch-size 150 \
  --auto-resume-rate-limit

# (Tùy chọn) Bù trích dẫn ngoại tuyến từ .bib/.bbl cho bài S2 trả 404 (source: local_bib)
python src/crawler/enrich_references.py --data-dir data

# ==============================================================================
# BỘ CÔNG CỤ KIỂM TOÁN, NGHIỆM THU & XUẤT DỮ LIỆU
# ==============================================================================
python src/crawler/validate_corpus.py --data-dir data
python src/crawler/audit_corpus.py --data-dir data --output data/stats/audit_report.json
python src/crawler/export_data.py --data-dir data --out-dir data/stats
```
````

---

## 2.3. Chính sách Lịch sự Máy chủ, Chịu lỗi & Kiểm chứng Dữ liệu

Vận hành thu thập quy mô lớn trên Google Colab đòi hỏi sự cân bằng tuyệt đối giữa **chuẩn lịch sự máy chủ học thuật** và **khả năng chịu lỗi tự động 100%**:

1. **Quy trình 2 giai đoạn tách rời & Khám phá ngoại tuyến Kaggle Snapshot (`--snapshot`):**
   - Quét tệp `arxiv-metadata-oai-snapshot.json` ngoại tuyến nạp sẵn 100% siêu dữ liệu của 25.000 ID trong `< 60 s` (`0` request Atom API, `0%` rủi ro `429` khám phá).
   - Tách pha `--skip-s2` và `--s2-only` bảo đảm kênh arXiv và kênh Semantic Scholar không bao giờ cản trở luồng của nhau.
2. **Chuẩn lịch sự Start-to-Start $3{,}05\text{ s}$, Đệm hậu tải $0{,}25\text{ s}$ & Định hình lưu lượng (`http.py`, `pipeline.py`):**
   - Duy trì nghiêm ngặt **1 kết nối tuần tự duy nhất** tới `export.arxiv.org` với nhịp **Start-to-Start $3{,}05\text{ s} + \text{jitter } 0\dots 0{,}10\text{ s}$** ($\ge 3{,}00\text{ s}$) và đệm hậu tải $0{,}25\text{ s}$, kết hợp **Deficit Breather** trần $6{,}0\text{ s}$ và dòng tải mượt $6{,}0\text{ MiB/s}$ để tránh dồn xung burst lên Fastly CDN.
   - **Traffic-Shaping & CDN-Aware Self-Healing:** Hoán vị tỷ lệ vàng trong chunk $\ge 16$ ID, xen kẽ `v2..vN` bài $\ge 25\text{ MiB}$ cách $15$ bản nhẹ, giới hạn Leaky Byte-Budget `360 MiB / 180 s` (ngủ sau khi đã đưa vào `extract_queue`), kích Defensive Soft-Pacing ($3{,}80\text{–}4{,}50\text{ s}$ trong `50` req) khi `HIT` thuần `< 3,0 MiB/s` và tự ngủ hồi phục `300 s` (tối đa `3` lần/phiên) nếu `HIT` thuần `< 2,0 MiB/s` qua `2` cửa sổ liên tiếp.
   - **Phục hồi `Range` tại chỗ & Cooldown khóa trần:** Đứt stream trên gói $\ge 1\text{ MiB}$ xoay session, nghỉ $12\text{–}14\text{ s}$ rồi nối qua `HTTP 206 Range` từ `.resume-{id}-v{K}.part` (tuyệt đối không xóa `.part` khi `429`, tách `is_stream_break` khỏi streak `429`); khi gặp `429` thật từ arXiv, defer bài và ngủ cooldown khóa trần `120 → 180 → 240 s` (hạ 1 bậc sau `6` bài `200 OK`).
3. **Semantic Scholar High-Density Engine (`s2.py` — `v3.18`):**
   - Lô `150` bài/request, Auto-Bisection cho `400`/`413`/`5xx`/`>= 9.500` refs, siết `_references_truncated()` triệt tiêu false-positive `/references`, **Save-First Isolation** lưu ngay từng bài hoàn tất trước khi vét phần bị cắt, **Fast S2 Backoff (`2→4→8→15 s`) + AIMD**, và ghi nhận trung thực trạng thái `not_indexed` (`HTTP 404`) tách biệt khỏi dữ liệu dự phòng `.bib/.bbl`.
4. **Khóa tiến trình OS Mutex & Checkpoint nền thông minh (`pipeline.py`, `checkpoint.py`):**
   - `_acquire_workspace_lock` khóa thư mục `data/` ở mức hệ điều hành (`msvcrt.locking` / `fcntl.flock`); `rate_state.json` bảo toàn thời gian cooldown còn dư giữa các phiên resume.
   - `checkpoint-worker` sao lưu SQLite bằng `Connection.backup()` sang `.tar.gz` trong nền kèm `shrink guard` và `skip_if_unchanged=True`.
5. **Kiểm chứng toàn vẹn hậu thu thập (`crawler/validate_corpus.py`, `crawler/audit_corpus.py`) & Cầu nối Milestone 2:**
   - Trình kiểm định độc lập xác nhận 5 bất biến: *(i)* đủ thư mục phiên bản liên tục `v1..vN`; *(ii)* không tồn tại tệp lạ ngoài siêu dữ liệu chuẩn và `.tex`/`.bib`/`.bbl`; *(iii)* khớp 100% dung lượng và mã băm `SHA-256` với `meta.json`; *(iv)* manifest nhất quán với đĩa và không còn bản ghi `pending`; *(v)* hai bảng Parquet tuân thủ đúng khóa không rỗng.
   - `audit_corpus.py` đối chiếu từng thư mục trên đĩa với bảng `version_pairs` trong `manifest.sqlite`. Đồng thời, việc lưu nguyên bản `.bbl` (không sửa nội dung) và bảo toàn ngày `version_date` trên từng phiên bản đặt nền tảng trực tiếp cho bộ phân tích cú pháp ở Milestone 2.
