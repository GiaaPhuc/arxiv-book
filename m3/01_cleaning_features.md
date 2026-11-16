# Chương 9. Tiền xử lý Thực thể & Bộ 21 Đặc trưng Đa chiều

```{admonition} Thông tin Dự án & Sản phẩm Bàn giao (Milestone 3)
:class: note
- **Giai đoạn:** Milestone 3 — Đối sánh Tài liệu Tham khảo, Xếp hạng Học máy `MRR@5` & Công bố Bộ dữ liệu Hugging Face (*Reference Matching Pipeline*).
- **Repository mã nguồn pipeline:** [`GiaaPhuc/arxiv-pipeline`](https://github.com/GiaaPhuc/arxiv-pipeline) · **Module trọng tâm:** `src/matching/*`, `src/run_matching.py`.
- **Tuân thủ phương pháp (Non-LLM & Non-Pretrained):** Toàn bộ pipeline Milestone 3 **không sử dụng mô hình ngôn ngữ lớn (LLM)** và **không sử dụng vector biểu diễn tiền huấn luyện (pretrained embeddings)** như BERT, SciBERT hay SPECTER. Hệ thống chỉ dùng chuẩn hóa chuỗi tất định, độ đo từ vựng cổ điển (`rapidfuzz`), TF-IDF cục bộ theo từng bài báo, đặc trưng cây phân cấp AST từ Milestone 2, `LogisticRegression` và `LightGBM LambdaMART` huấn luyện từ đầu.
- **Nguyên tắc liêm chính dữ liệu:** Toàn bộ bảng tổng hợp và biểu đồ trực quan ở Chương 11 và Chương 12 được tính toán và kết xuất tự động bằng Python khi biên dịch sách (`jupyter-book build .`) từ thư mục `stats/m3/` (kết quả chạy thực nghiệm trên dải `range_0`: `2408.11045`–`2408.16044`, 5.000 ID).
```

## 9.1. Bài toán Phân giải Thực thể Học thuật & Luồng Xử lý 6 Chặng

Tiếp nối nguồn dữ liệu thô thu thập ở Milestone 1 và kho ngữ liệu có cấu trúc ở Milestone 2, **Milestone 3** giải quyết bài toán **phân giải thực thể trích dẫn** (*citation entity resolution*): liên kết từng mục tài liệu tham khảo `bibtex` trích xuất từ mã nguồn LaTeX/BibTeX (Milestone 2) về đúng bản ghi tham khảo mang `ref_arxiv_id` trong bảng `references` thu thập từ Semantic Scholar (Milestone 1) của **cùng một công bố**.

Xét một công bố $p$ sở hữu $m$ mục trong bảng `bibtex` và $n$ tham khảo ứng viên có `arXiv ID` trong bảng `references`. Không gian đối sánh của công bố $p$ là ma trận nhị phân $m \times n$, trong đó mỗi mục BibTeX $b_i$ đóng vai trò một **truy vấn (query)** và mỗi tham khảo $r_j$ là một **ứng viên (candidate)**:

- **Ràng buộc mỗi hàng (At-most-one Positive):** Mỗi mục BibTeX $b_i$ khớp với **tối đa một** ứng viên $r_j$ thực sự tồn tại trên arXiv; tất cả $(n - 1)$ ứng viên còn lại của dòng đó đều mang nhãn âm (`label = 0`).
- **Sự phổ biến của truy vấn toàn âm (*Negative-Only Queries*):** Các công bố học thuật trích dẫn rất nhiều sách chuyên khảo, kỷ yếu hội nghị không phát hành bản thảo trên arXiv, tiêu chuẩn kỹ thuật hoặc tài liệu phần mềm (`scipy`, chuẩn IEEE, sách giáo trình). Trong thực nghiệm trên dải `range_0`, có tới **68,30%** số mục BibTeX (`18.412 / 26.959` truy vấn) là truy vấn toàn âm (`groundtrutharxivid = None`), đặt ra thách thức lớn cho cả bước huấn luyện hàm mất mát xếp hạng lẫn cách đọc chỉ số `MRR@5`.
- **Bất đối xứng dữ liệu hai đầu vào:** Dữ liệu từ `bibtex` mang dấu ấn cú pháp TeX (`{BERT}`, `\'e`, `\"o`), đôi khi chỉ chứa tên tạp chí hoặc viết tắt họ tên (`"Vaswani, Ashish"` hoặc `"A. Vaswani"`), và `year` có thể phản ánh năm xuất bản hội nghị/tạp chí chính thức. Ngược lại, `references` từ Semantic Scholar lưu văn bản Unicode thuần (`"Ashish Vaswani"`), không có cột `doi` hay `year` tách riêng trong lược đồ Parquet khóa cứng (năm phải trích từ `ref_submission_date[:4]`, có thể lệch 1–2 năm so với năm đăng tạp chí).

Để nối thông liền mạch dữ liệu từ cả Milestone 1 và Milestone 2 mà không gây tràn bộ nhớ hay rò rỉ dữ liệu kiểm thử, hàm `run_matching_pipeline` trong `src/matching/pipeline.py` điều phối qua **6 chặng tuần tự**:

<div class="pipeline-flow" role="region" aria-label="Sơ đồ Luồng Xử lý Đối sánh Tham chiếu Milestone 3">
  <div class="pf-endpoint-node pf-input">
    <span class="pf-icon">&#128218;</span>
    <span>Đầu vào hợp nhất: M1 (<code>references</code>, <code>s2_references.raw.json.gz</code>) + M2 (<code>bibtex</code>, <code>elements</code>, <code>hierarchy</code>)</span>
  </div>
  <div class="pf-connector" aria-hidden="true">
    <svg width="20" height="24" viewBox="0 0 20 24" fill="none">
      <line x1="10" y1="0" x2="10" y2="17" stroke="currentColor" stroke-width="1.8"/>
      <path d="M5 14L10 21L15 14" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
  </div>
  <div class="pf-stage-card pf-stage-arxiv">
    <div class="pf-stage-header">
      <div class="pf-stage-title">
        <span class="pf-stage-dot"></span>
        <span>Chặng 1 &amp; 2 — Lọc Dải ID &amp; Tiền xử lý Một lần Mỗi Bài (<code>cleaner.py</code>)</span>
      </div>
      <span class="pf-rate-badge">--range-index &lt;0..4 | all&gt;</span>
    </div>
    <div class="pf-steps-grid">
      <div class="pf-step-item">
        <span class="pf-step-num">1</span>
        <div class="pf-step-body">
          <strong>Nạp phân mảnh &amp; làm giàu DOI cục bộ</strong>
          <span>Đọc streaming bảng <code>bibtex</code> và <code>references</code> theo <code>src/id_ranges.csv</code>; nạp bổ sung <code>externalIds.DOI</code> từ <code>s2_references.raw.json.gz</code> (nếu có)</span>
        </div>
      </div>
      <div class="pf-step-item">
        <span class="pf-step-num">2</span>
        <div class="pf-step-body">
          <strong>Pre-cleaning trong &Oscr;(m + n)</strong>
          <span>Giải mã dấu TeX, NFKD ASCII folding, tách <code>AuthorTokens</code> &amp; trích xuất mỏ neo arXiv ID/DOI đúng 1 lần qua <code>PrecleanedBib</code> / <code>PrecleanedRef</code></span>
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
  <div class="pf-stage-card pf-stage-extract">
    <div class="pf-stage-header">
      <div class="pf-stage-title">
        <span class="pf-stage-dot"></span>
        <span>Chặng 3 &amp; 4 — Gán nhãn Hai tầng, Chia tập &amp; Trích xuất 21 Đặc trưng</span>
      </div>
      <span class="pf-rate-badge">labelling &middot; auto_matcher &middot; features</span>
    </div>
    <div class="pf-steps-grid">
      <div class="pf-step-item">
        <span class="pf-step-num">3</span>
        <div class="pf-step-body">
          <strong>Manual Gold + Auto-Matcher + Split cấp bài</strong>
          <span>Gán nhãn tay (&ge;5 bài) + heuristic 3 tầng (&ge;10% bài còn lại) + kiểm toán P/R/F1; chia <code>train/valid/test</code> theo <code>arxivid</code> (<code>seed=42</code>)</span>
        </div>
      </div>
      <div class="pf-step-item">
        <span class="pf-step-num">4</span>
        <div class="pf-step-body">
          <strong>Stage-1 Blocking &amp; 21 Đặc trưng Đa chiều</strong>
          <span>Nạp AST M2 chỉ cho các bài trong <code>splits</code>; chạy <code>rapidfuzz.cdist</code> blocking khi n &gt; 50; ghép 15B + 3E + 3A thành <code>MatchFeatures</code></span>
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
        <span>Chặng 5 &amp; 6 — Xếp hạng LambdaMART, Đánh giá MRR@5 &amp; Đóng gói Hugging Face</span>
      </div>
      <span class="pf-rate-badge">ranker &middot; evaluation &middot; export_hf</span>
    </div>
    <div class="pf-steps-grid pf-steps-3">
      <div class="pf-step-item">
        <span class="pf-step-num">5</span>
        <div class="pf-step-body">
          <strong>Weighted LambdaMART &amp; Top-5</strong>
          <span>Huấn luyện trên nhóm dương (Manual=3, Auto=1), ưu tiên Hard Anchor, khử trùng &amp; đệm <code>None</code></span>
        </div>
      </div>
      <div class="pf-step-item">
        <span class="pf-step-num">6a</span>
        <div class="pf-step-body">
          <strong>Đánh giá Đa chiều &amp; Ablation</strong>
          <span>Đo <code>MRR@5</code> (all &amp; matchable), 4 mô hình, Ablation 18 vs 21 đặc trưng M2 &amp; đồ thị 300 DPI</span>
        </div>
      </div>
      <div class="pf-step-item">
        <span class="pf-step-num">6b</span>
        <div class="pf-step-body">
          <strong>Xuất 6 bảng ZSTD Hugging Face</strong>
          <span>Đóng gói shard &le; 80 MB, sinh Dataset Card YAML &amp; kiểm chứng <code>datasets.load_dataset</code></span>
        </div>
      </div>
    </div>
  </div>
  <div class="pf-connector" aria-hidden="true">
    <svg width="20" height="24" viewBox="0 0 20 24" fill="none">
      <line x1="10" y1="0" x2="10" y2="17" stroke="currentColor" stroke-width="1.8"/>
      <path d="M5 14L10 21L15 14" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
  </div>
  <div class="pf-endpoint-node pf-output">
    <span class="pf-icon">&#10003;</span>
    <span>Đầu ra: <code>predictions.parquet</code>, <code>evaluation_results.json</code>, <code>figures/*.png</code> &amp; <code>hf_range_&lt;k&gt;/</code></span>
  </div>
</div>

### Thống nhất Khóa Liên kết Giữa 3 Cột mốc (`src/matching/models.py`)

Hợp đồng dữ liệu trong `src/matching/models.py` (`SCHEMA_VERSION = 1`) bảo đảm sự đồng bộ tuyệt đối giữa 3 bảng đầu vào/đầu ra có tên cột khóa khác nhau:

| Thành phần dữ liệu | Nguồn gốc | Khóa bài báo | Khóa định danh con / ứng viên | Quy tắc chuẩn hóa khóa trong `matching/` |
| :--- | :---: | :--- | :--- | :--- |
| `papers` | M1 (`crawler/export.py`) | `arxiv_id` | — | Ánh xạ về `base_arxiv_id` khi lọc theo dải 5.000 ID |
| `references` | M1 (`crawler/export.py`) | `arxiv_id` | `ref_arxiv_id` | Chuẩn hóa `norm_arxiv_id` để so khớp; giữ nguyên `raw_ref_arxiv_id` (gồm cả hậu tố `vN` nếu có) khi ghi đáp án/dự đoán |
| `elements`, `hierarchy` | M2 (`parsing/export_m2.py`) | `arxivid` | `elementid`, `version`, `parentid` | Chỉ nạp cho các bài thuộc `splits` (`train`, `valid`, `test`) để tiết kiệm RAM |
| `bibtex` | M2 (`parsing/export_m2.py`) | `arxivid` | `citationkey` | Khóa truy vấn duy nhất `(arxivid, citationkey)` bên trong từng công bố |
| `predictions` | M3 (`matching/pipeline.py`) | `arxivid` | `citationkey`, `cand1`–`cand5` | Chỉ gồm các bài nằm trong `train`, `valid`, `test`; giữ nguyên văn `groundtrutharxivid` |

---

## 9.2. Tiền xử lý Thực thể Một lần Mỗi Bài báo (`src/matching/cleaner.py`)

Nếu thực hiện giải mã LaTeX và tách tên tác giả lặp lại bên trong vòng lặp cặp $m \times n$, chi phí CPU sẽ tăng lên $\mathcal{O}(m \cdot n)$. Module `src/matching/cleaner.py` chuyển toàn bộ khâu làm sạch sang tiền xử lý đúng một lần mỗi bản ghi (`preclean_bibtex` và `preclean_reference`), giảm độ phức tạp xuống $\mathcal{O}(m + n)$ qua bốn bước tất định:

1. **Giải mã Dấu Phụ & Ngoặc Nhọn LaTeX (`decode_latex`):**
   - Sử dụng bộ quét ngoặc cân bằng `_group(s, start)` thay cho biểu thức chính quy xóa ngoặc thô để bảo toàn cấu trúc lồng nhau và không ăn mất chữ cái sau lệnh.
   - Chuyển đổi bảng 15 dấu phụ LaTeX `_ACCENTS` (như `\'e` $\rightarrow$ `é`, `\"a` $\rightarrow$ `ä`, `\c{c}` $\rightarrow$ `ç`, `\v{s}` $\rightarrow$ `š`, `\H{o}` $\rightarrow$ `ő`) và bảng ký hiệu `_SYMBOLS` (`\ae`, `\oe`, `\o`, `\l`, `\ss`, `\textendash`...), bóc vỏ các lệnh định dạng kiểu chữ (`\textbf`, `\textit`, `\emph`, `\textrm`, `\mathrm`, `\textsc`) và chuẩn hóa tổ hợp Unicode về `NFC`.
2. **Gấp Bảng mã ASCII & Chuẩn hóa Tiêu đề (`_ascii_fold`, `clean_title`):**
   - Bảng ánh xạ tường minh các ký tự Latin mở rộng mà `NFKD` không tự phân rã (`ø` $\rightarrow$ `o`, `ß` $\rightarrow$ `ss`, `ł` $\rightarrow$ `l`, `æ` $\rightarrow$ `ae`, `œ` $\rightarrow$ `oe`, `đ` $\rightarrow$ `d`, `ı` $\rightarrow$ `i`).
   - Áp dụng chuẩn hóa `NFKD`, loại bỏ dấu tổ hợp (*combining marks*), chuyển chữ thường, đổi dấu câu thành khoảng trắng (`_PUNCT`) và tạo thêm bộ token nội dung `title_tokens_nostop` loại bỏ 12 hư từ học thuật đầu/cuối (`a`, `an`, `the`, `on`, `for`, `with`, `of`, `in`, `to`, `towards`, `via`, `using`).
3. **Phân tách Tác giả Đa văn hóa (`extract_author_tokens` $\rightarrow$ `AuthorTokens`):**
   - Làm sạch chuỗi rác cuối danh sách (`"et al."`, `"others"`, `"and others"`, `"collaboration"`).
   - Hỗ trợ đồng thời cả định dạng đảo `"Họ, Tên Tên_đệm"` lẫn định dạng xuôi `"Tên Tên_đệm Họ"`. Khi gặp dạng xuôi, thuật toán quét ngược qua tập 14 tiểu từ họ ghép `_SURNAME_PARTICLES` (`van`, `von`, `der`, `den`, `de`, `del`, `di`, `da`, `al`, `la`, `le`, `du`, `mac`, `mc`) để giữ nguyên họ phức hợp như `van der Waals` hay `de la Vallée`.
   - Trả về cấu trúc `AuthorTokens(surnames, surname_initials, first_surname, first_initial, count)` phục vụ cả khớp chính xác họ tác giả đầu lẫn đối chiếu chữ cái đầu tên riêng.
4. **Chuẩn hóa Định danh Mỏ neo & Thời gian (`normalize_arxiv_id`, `normalize_doi`, `_year`):**
   - `normalize_arxiv_id`: hỗ trợ bóc tiền tố `arxiv:`, URL `arxiv.org/abs/...` và `arxiv.org/pdf/...`, loại bỏ hậu tố `.pdf` và hậu tố phiên bản `vN` (`2408.11045v2` $\rightarrow$ `2408.11045`), đồng thời bảo toàn nguyên văn mã phân loại cũ trước năm 2007 (`hep-th/9901001`).
   - `_arxiv_from_bib`: tìm mỏ neo arXiv ID theo thứ tự trường `arxiv_id` $\rightarrow$ `eprint` $\rightarrow$ `url` $\rightarrow$ trích mẫu `arXiv:` / `10.48550/arXiv.` bên trong `doi` và `journal`.
   - `_year`: trích 4 chữ số năm hợp lệ (`1000..2200`) từ `bib.year` hoặc `ref_submission_date`, giữ `None` khi thiếu để các hàm đặc trưng tuyệt đối không suy đoán hay mặc định trùng năm.

---

## 9.3. Kỹ thuật 21 Đặc trưng Đa chiều & Khai thác Cấu trúc AST Milestone 2

Toàn bộ vector đặc trưng biểu diễn một cặp `(BibtexRow, Reference)` được khóa cứng trong `FEATURE_COLUMNS` (`src/matching/models.py`) gồm **21 đặc trưng** phối hợp từ ba module chuyên biệt: **15 đặc trưng cặp** (`src/matching/lexical_features.py` — vai B), **3 đặc trưng ngữ cảnh cấu trúc AST từ Milestone 2** (`src/matching/hierarchy_features.py` — vai E), và **3 đặc trưng tương đối cấp truy vấn cùng cơ chế Stage-1 Blocking** (`src/matching/features.py` — vai A).

### Bảng Đặc tả Chính thức 21 Đặc trưng (`FEATURE_COLUMNS`)

| # | Tên đặc trưng | Kiểu & Miền | Nhóm (Owner) | Công thức / Định nghĩa & Biện minh Khoa học |
| :-: | :--- | :---: | :--- | :--- |
| 1 | `title_exact_match` | `int` `{0, 1}` | Tiêu đề (**B**) | `1` nếu `bib.clean_title == ref.clean_title` (khác rỗng). Tín hiệu đồng nhất tuyệt đối sau chuẩn hóa LaTeX/ASCII. |
| 2 | `title_levenshtein_ratio` | `float` `[0, 1]` | Tiêu đề (**B**) | `rapidfuzz.fuzz.ratio(a, b) / 100.0`. Đo khoảng cách chỉnh sửa mức ký tự, bắt tốt lỗi chính tả hoặc sai khác số ít/nhiều. |
| 3 | `title_token_sort_ratio` | `float` `[0, 1]` | Tiêu đề (**B**) | `rapidfuzz.fuzz.token_sort_ratio(a, b) / 100.0`. Bất biến theo thứ tự từ, chống nhiễu khi đảo cụm phụ đề hoặc dấu gạch nối. |
| 4 | `title_jaccard_word_3gram` | `float` `[0, 1]` | Tiêu đề (**B**) | Hệ số Jaccard trên tập 3-gram từ của `clean_title` (tiêu đề $< 3$ từ lùi về toàn bộ tuple từ). Phạt mạnh các cụm từ ghép sai trật tự cục bộ. |
| 5 | `title_tfidf_cosine` | `float` `[0, 1]` | Tiêu đề (**B**) | Độ tương đồng Cosine từ `TfidfVectorizer(analyzer="char", ngram_range=(3, 5))` huấn luyện **nội bộ trên tập tiêu đề không nhãn của chính bài báo đó** (không bao giờ fit xuyên bài $\rightarrow$ **0% rò rỉ dữ liệu**). |
| 6 | `title_length_ratio` | `float` `[0, 1]` | Tiêu đề (**B**) | $\min(\lvert a\rvert, \lvert b\rvert) / \max(\lvert a\rvert, \lvert b\rvert)$ (`0` nếu rỗng). Ngăn hiện tượng tiêu đề ngắn hoặc tên tạp chí rỗng khớp nhầm với tiêu đề đầy đủ. |
| 7 | `first_author_surname_match` | `int` `{0, 1}` | Tác giả (**B**) | `1` nếu `bib.authors.first_surname == ref.authors.first_surname` (khác rỗng). Lọc nhiễu mạnh vì thứ tự tác giả đầu hiếm khi đổi giữa preprint và bản đăng chính thức. |
| 8 | `first_author_initial_match` | `int` `{0, 1}` | Tác giả (**B**) | `1` nếu cả họ lẫn chữ cái đầu tên tác giả thứ nhất đều khớp (`first_surname_match == 1` và `first_initial` trùng). Giải quyết xung đột ở các họ phổ biến (`Zhang`, `Wang`, `Li`, `Smith`). |
| 9 | `authors_jaccard_sim` | `float` `[0, 1]` | Tác giả (**B**) | Độ tương đồng Jaccard giữa hai tập họ tác giả `bib.authors.surnames` và `ref.authors.surnames`. Phản ánh mức độ trùng khớp toàn bộ nhóm tác giả. |
| 10 | `author_count_diff` | `int` `>= 0` | Tác giả (**B**) | `abs(bib.authors.count - ref.authors.count)` khi cả hai đều $> 0$; gán giá trị sentinel `99` nếu một bên khuyết danh sách tác giả. |
| 11 | `year_diff` | `int` `>= 0` | Thời gian (**B**) | `abs(bib.year - ref.year)` khi cả hai có năm hợp lệ; gán `999` khi thiếu năm để mô hình cây nhận diện rõ trường hợp thiếu dữ liệu. |
| 12 | `year_match` | `int` `{0, 1}` | Thời gian (**B**) | `1` nếu đủ cả hai năm và `year_diff == 0`; `0` trong mọi trường hợp còn lại. |
| 13 | `year_missing` | `int` `{0, 1}` | Thời gian (**B**) | `1` nếu `bib.year is None` hoặc `ref.year is None`. Tách rành mạch giá trị `year_diff = 999` khỏi chênh lệch năm thật khi rẽ nhánh cây quyết định. |
| 14 | `arxiv_id_in_bib_text` | `int` `{0, 1}` | Mỏ neo (**B**) | `1` nếu `extracted_arxiv_id == norm_arxiv_id`. Tín hiệu định danh trực tiếp chính xác gần như tuyệt đối. |
| 15 | `doi_exact_match` | `int` `{0, 1}` | Mỏ neo (**B**) | `1` nếu `bib.norm_doi == ref.norm_doi` (với DOI làm giàu từ `s2_references.raw.json.gz`), hoặc `bib.norm_doi == "10.48550/arxiv." + norm_arxiv_id`. |
| 16 | `cite_frequency` | `int` `>= 0` | AST M2 (**E**) | Tổng số lần `citationkey` xuất hiện trong thân bài viết (đếm qua `_CITE_CMD_RE` trên các nút lá/đề mục ở phiên bản mới nhất). Các bài báo nền tảng được trích dẫn lặp lại nhiều lần thường là preprint arXiv kinh điển. |
| 17 | `first_cite_section_type` | `int` `-1..3` | AST M2 (**E**) | Nhóm mục ngữ nghĩa chứa lần trích dẫn đầu tiên: `-1` (không có AST / không thấy `\cite`), `0` (Abstract/Introduction/Overview), `1` (Related Work/Background/Preliminaries), `2` (Method/Model/Experiment/Evaluation), `3` (Conclusion/Appendix/Acknowledgements/Other). |
| 18 | `first_cite_section_depth` | `int` `>= 0` | AST M2 (**E**) | Độ sâu trên đồ thị cây từ gốc `#root<v>` tới nút chứa lần trích dẫn đầu tiên (`0` nếu khuyết AST). Phản ánh vị trí cấu trúc (mục chính nông vs chú thích phụ sâu). |
| 19 | `title_sim_rank_in_query` | `int` `>= 1` | Tương đối (**A**) | Thứ hạng giảm dần (`1` = cao nhất) của `title_token_sort_ratio` trong tập ứng viên của cùng một `citationkey`. |
| 20 | `title_sim_diff_from_max` | `float` `<= 0` | Tương đối (**A**) | Độ lệch `sim - max_k(sim_k)` so với ứng viên có điểm tiêu đề cao nhất trong truy vấn. Tín hiệu chuẩn hóa nội bộ truy vấn cực mạnh cho mô hình cây xếp hạng. |
| 21 | `title_sim_margin_to_top2` | `float` `>= 0` | Tương đối (**A**) | Khoảng cách `top1_sim - top2_sim` giữa hai ứng viên dẫn đầu trong truy vấn (hoặc `top1_sim` nếu chỉ có 1 ứng viên). Đo độ rõ ràng của ứng viên đứng đầu. |

### Khai thác Đồ thị Phân cấp AST Milestone 2 (`src/matching/hierarchy_features.py`)

Thay vì lặp lại thao tác duyệt cây $m$ lần cho $m$ mục BibTeX của một bài báo, hàm `build_paper_citation_index(elements, hierarchy, version_strategy="latest")` xây dựng chỉ mục `PaperCitationIndex` đúng **một lần mỗi bài** trong thời gian tuyến tính $\mathcal{O}(|E| + |H|)$:

1. **Chọn phiên bản mới nhất (`max(version)`):** Trong bảng `hierarchy` đa phiên bản của Milestone 2, bộ lập chỉ mục chọn phiên bản cao nhất hiện có (`target_version = max(version)`) để phản ánh đúng trạng thái hoàn chỉnh nhất của bản thảo mà không đếm trùng qua các phiên bản cũ $v_1 \dots v_{N-1}$.
2. **Duyệt tiền tự lặp (*Iterative DFS*) bảo toàn thứ tự đọc:** Dựng danh sách kề `children_of` và duyệt DFS theo đúng thứ tự con trong bản thảo, đồng thời kế thừa loại đề mục tổ tiên (`curr_sec`) thông qua `classify_heading_section_type()`. Cách gắn nhãn ngay thời điểm bật khỏi ngăn xếp (*on-pop*) bảo đảm các nút dùng chung trong DAG không bị kế thừa nhầm ngữ cảnh từ nhánh sau.
3. **Chỉ quét nút lá & đề mục tránh đếm lặp:** Vì các nút trung gian như `paragraph` hoặc `list` trong Milestone 2 tổng hợp văn bản của các câu con, bộ chỉ mục chỉ quét lệnh `\cite` trên các nút thuộc `{sentence, block_formula, figure, heading}` (hoặc nút không có con), bỏ qua các vùng nguyên văn (`verbatim`, `Verbatim`, `lstlisting`, `minted`, `\verb`), và nhận diện đầy đủ cả 10 họ lệnh trích dẫn chuẩn khớp với `src/parsing/validate_m2.py` (`\cite`, `\citet`, `\citep`, `\citealt`, `\citealp`, `\citeauthor`, `\citeyear`, `\parencite`, `\textcite`, `\autocite` kèm dạng `*` và `[]`).
4. **Tra cứu $O(1)$ kèm dự phòng an toàn:** Hàm `extract_hierarchy_features()` tra cứu không phân biệt hoa/thường theo `citationkey`, và tự động trả về bộ giá trị trung tính `(0, -1, 0)` cho các bài không có mã nguồn TeX (`no_source`) hoặc trường hợp hiếm gặp khi mục BibTeX chưa từng được gọi bằng `\cite` trong thân bài.

### Stage-1 Blocking Cho Bài Nhiều Tham khảo (`src/matching/features.py`)

Khi một bài báo tổng quan (*survey*) có hàng trăm tham khảo arXiv ($n > 50$), việc tính đầy đủ toàn bộ 21 đặc trưng cho $m \times n$ cặp sẽ làm bùng nổ số dòng đặc trưng một cách không cần thiết. Hàm `extract_paper_features` áp dụng chiến lược **tính chính xác toàn bộ khi $n \le 50$**, và chỉ kích hoạt **Stage-1 Blocking** khi $n > \text{blocking\_threshold\_n}$ (`50`):

- Tính ma trận tương đồng chữ cái `rapidfuzz.process.cdist(..., scorer=fuzz.QRatio, workers=1)` ở tầng C++.
- Với từng mục BibTeX $b_i$, chỉ giữ lại **hợp (union)** của 3 tập ứng viên:
  1. Mọi ứng viên thỏa mãn **Hard Anchor** (`extracted_arxiv_id` khớp hoặc `norm_doi` khớp);
  2. Mọi ứng viên trùng **họ tác giả đầu** (`ref.authors.first_surname == bib.authors.first_surname`);
  3. **Top-20** ứng viên có điểm `fuzz.QRatio` cao nhất trên tiêu đề.

Cơ chế hợp 3 nguồn này vừa giữ tập cặp ứng viên cô đọng (trung bình $\approx 19{,}3$ cặp/truy vấn trên `range_0`: `519.700` cặp cho `26.959` truy vấn), vừa bảo toàn tỷ lệ hồi tưởng (*recall*) ngay cả khi tiêu đề BibTeX bị rút gọn hoặc sai lệch năm xuất bản.
