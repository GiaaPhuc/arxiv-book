# Chương 5. Thu thập Đa tệp & Xây dựng Cây Phân cấp Thích ứng

```{admonition} Thông tin Dự án & Sản phẩm Bàn giao (Milestone 2)
:class: note
- **Giai đoạn:** Milestone 2 — Phân tích Cú pháp Phân cấp, Chuẩn hóa và Khử trùng lặp Mã nguồn LaTeX (*Hierarchical Parsing, Standardization & Cross-Version Deduplication*).
- **Repository mã nguồn pipeline:** [`GiaaPhuc/arxiv-pipeline`](https://github.com/GiaaPhuc/arxiv-pipeline) · **Module trọng tâm:** `src/parsing/*`, `src/run_parse.py`, `src/validate_m2.py`.
- **Repository báo cáo trực tuyến (Jupyter Book):** [`GiaaPhuc/arxiv-book`](https://github.com/GiaaPhuc/arxiv-book) · **GitHub Pages:** <https://giaaphuc.github.io/arxiv-book/>
- **Nguyên tắc liêm chính dữ liệu:** Toàn bộ bảng tổng hợp và biểu đồ trực quan ở Chương 7 và Chương 8 được tính toán và kết xuất tự động bằng Python ngay trong lúc biên dịch sách (`jupyter-book build .`) từ thư mục `stats/m2/`, không sử dụng ảnh chụp màn hình tĩnh và không nhúng mã nguồn cài đặt của pipeline vào báo cáo.
```

## 5.1. Bài toán Phân tích LaTeX Thực tế & Kiến trúc Luồng Đầu–Cuối

Tiếp nối kho dữ liệu thô đã thu thập ở Milestone 1 (gồm toàn bộ các phiên bản $v_1 \dots v_N$ của 25.000 định danh arXiv được giao), **Milestone 2** giải quyết bài toán chuyển đổi các cây thư mục mã nguồn `.tex`/`.bib` phi cấu trúc thành **ba bảng dữ liệu quan hệ–phân cấp chuẩn hóa** (`elements`, `hierarchy`, `bibtex`), tạo nền tảng biểu diễn văn bản sạch và giàu ngữ cảnh cho mô hình đối sánh tài liệu tham khảo (đánh giá bằng `MRR@5`) ở Milestone 3.

Khác với các ngôn ngữ đánh dấu có ngữ pháp phi ngữ cảnh (CFG) cố định như XML hay HTML, mã nguồn LaTeX thực tế trên arXiv đặt ra bốn thách thức kỹ thuật lớn:

1. **Tổ chức đa tệp phức tạp và nhiễu tệp nháp:** Một phiên bản bài báo có thể chia thành hàng chục tệp `.tex` lồng nhau qua `\input`, `\include`, `\subfile`, `\import`, đồng thời lẫn các tệp không tham gia biên dịch như bản trả lời phản biện (`rebuttal.tex`), phụ lục tách rời (`supplement_standalone.tex`), hình vẽ TikZ độc lập (`\documentclass{standalone}`) hoặc các lệnh nạp tệp đã bị vô hiệu hóa sau dấu `%`.
2. **Cấu trúc phân cấp không đồng nhất giữa các họ lớp tài liệu:** Tác giả sử dụng nhiều lớp định dạng khác nhau (`article`, `revtex4-2`, `IEEEtran`, `llncs`, `acmart`, `amsart`...) và thường xuyên nhảy cấp đề mục (ví dụ từ `\section` xuống thẳng `\paragraph`), trộn lẫn các đề mục không đánh số `\section*{Acknowledgements}` (cần giữ lại) với `\section*{References}` (cần loại trừ khỏi cây nội dung).
3. **Đa dạng ký hiệu toán học, macro tự định nghĩa và bẫy tách câu khoa học:** Tác giả tự định nghĩa macro ở phần mở đầu (`\newcommand`, `\def`), viết phương trình bằng gần mười kiểu môi trường khác nhau, và sử dụng dày đặc dấu chấm trong số thập phân (`3.14`), tên viết tắt (`A. Einstein`), thuật ngữ học thuật (`et al.`, `i.e.`, `Fig. 1`) lẫn biểu thức toán học nội dòng.
4. **Trùng lặp lớn nhưng không đồng nhất khóa giữa các phiên bản $v_1 \dots v_N$:** Giữa hai phiên bản liên tiếp của cùng một bài báo, phần lớn câu văn, công thức và tài liệu tham khảo giữ nguyên nội dung nhưng có thể thay đổi khóa trích dẫn (`\cite{vaswani2017}` ở $v_1$ đổi thành `\cite{vit_transformer}` ở $v_2$) hoặc bổ sung/đánh rơi trường siêu dữ liệu BibTeX (`doi`, `year`).

Để giải quyết triệt để cả bốn thách thức trên trong giới hạn tài nguyên của **môi trường xử lý CPU đám mây** (vận hành thực nghiệm trên cấu hình **12 worker song song** với lô xả 500 bài/shard), hệ thống phân tích cú pháp trong `src/parsing/` được thiết kế theo kiến trúc luồng **7 bước khép kín cấp bài báo**, xử lý song song đa tiến trình và xả trực tiếp ra các phân mảnh Parquet:

<div class="pipeline-flow" role="region" aria-label="Sơ đồ Quy trình Phân tích Cú pháp và Khử trùng lặp Milestone 2">
  <div class="pf-endpoint-node pf-input">
    <span class="pf-icon">&#128193;</span>
    <span>Kho ngữ liệu Milestone 1 (<code>data/papers/&lt;dirname&gt;/v1..vN/tex/</code>)</span>
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
        <span>Chặng 1 — Thu thập Đa tệp, Chuẩn hóa &amp; Dựng Cây Phân cấp (từng phiên bản <code>v1..vN</code>)</span>
      </div>
      <span class="pf-rate-badge">gathering &middot; cleaner &middot; hierarchy</span>
    </div>
    <div class="pf-steps-grid">
      <div class="pf-step-item">
        <span class="pf-step-num">1</span>
        <div class="pf-step-body">
          <strong>Khử comment &amp; bầu chọn tệp gốc</strong>
          <span>Bảo toàn <code>\%</code>, <code>verbatim</code>; chấm điểm <code>S(f)</code> chọn <code>\documentclass</code> chính</span>
        </div>
      </div>
      <div class="pf-step-item">
        <span class="pf-step-num">2</span>
        <div class="pf-step-body">
          <strong>Nối phẳng DFS chống chu trình</strong>
          <span>Mở rộng <code>\input</code>/<code>\include</code>/<code>\subfile</code> (độ sâu &le; 15), lọc bỏ tệp <code>.tex</code> thừa</span>
        </div>
      </div>
      <div class="pf-step-item">
        <span class="pf-step-num">3</span>
        <div class="pf-step-body">
          <strong>Mở rộng macro &amp; chuẩn hóa toán học</strong>
          <span>Giải nén <code>\newcommand</code>; đưa toán về <code>&#36;...&#36;</code> và <code>\begin{equation}</code></span>
        </div>
      </div>
      <div class="pf-step-item">
        <span class="pf-step-num">4</span>
        <div class="pf-step-body">
          <strong>Ngăn xếp cấp bậc &amp; tách câu ngữ cảnh</strong>
          <span>Monotonic Rank Stack + tách câu 4 bước <code>Protect–Mask–Split–Restore</code></span>
        </div>
      </div>
    </div>
  </div>
  <div class="pf-connector" aria-hidden="true">
    <svg width="20" height="16" viewBox="0 0 20 16" fill="none">
      <line x1="10" y1="0" x2="10" y2="16" stroke="currentColor" stroke-width="1.8" stroke-dasharray="3 3"/>
    </svg>
    <div class="pf-queue-pill">
      <span>&#8645; Tách nhánh <code>References</code> / <code>thebibliography</code> + tệp <code>.bib</code>, <code>.bbl</code> khỏi cây văn bản</span>
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
        <span>Chặng 2 — Trích xuất &amp; Chuẩn hóa Tài liệu Tham khảo về BibTeX</span>
      </div>
      <span class="pf-rate-badge">bib_extractor.py</span>
    </div>
    <div class="pf-steps-grid">
      <div class="pf-step-item">
        <span class="pf-step-num">5a</span>
        <div class="pf-step-body">
          <strong>Bộ phân tích <code>.bib</code> cân bằng ngoặc</strong>
          <span>Giải <code>@string</code>, nối chuỗi <code>#</code>, bảo toàn URL mã hóa <code>%</code></span>
        </div>
      </div>
      <div class="pf-step-item">
        <span class="pf-step-num">5b</span>
        <div class="pf-step-body">
          <strong>Anchor-First + Cascade 4 mẫu cho <code>\bibitem</code></strong>
          <span>Bắt <code>DOI</code>/<code>arXiv</code>/<code>Year</code>/<code>\bibinfo</code> &amp; phân đoạn văn bản tự do</span>
        </div>
      </div>
    </div>
  </div>
  <div class="pf-connector" aria-hidden="true">
    <svg width="20" height="22" viewBox="0 0 20 22" fill="none">
      <line x1="10" y1="0" x2="10" y2="15" stroke="currentColor" stroke-width="1.8"/>
      <path d="M5 12L10 19L15 12" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
  </div>
  <div class="pf-stage-card pf-stage-ok">
    <div class="pf-stage-header">
      <div class="pf-stage-title">
        <span class="pf-stage-dot"></span>
        <span>Chặng 3 — Khử trùng lặp Hai tầng Xuyên Phiên bản &amp; Xuất Sharded Parquet</span>
      </div>
      <span class="pf-rate-badge">dedup &middot; export_m2 &middot; lô 500 bài</span>
    </div>
    <div class="pf-steps-grid pf-steps-3">
      <div class="pf-step-item">
        <span class="pf-step-num">6a</span>
        <div class="pf-step-body">
          <strong>Union-Find &amp; Hợp nhất trường</strong>
          <span>Gom cụm tham chiếu trùng, chống bẫy khóa số <code>\bibitem{1}</code>, chọn <code>canonical_key</code></span>
        </div>
      </div>
      <div class="pf-step-item">
        <span class="pf-step-num">6b</span>
        <div class="pf-step-body">
          <strong>Viết lại <code>\cite{}</code> &amp; Băm toàn văn</strong>
          <span>Đồng bộ khóa trích dẫn trước khi băm <code>(kind, content)</code> dùng chung <code>elementid</code></span>
        </div>
      </div>
      <div class="pf-step-item">
        <span class="pf-step-num">7</span>
        <div class="pf-step-body">
          <strong>Xả Sharded Parquet &amp; Thống kê</strong>
          <span>Ghi <code>elements</code>, <code>hierarchy</code>, <code>bibtex</code> kiểu <code>dictionary</code></span>
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
    <span>Kiểm chứng 8 bất biến đồ thị &amp; quan hệ (<code>validate_m2.py</code>) &rarr; Xuất báo cáo (<code>stats/m2_*</code>)</span>
  </div>
</div>

---

## 5.2. Hợp đồng Dữ liệu & Lược đồ Ba Bảng Đầu ra (`elements`, `hierarchy`, `bibtex`)

Toàn bộ kết quả phân tích cú pháp được lưu trữ tại thư mục `data/parsed/` dưới dạng các **phân mảnh Apache Parquet** (`part-00000.parquet` – `part-00049.parquet`, tổng cộng **50 phân mảnh mỗi bảng**, mỗi phân mảnh chứa tối đa `500` bài báo cho toàn tập `25.000` bài), tương thích trực tiếp với định dạng công bố dữ liệu phân mảnh trên Hugging Face ở Milestone 3:

<div class="corpus-tree-card" role="region" aria-label="Cấu trúc thư mục đầu ra Milestone 2">
  <div class="ct-header">
    <span>Cấu trúc dữ liệu đầu ra của bộ phân tích cú pháp (<code>data/parsed/</code> &amp; <code>data/stats/</code>)</span>
    <span class="ct-dots" aria-hidden="true"><span></span><span></span><span></span></span>
  </div>
  <div class="ct-list">
    <div class="ct-row">
      <div class="ct-path"><span class="ct-dir">data/parsed/</span></div>
      <div class="ct-desc">Thư mục chứa 3 bảng Parquet phân mảnh và sổ trạng thái chạy tiếp (resume)</div>
    </div>
    <div class="ct-row">
      <div class="ct-path"><span class="ct-branch">├── </span><span class="ct-dir">elements/</span><span class="ct-file">part-*.parquet</span></div>
      <div class="ct-desc">Kho phần tử nội dung duy nhất xuyên suốt các phiên bản của từng bài báo</div>
    </div>
    <div class="ct-row">
      <div class="ct-path"><span class="ct-branch">├── </span><span class="ct-dir">hierarchy/</span><span class="ct-file">part-*.parquet</span></div>
      <div class="ct-desc">Danh sách cạnh phân cấp <code>(elementid &rarr; parentid)</code> riêng theo từng <code>version</code></div>
    </div>
    <div class="ct-row">
      <div class="ct-path"><span class="ct-branch">├── </span><span class="ct-dir">bibtex/</span><span class="ct-file">part-*.parquet</span></div>
      <div class="ct-desc">Các mục BibTeX đã khử trùng lặp và hợp nhất trường siêu dữ liệu</div>
    </div>
    <div class="ct-row">
      <div class="ct-path"><span class="ct-branch">├── </span><span class="ct-file">_done.txt</span></div>
      <div class="ct-desc">Danh sách <code>arxiv_id</code> đã xả thành công ra Parquet (hỗ trợ resume tức thì)</div>
    </div>
    <div class="ct-row">
      <div class="ct-path"><span class="ct-branch">├── </span><span class="ct-file">_errors.jsonl</span></div>
      <div class="ct-desc">Nhật ký cô lập ngoại lệ cấp bài báo (nếu có) để không dừng toàn tiến trình</div>
    </div>
    <div class="ct-row">
      <div class="ct-path"><span class="ct-branch">└── </span><span class="ct-file">parse_run.json</span></div>
      <div class="ct-desc">Bản ghi tóm tắt thông số phiên chạy gần nhất</div>
    </div>
    <div class="ct-row">
      <div class="ct-path"><span class="ct-dir">data/stats/</span></div>
      <div class="ct-desc">Bộ 4 tệp thống kê gọn nhẹ phục vụ biên dịch tự động Chương 7 &amp; Chương 8</div>
    </div>
    <div class="ct-row">
      <div class="ct-path"><span class="ct-branch">└── </span><span class="ct-file">m2_{summary,performance}.json, m2_{papers_stats,elements_kind}.csv</span></div>
      <div class="ct-desc">Thống kê độ phủ, hiệu quả khử trùng lặp và hiệu năng Colab CPU</div>
    </div>
  </div>
</div>

Lược đồ chi tiết của ba bảng dữ liệu được khóa cứng trong `src/parsing/models.py` (`SCHEMA_VERSION = 1`) và kiểm định nghiêm ngặt bằng `pyarrow` như sau:

| Bảng | Đơn vị bản ghi | Lược đồ cột & Kiểu dữ liệu (`pyarrow`) | Ràng buộc toàn vẹn & Quy ước định danh |
| :--- | :--- | :--- | :--- |
| **`elements`** | Một phần tử nội dung **phân biệt** của một bài báo xuyên suốt $v_1 \dots v_N$ | `elementid` (`string`, không null); `arxivid` (`string`, không null); `kind` (`dictionary<int8, string>`, không null); `content` (`string`, không null) | Tập giá trị hợp lệ của `kind` gồm đúng 8 loại: `'document'`, `'heading'`, `'paragraph'`, `'list'`, `'item'`, `'sentence'`, `'block_formula'`, `'figure'`. Nút gốc mỗi phiên bản có định danh `<dirname>#root<v>`; mọi nút khác nếu trùng khớp cặp `(kind, content)` giữa các phiên bản chỉ lưu **một dòng duy nhất** (`#h1`, `#p1`, `#lst1`, `#itm1`, `#s1`, `#eq1`, `#fig1`...). |
| **`hierarchy`** | Một cạnh quan hệ con $\rightarrow$ cha trong một phiên bản cụ thể | `arxivid` (`string`, không null); `version` (`int32`, không null); `elementid` (`string`, không null); `parentid` (`string`, không null) | Với mỗi cặp `(arxivid, version)` có mã nguồn TeX, tập cạnh `(elementid -> parentid)` tạo thành một đồ thị có hướng không chu trình (DAG / cây) hội tụ duy nhất về gốc `<dirname>#root<version>`. Nút gốc không bao giờ xuất hiện ở cột `elementid`. |
| **`bibtex`** | Một tài liệu tham khảo duy nhất sau khi gộp trùng & hợp nhất trường của một bài báo | `arxivid` (`string`, không null); `citationkey` (`string`, không null); `entrytype` (`dictionary<int8, string>`, không null); `title` (`string`); `authors` (`list<string>`, không null); `year` (`int32`, có thể null); `doi` (`string`); `journal` (`string`); `url` (`string`) | Mỗi `(arxivid, citationkey)` là duy nhất. Các mục trích xuất từ cả `.bib`, `.bbl` lẫn `\bibitem` được chuẩn hóa về chữ thường cho `entrytype` (`'article'`, `'inproceedings'`, `'book'`, `'misc'`...), bỏ tiền tố URL khỏi `doi`, và tự động điền `https://arxiv.org/abs/<id>` vào `url` khi phát hiện mã arXiv. |

**Cơ chế chia sẻ nút xuyên phiên bản (Cross-Version Shared DAG):** Thay vì nhân bản toàn bộ cây văn bản cho mỗi lần tác giả cập nhật bản thảo, kiến trúc tách bảng `elements` (lưu nội dung) khỏi bảng `hierarchy` (lưu cấu trúc theo phiên bản) cho phép tái sử dụng tối đa các phần tử không đổi:

<div class="jb-dag-grid" role="region" aria-label="Minh họa chia sẻ phần tử xuyên phiên bản giữa bảng elements và hierarchy">
  <div class="jb-dag-panel">
    <div class="jb-dag-panel-title">
      <span>Phiên bản <code>v1</code> (<code>version = 1</code>)</span>
      <span class="jb-badge-version">#root1</span>
    </div>
    <div>
      <code>2408-11045#root1</code> (<em>Version 1 root</em>)<br/>
      &nbsp;&nbsp;&boxur;&HorizontalLine; <code>#h1</code> <span class="jb-badge-shared">dùng chung</span> <em>"Introduction"</em><br/>
      &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&boxur;&HorizontalLine; <code>#p1</code> <span class="jb-badge-shared">dùng chung</span><br/>
      &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&boxvr;&HorizontalLine; <code>#s1</code> <span class="jb-badge-shared">dùng chung</span> <em>"Transformers scale well \cite{vaswani2017}."</em><br/>
      &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&boxur;&HorizontalLine; <code>#s2</code> <span class="jb-badge-version">chỉ v1</span> <em>"We test on small datasets."</em>
    </div>
  </div>
  <div class="jb-dag-panel">
    <div class="jb-dag-panel-title">
      <span>Phiên bản <code>v2</code> (<code>version = 2</code>)</span>
      <span class="jb-badge-version">#root2</span>
    </div>
    <div>
      <code>2408-11045#root2</code> (<em>Version 2 root</em>)<br/>
      &nbsp;&nbsp;&boxur;&HorizontalLine; <code>#h1</code> <span class="jb-badge-shared">dùng chung</span> <em>"Introduction"</em><br/>
      &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&boxur;&HorizontalLine; <code>#p1</code> <span class="jb-badge-shared">dùng chung</span><br/>
      &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&boxvr;&HorizontalLine; <code>#s1</code> <span class="jb-badge-shared">dùng chung</span> <em>"Transformers scale well \cite{vaswani2017}."</em><br/>
      &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&boxur;&HorizontalLine; <code>#s3</code> <span class="jb-badge-version">mới ở v2</span> <em>"We evaluate on 25 benchmarks."</em>
    </div>
  </div>
</div>

Trong ví dụ trên, các nút `#h1`, `#p1`, `#s1` chỉ chiếm **1 dòng duy nhất** cho mỗi nút trong bảng `elements`, trong khi bảng `hierarchy` ghi nhận hai bộ cạnh độc lập gắn vào `#root1` (`version = 1`) và `#root2` (`version = 2`).

---

## 5.3. Thu thập Đa tệp & Xác định Đường Biên dịch Chính (`gathering.py`)

Module cửa ngõ `src/parsing/gathering.py` nhận từ điển byte thô `{relpath: bytes}` của một phiên bản từ `Corpus.tex_files(arxiv_id, version)` và biến đổi thành một đối tượng `CompilationUnit` thông qua quy trình **3 pha tất định**:

### Pha 1 — Giải mã an toàn & Khử comment bảo toàn ngữ nghĩa (`strip_comments`)

1. **Giải mã không suy biến:** Mọi tệp `.tex` và `.bib` được thử giải mã ưu tiên theo `utf-8-sig` (tự động loại bỏ BOM nếu có); trường hợp tệp cổ điển dùng bảng mã phương Tây 8-bit (`ISO-8859-1` / `Windows-1252`), bộ đọc tự động chuyển sang `latin-1` để bảo đảm **0% lỗi `UnicodeDecodeError`** trên toàn bộ 25.000 bài báo.
2. **Quét khử comment có nhận thức ngữ cảnh:** Một sai lầm phổ biến của các bộ parser đơn giản là xóa thẳng bằng biểu thức `%.*`, làm hỏng ký hiệu phần trăm hợp lệ (`50\%`), cắt cụt đường dẫn chứa mã hóa phần trăm trong `\url{https://.../file%20name.pdf}` hoặc phá vỡ khối mã nguồn minh họa. Hàm `strip_comments` khắc phục bằng bộ quét trạng thái theo dòng:
   - **Vùng bất khả xâm phạm:** Giữ nguyên toàn bộ nội dung bên trong `\begin{verbatim}...\end{verbatim}`, `\begin{lstlisting}...\end{lstlisting}`, lệnh `\verb|...|` (với ký tự phân cách bất kỳ) và đối số của `\url{...}` / `\href{...}`.
   - **Phân biệt `\%` và `%` thật:** Chỉ cắt bỏ phần văn bản từ ký tự `%` khi đứng liền trước nó là một **số chẵn** dấu gạch chéo ngược `\` (tức `\\\%` là ký tự `%` được thoát, còn `\\%` là lệnh xuống dòng `\\` theo sau bởi comment `%`).
   - **Nối dòng chuẩn TeX:** Nếu một dòng kết thúc bằng dấu `%` dùng để nối dòng (hoặc dòng chỉ gồm khoảng trắng và comment), bộ quét loại bỏ dấu `%` cùng ký tự xuống dòng theo đúng cơ chế đọc token của trình biên dịch TeX để không chèn khoảng trắng giả vào giữa từ.

### Pha 2 — Bầu chọn Tệp Gốc đa tín hiệu (`elect_root_tex`)

Sau khi toàn bộ tệp `.tex` đã được xóa sạch comment (nhờ đó loại bỏ hoàn toàn bẫy `% \documentclass{article}` nằm trong dòng ghi chú), hệ thống xác định tập ứng viên chứa lệnh `\documentclass` (hoặc `\documentstyle` của LaTeX 2.09). Khi một thư mục phiên bản chứa đồng thời nhiều tệp có `\documentclass` (chẳng hạn `main.tex`, `rebuttal.tex` và các tệp hình vẽ độc lập `\documentclass[tikz]{standalone}`), hàm chấm điểm đa tín hiệu $S(f)$ được tính cho từng tệp ứng viên $f$:

$$
S(f) = 100 \cdot \mathbb{I}_{\text{doc}}(f) - 80 \cdot \mathbb{I}_{\text{sub}}(f) + 25 \cdot |\text{children}(f)| + 20 \cdot \mathbb{I}_{\text{name}}(f) + 15 \cdot \mathbb{I}_{\text{front}}(f) + \min\!\left(10,\; \frac{\text{len}(f)}{10\,000}\right)
$$

trong đó:
- $\mathbb{I}_{\text{doc}}(f) = 1$ nếu $f$ chứa môi trường `\begin{document}`;
- $\mathbb{I}_{\text{sub}}(f) = 1$ nếu lớp tài liệu là `standalone` hoặc `subfiles` (phạt nặng các tệp hình TikZ và tệp chương rời biên dịch độc lập);
- $|\text{children}(f)|$ là số lệnh nạp tệp con (`\input`, `\include`, `\subfile`, `\import`) thực sự **phân giải được sang tệp có thật** trong gói nguồn của phiên bản đó (không cộng điểm cho các lệnh `\input` trỏ tới tệp ảo hoặc tệp của dự án khác);
- $\mathbb{I}_{\text{name}}(f) = 1$ nếu tên cơ sở thuộc tập tên chuẩn học thuật `{"main.tex", "paper.tex", "ms.tex", "article.tex", "root.tex"}`;
- $\mathbb{I}_{\text{front}}(f) = 1$ nếu $f$ chứa `\maketitle` hoặc môi trường `abstract`.

Tệp đạt điểm $S(f)$ cao nhất (với thứ tự từ điển đường dẫn làm tiêu chí phá hòa tất định) được bầu chọn làm **tệp gốc xuất bản (`root_relpath`)**. Việc chỉ tính điểm $+25$ cho các lệnh nạp tệp phân giải thành công đã khắc phục triệt để các ca thực tế phức tạp trên kho dữ liệu (điển hình như bài báo `2408.11049` ở các phiên bản $v_4, v_5$, nơi thư mục nguồn chứa đồng thời hai bản thảo `.tex` hoàn chỉnh và bản thảo phụ chứa nhiều lệnh `\input` không trỏ tới tệp thật trong gói; nhờ ràng buộc phân giải đường dẫn, bộ bầu chọn chọn chính xác `2407.01856v1.tex` làm tệp gốc xuất bản). Trong trường hợp hiếm gặp khi gói nguồn chỉ gồm một tệp thân văn bản không khai báo `\documentclass` (dựa vào cơ chế ghép preamble tự động của AutoTeX trên arXiv), hệ thống tự động hạ cấp an toàn sang tệp chứa `\begin{document}` hoặc tệp `.tex` có điểm cấu trúc lớn nhất.

### Pha 3 — Mở rộng Bắc cầu DFS có Chống Chu trình (`gather_compilation_unit`)

Xuất phát từ `root_relpath`, bộ thu thập thực hiện duyệt chiều sâu (DFS) để thay thế tại chỗ (*in-place inline*) mọi lệnh nạp tệp con theo đúng thứ tự trình biên dịch LaTeX đọc mã nguồn:

- **Hỗ trợ đầy đủ biến thể cú pháp nạp tệp:** Bao gồm `\input{path}`, cú pháp TeX cổ điển cách bằng khoảng trắng `\input path`, `\include{path}` (tự động chèn ranh giới ngắt đoạn `\par` ở hai đầu theo đúng ngữ nghĩa của `\include`), `\subfile{path}` (chỉ trích phần thân bên trong `\begin{document}...\end{document}` của tệp con nếu có) và `\import{dir}{file}` / `\subimport{dir}{file}`.
- **Phân giải đường dẫn kép:** Với mỗi tham chiếu `target`, hệ thống chuẩn hóa dấu phân cách và thử tra cứu tuần tự theo thư mục của tệp gốc (`root_dir / target`, `root_dir / (target + ".tex")`) trước khi thử theo thư mục của tệp đang xét (`current_dir / target`, `current_dir / (target + ".tex")`). Nếu `target` trỏ tới tệp `.bbl` có sẵn trong kho, nội dung `.bbl` được thu nhận vào `raw_bibitems_blocks` để bảo toàn danh mục tài liệu tham khảo đã biên dịch.
- **Bảo vệ chống đệ quy vô hạn (Cycle Guard):** Duy trì ngăn xếp đường đi đang mở `active_stack` để chặn tức thì mọi chu trình nạp chéo ($A \to B \to A$) đồng thời áp trần độ sâu lồng nhau `MAX_INCLUDE_DEPTH = 15`.
- **Kiểm toán tệp dư thừa:** Mọi tệp `.tex` nằm trên cây DFS từ gốc được tính vào `used_tex_files`; các tệp `.tex` còn lại trong thư mục phiên bản được phân loại tường minh vào `unused_tex_files` (`total_tex_files = used_tex_files + unused_tex_files`), cung cấp số liệu định lượng trực tiếp cho Mục 7.1.

---

## 5.4. Xây dựng Cây Phân cấp Thích ứng & Bảo toàn Độ phủ Phiên bản (`hierarchy.py`)

Từ văn bản LaTeX đã nối phẳng trong `CompilationUnit`, module `src/parsing/hierarchy.py` phối hợp với các hàm làm sạch/tách câu (trình bày tại Chương 6) để dựng cây cú pháp trừu tượng gồm các nút `RawNode`:

### 1. Ngăn xếp Cấp bậc Đơn điệu (Dynamic Monotonic Rank Stack)

Để thích ứng với mọi cấu trúc đề mục mà không phụ thuộc vào việc bài báo dùng `\chapter` hay bắt đầu từ `\section`, hay nhảy cóc từ `\section` xuống `\paragraph`, hệ thống ánh xạ toàn bộ các lệnh phân mục chuẩn (kể cả biến thể có dấu sao `\section*{...}` và biến thể có tiêu đề rút gọn `\section[short]{long}`) vào một thang trọng số thứ tự nghiêm ngặt:

| Lệnh phân mục LaTeX | Trọng số cấp bậc (`rank`) | Loại nút sinh ra (`kind`) | Quy tắc cập nhật ngăn xếp cha (`heading_stack`) |
| :--- | :---: | :---: | :--- |
| Nút gốc phiên bản (`#root<v>`) | `-1` | `document` | Khởi tạo đáy ngăn xếp `[(root_id, -1)]` với `content = "Version <v> root"` |
| `\part`, `\part*` | `0` | `heading` | Lấy (`pop`) mọi phần tử đỉnh có `top.rank >= 0`, gắn vào `#root<v>` |
| `\chapter`, `\chapter*` | `1` | `heading` | `pop` mọi phần tử đỉnh có `top.rank >= 1`, gắn vào phần tử đỉnh mới |
| `\section`, `\section*` | `2` | `heading` | `pop` mọi phần tử đỉnh có `top.rank >= 2`, gắn vào phần tử đỉnh mới |
| `\subsection`, `\subsection*` | `3` | `heading` | `pop` mọi phần tử đỉnh có `top.rank >= 3`, gắn vào phần tử đỉnh mới |
| `\subsubsection`, `\subsubsection*` | `4` | `heading` | `pop` mọi phần tử đỉnh có `top.rank >= 4`, gắn vào phần tử đỉnh mới |
| `\paragraph`, `\paragraph*` | `5` | `heading` | `pop` mọi phần tử đỉnh có `top.rank >= 5`, gắn vào phần tử đỉnh mới |
| `\subparagraph`, `\subparagraph*` | `6` | `heading` | `pop` mọi phần tử đỉnh có `top.rank >= 6`, gắn vào phần tử đỉnh mới |

Nhờ tính chất đơn điệu tăng nghiêm ngặt của `rank` trên `heading_stack`, bất kể tác giả tổ chức đề mục sâu hay nông, cây sinh ra luôn **liên thông 100% về `#root<v>`** và phản ánh đúng quan hệ bao hàm ngữ nghĩa của bài báo. Riêng khối `\begin{abstract}...\end{abstract}` (hoặc macro `\abstract{...}` của lớp `revtex`) được chuẩn hóa thành một nút `heading` mang nội dung `"Abstract"` gắn trực tiếp dưới `#root<v>`.

### 2. Bộ lọc Ngữ nghĩa Loại trừ `References` và Bao gồm `Acknowledgements` / `Appendices`

Đề bài đặt ra quy tắc phân tách rạch ròi giữa nội dung văn bản và danh mục tài liệu tham khảo:

- **Loại trừ tuyệt đối mục Tài liệu tham khảo khỏi cây:** Mọi môi trường `\begin{thebibliography}...\end{thebibliography}` đều được cắt tách ngay lập tức để chuyển sang danh sách `raw_bibitems_blocks` cho bộ trích xuất BibTeX. Đồng thời, khi gặp bất kỳ lệnh đề mục nào có tiêu đề sau làm sạch (chữ thường, bỏ dấu hai chấm/số thứ tự) khớp với tập từ khóa `{"references", "bibliography", "literature cited", "works cited"}`, bộ dựng cây bật cờ trạng thái `in_references_section = True` và bỏ qua toàn bộ nội dung bên dưới cho tới khi gặp đề mục cùng hoặc cao cấp hơn kế tiếp (ví dụ `\appendix` đặt sau tài liệu tham khảo).
- **Bao gồm đầy đủ Lời cảm ơn và Phụ lục:** Khi gặp lệnh chuyển vùng `\appendix`, môi trường `\begin{appendices}...\end{appendices}`, hoặc các đề mục không đánh số như `\section*{Acknowledgements}`, `\section*{Acknowledgments}`, `\section*{Appendix A}`, cờ loại trừ được tắt (`in_references_section = False`) và toàn bộ đề mục, đoạn văn, công thức, bảng biểu bên trong đều được đưa đầy đủ vào cây phân cấp như các mục chính thức.

### 3. Phân nhánh Danh sách, Độ mịn Nút lá & Bảo toàn Phiên bản Rỗng

Bên dưới mỗi đề mục (`heading`), dòng văn bản được phân rã tới độ mịn nút lá theo đúng đặc tả:

1. **Danh sách liệt kê lồng nhau (`list` $\rightarrow$ `item`):** Các môi trường `itemize`, `enumerate` và `description` sinh nút trung gian `kind = "list"`; mỗi lệnh `\item` ở đúng mức lồng tương ứng sinh một nút con `kind = "item"` gắn vào `list` đó. Nội dung bên trong từng `item` tiếp tục được đệ quy phân rã thành các đoạn/câu lá, phương trình khối hoặc một `list` con cấp sâu hơn.
2. **Ba loại nút lá nội dung (`sentence`, `block_formula`, `figure`):**
   - **Hình vẽ và Bảng biểu (`kind = "figure"`):** Theo quy ước của đề bài (*Tables được xếp chung vào nhóm Figure*), toàn bộ các khối môi trường nổi `\begin{figure[*]}...`, `\begin{table[*]}...`, `\begin{wrapfigure}...` và `\begin{algorithm[*]}...` được đóng gói nguyên khối thành nút lá `figure` (sau khi đã dọn sạch các tham số vị trí `[htbp!]` và đường kẻ trình bày).
   - **Phương trình khối (`kind = "block_formula"`):** Mỗi khối `\begin{equation}...\end{equation}` (đã hợp nhất từ mọi môi trường toán trưng bày) tạo thành một nút lá độc lập gắn vào đoạn hoặc mục chứa nó.
   - **Câu văn xuôi (`kind = "sentence"`):** Phần văn bản còn lại được chia theo ranh giới đoạn trống (`\n\s*\n` hoặc `\par`) thành các nút `kind = "paragraph"`, rồi tách thành từng câu đơn `kind = "sentence"` bằng thuật toán 4 bước không cắt nhầm.
3. **Ghi nhận trung thực phiên bản không có mã nguồn TeX (`no_source` / `ok_no_tex`):** Khi điều phối viên `pipeline.py` duyệt qua `Corpus.versions(arxiv_id)` từ Milestone 1, các phiên bản chỉ có PDF biên dịch sẵn (`status != Status.OK`, ví dụ `2408.01045v1`) có `unit.root_relpath = None`. Hệ thống **không bỏ qua và không báo lỗi**, mà trả về `0` phần tử trong Parquet đồng thời tăng bộ đếm `n_versions_empty` trong `PaperStats` để tỷ lệ bao phủ phiên bản ở Chương 7 phản ánh trung thực 100% tổng số phiên bản thực tế trên arXiv.

### 4. Đối chứng Thực nghiệm trên Mẫu Thực tế Đa Phiên bản (`c_real_sample_check.json`)

Trước khi chạy trên toàn bộ kho ngữ liệu 25.000 bài báo, hai module `gathering.py` và `hierarchy.py` được kiểm chứng trực tiếp trên mẫu thực tế gồm **10 bài báo đa dạng (26 phiên bản)** trích từ phân vùng dữ liệu đã thu thập (`2408.11045`–`2408.11054`), bao gồm cả bài đơn tệp, bài đa tệp phân tầng và bài có nhiều tệp `.tex` ứng viên gốc:

- **Độ phủ phiên bản & Bầu chọn tệp gốc:** Cả `26/26` phiên bản có mã nguồn TeX đều xác định chính xác tệp gốc xuất bản (`root_relpath != None`), ghi nhận tổng cộng `67` tệp `.tex` (`34` tệp tham gia cây biên dịch `used_tex_files`, `33` tệp nháp/hình rời `unused_tex_files` được tách biệt hoàn toàn). Đặc biệt, ở `2408.11049` ($v_4, v_5$), quy tắc chỉ cộng $+25$ điểm cho các lệnh `\input` phân giải được sang tệp thật đã loại bỏ chính xác bản thảo phụ để chọn đúng `2407.01856v1.tex`.
- **Kiểm chứng bất biến cấu trúc trên cây sinh ra:** Trên toàn bộ `26/26` cây phiên bản thực tế (`5.070` nút `RawNode`), kết quả kiểm tra tự động xác nhận **0 lỗi ngoại lệ**, **100% cây có duy nhất một nút gốc `document`** (`node_id = 0`), **100% nút con liên thông về gốc không chu trình**, và **0% rò rỉ tiêu đề `References`/`Bibliography` hay lệnh `\bibitem` vào cây nội dung** (trong khi vẫn thu hồi đầy đủ các tệp `.bib` và các khối `thebibliography` sang nhánh trích xuất tài liệu tham khảo). Kết quả thực nghiệm mở rộng trên toàn bộ **25.000 bài báo (`41.629` phiên bản)** được trình bày chi tiết tại Chương 7 và Chương 8.

