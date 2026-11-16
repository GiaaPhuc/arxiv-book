# Chương 10. Gán nhãn Hai tầng, Học máy Xếp hạng `LambdaMART` & Đóng gói Hugging Face

Nếu Chương 9 giải quyết bài toán chuẩn hóa thực thể và xây dựng không gian 21 đặc trưng đầu vào, thì Chương 10 trình bày ba cấu phần quyết định chất lượng mô hình và sản phẩm nộp cuối khóa của Milestone 3: **khung gán nhãn ground truth hai tầng có kiểm toán**, **mô hình học máy xếp hạng `LightGBM LambdaMART`** cùng quy tắc hậu xử lý Top-5, và **kiến trúc đóng gói 6 bảng Sharded Parquet** chuẩn Hugging Face Hub.

---

## 10.1. Khung Gán nhãn Ground Truth Hai tầng & Chia tập Chống Rò rỉ (`labelling.py`, `auto_matcher.py`)

Đề bài Milestone 3 quy định mỗi bộ dữ liệu công bố cần kết hợp cả **nhãn thủ công chuẩn vàng** ($\ge 5$ công bố, mỗi công bố $\ge 20$ mục BibTeX, tổng $\ge 100$ mục) lẫn **nhãn tự động dựa trên heuristic cổ điển** ($\ge 10\%$ số công bố ngoài tập thủ công, gán đủ 100% mục BibTeX của các công bố được chọn). Nhóm hiện thực hóa quy trình này qua hai module tách biệt trong `src/matching/`:

### 1. Gán nhãn Thủ công Tương tác & Đo Độ đồng thuận Liên người gán (`src/matching/labelling.py`)

Công cụ CLI `python -m matching.labelling --range-index <0..4> --data-dir data` hỗ trợ quy trình gán nhãn có thể tạm dừng và tiếp tục an toàn trên từng dải 5.000 ID:

- **Lọc bài đủ điều kiện:** Tự động liệt kê các bài trong dải sở hữu đồng thời $\ge 20$ mục BibTeX và $\ge 5$ tham khảo có arXiv ID trong bảng `references`.
- **Giao diện gợi ý thông minh & Lưu nguyên tử:** Khi gán từng mục BibTeX, CLI hiển thị toàn văn siêu dữ liệu gốc (`title`, `authors`, `year`, `doi`, `url`) kèm **Top-5 ứng viên** sắp xếp theo `fuzz.token_sort_ratio`, hỗ trợ gõ `all` để duyệt toàn bộ danh sách ứng viên của bài hoặc `0` để xác nhận truy vấn toàn âm (`groundtrutharxivid = null`). Mọi lựa chọn đều được ghi nguyên tử ngay lập tức qua `atomic_write` vào `data/groundtruth/range_<k>/manual_annotations.json`; các mục chưa xem tuyệt đối không tự sinh `null` nếu người dùng bấm `q` hoặc ngắt giữa chừng.
- **Cổng nghiệm thu tự động (`manual_pool_ready`):** CLI chỉ xác nhận tập nhãn thủ công sẵn sàng khi thỏa đồng thời: đủ $\ge 5$ bài hoàn chỉnh 100% mục BibTeX, mỗi bài $\ge 20$ mục, tổng $\ge 100$ mục, và có ít nhất **`2` bài đạt chuẩn đánh giá (`qualified_eval_papers >= 2`)** — tức mỗi bài chứa tối thiểu **3 nhãn dương** và **3 nhãn âm** để đưa vào tập `valid` và `test` không bị suy biến.
- **Đo độ tin cậy liên người gán (`compute_cohens_kappa`):** Hỗ trợ cờ `--compare-path` đối chiếu độc lập hai tệp nhãn thủ công trên cùng tập khóa `(arxivid, citationkey)` (chuẩn hóa ID về dạng không kèm hậu tố phiên bản khi so khớp danh mục, xem `None` là một nhãn hợp lệ), xuất chỉ số Cohen's Kappa ($\kappa$) ra `kappa.json`.

### 2. Bộ Đối sánh Tự động Bảo thủ 3 Tầng & Kiểm toán P/R/F1 (`src/matching/auto_matcher.py`)

Thay vì dùng một ngưỡng tương đồng đơn giản dễ sinh nhãn dương giả (làm mô hình học máy học sai tín hiệu), bộ đối sánh tự động `_match(bib, candidates)` áp dụng **thác quyết định 3 tầng ưu tiên độ chính xác (High-Precision Cascade)** trên dữ liệu đã tiền xử lý:

1. **Tầng 3 — Mỏ neo arXiv ID (`bib.extracted_arxiv_id`):** Khớp trực tiếp `base_arxiv_id` với tập ứng viên đã khử trùng lặp phiên bản của chính bài báo đó.
2. **Tầng 2 — Mỏ neo DOI chính xác (`bib.norm_doi`):** Khớp chuẩn xác trên mã DOI (kể cả DOI thu hồi từ `s2_references.raw.json.gz`). Nếu nhiều ứng viên cùng trùng DOI gây nhập nhằng, hệ thống phát cảnh báo và từ chối gán nhãn (`None`) thay vì đoán ngẫu nhiên.
3. **Tầng 1 — Khớp Chuỗi Nghiêm ngặt Có Bảo vệ Khuyết Năm:** Chỉ kích hoạt khi ứng viên vượt qua hàng loạt chốt chặn chi phí thấp:
   - Cùng **họ tác giả đầu** (`ref.authors.first_surname == bib.authors.first_surname`, khác rỗng);
   - Tỷ lệ độ dài tiêu đề `min(len_a, len_b) / max(len_a, len_b) >= 0,70`;
   - Kiểm tra năm nhất quán: nếu **đủ cả hai năm** thì bắt buộc `|bib.year - ref.year| <= 1` và `fuzz.token_sort_ratio >= 0,94`; nếu **thiếu một trong hai năm**, siết chặt ngưỡng tiêu đề lên **`>= 0,97`**;
   - Nếu có nhiều ứng viên đồng hạng cao nhất trên cùng một mục BibTeX, trả về `None` để tránh gán nhầm.
4. **Giải quyết xung đột 1-nhiều nội bộ bài báo (`run_auto_matcher`):** Nếu hai mục BibTeX khác nhau trong cùng một bài báo cùng trỏ về một `ref_arxiv_id` duy nhất, bộ điều phối giữ lại mục có thứ tự ưu tiên cao hơn theo khóa `(-tier, -title_score, citationkey)` (ưu tiên bậc `tier` cao hơn, điểm tiêu đề cao hơn, và khóa `citationkey` nhỏ hơn theo từ điển) rồi đặt mục yếu hơn thành `None` kèm cảnh báo log.
5. **Kiểm toán định lượng trực tiếp trên Manual Gold (`audit_auto_matcher`):** Trước khi tin dùng nhãn tự động cho huấn luyện, hệ thống chạy chính `run_auto_matcher` lên toàn bộ các bài **Manual Gold**, đo đạc Precision, Recall và F1 ở cấp liên kết (một liên kết đoán dương nhưng sai đích arXiv ID bị phạt đồng thời cả `FP` lẫn `FN`). Trên dải `range_0` (`114` truy vấn thủ công), bộ đối sánh tự động đạt **Precision = 100,00%** (`FP = 0`) với **Recall = 65,12%** và **F1 = 78,87%**.

### 3. Chiến lược Chia tập Cấp Bài báo (`create_dataset_splits`)

Một lỗi rò rỉ dữ liệu (*data leakage*) phổ biến trong bài toán đối sánh thực thể là chia `train/valid/test` theo từng dòng cặp `(bib, ref)` hoặc từng mục BibTeX, khiến ứng viên tham khảo của cùng một bài xuất hiện đồng thời ở cả `train` và `test`. Hàm `create_dataset_splits(..., seed=42)` bắt buộc **chia tập ở cấp công bố (`arxivid`)**:

- **Ràng buộc chọn bài đánh giá:** Chỉ các bài có $\ge 20$ mục BibTeX, $\ge 3$ nhãn dương và $\ge 3$ nhãn âm mới đủ điều kiện vào `test` hoặc `valid` (từ chối thẳng nếu thiếu, không có cơ chế nới lỏng ngầm).
- **Cấu trúc 3 phân vùng chuẩn đề bài:** Trong từng dải 5.000 ID, rút ngẫu nhiên tất định (`seed=42`) đúng **1 bài thủ công + 1 bài tự động** cho `test`, **1 bài thủ công + 1 bài tự động** cho `valid`, và toàn bộ các bài còn lại đưa vào `train`. Nhãn `groundtrutharxivid` gốc (bao gồm hậu tố phiên bản nếu có, ví dụ `1706.03762v2`) được giữ nguyên tuyệt đối; pipeline chỉ cập nhật lại trường `partition` theo ánh xạ trong `splits.json`.

---

## 10.2. Mô hình Xếp hạng `LightGBM LambdaMART`, Đối chứng Baselines & Hậu xử lý Top-5

### 1. Vì sao chọn Learning-to-Rank (`LambdaMART`) thay vì Phân loại Điểm đơn lẻ?

Bài toán của đề bài yêu cầu xuất danh sách xếp hạng **Top-5 ứng viên (`cand1..cand5`)** bên trong phạm vi ứng viên của từng mục BibTeX và chấm điểm bằng **`MRR@5`**. Trong thiết lập đó, thứ tự tương đối giữa các ứng viên thuộc cùng một truy vấn quan trọng hơn xác suất nhị phân tuyệt đối trên toàn cục:

- Với các truy vấn khó (ví dụ tiêu đề BibTeX thiếu chữ hoặc tên tác giả bị rút gọn), một bộ phân loại điểm (*pointwise Logistic Regression*) có thể gán xác suất thấp cho mọi ứng viên và đánh mất tương quan nội bộ truy vấn.
- Ngược lại, **`LGBMRanker` (`objective="lambdarank"`, `metric="ndcg"`, theo dõi `eval_at=[1, 3, 5]` khi bật dừng sớm)** tối ưu trực tiếp các cặp ứng viên trong từng nhóm truy vấn `(arxivid, citationkey)`, tận dụng mạnh bộ 3 đặc trưng tương đối (`title_sim_diff_from_max`, `title_sim_rank_in_query`, `title_sim_margin_to_top2`) kết hợp các mỏ neo định danh và ngữ cảnh trích dẫn AST từ Milestone 2.

### 2. Hai Cơ chế Bảo vệ Toán học trong `train_ranker.py`

1. **Lọc nhóm toàn âm khi huấn luyện `LambdaMART` (`positive_only=True`):**
   Trong thuật toán `lambdarank`, một nhóm truy vấn chỉ chứa toàn nhãn `0` (truy vấn ngoài arXiv) không tạo được bất kỳ cặp (dương, âm) nào nên sinh gradient và Hessian bằng `0`. Do đó `prepare_training_data` loại bỏ các nhóm toàn âm trước khi truyền ma trận vào `LGBMRanker` (trên dải `range_0`, tập huấn luyện sau lọc còn `210.774` dòng thuộc `8.456` nhóm truy vấn có nhãn dương), trong khi vẫn giữ đầy đủ các dòng âm trong nhóm có đáp án và vẫn huấn luyện `LogisticRegression` trên toàn tập để đối chứng công bằng.
2. **Trọng số theo nguồn nhãn (`Manual = 3,0`, `Auto = 1,0`) & Dừng sớm trên `Valid-Manual`:**
   Do tập `Auto` áp đảo về số lượng (`508` bài `train` so với `3` bài `Manual` ở `range_0`) và mang đặc trưng bảo thủ (chỉ bắt các ca dễ/chính xác tuyệt đối), `train_ranker.py` gán **`sample_weight = 3,0`** cho mọi dòng thuộc nguồn `Manual` và **`1,0`** cho nguồn `Auto`. Đồng thời, cơ chế dừng sớm (*early stopping* `10` vòng) của `LambdaMART` chỉ theo dõi điểm `NDCG@1,3,5` trên tập **`Valid-Manual`** (`8` nhóm truy vấn chứa đủ cặp dương/âm của bài kiểm định thủ công `2408.11078`) — buộc mô hình phải tổng quát hóa được trên các trích dẫn thực tế khó thay vì học vẹt ngưỡng cắt heuristic của bộ tự động.

### 3. Bốn Cấu hình Mô hình & Bộ Đôi Ablation Đánh giá Đồng bộ (`pipeline.py`)

Khi chạy với `MatchingRanker` thật, hàm `_collect_ranker_eval_artifacts` tự động huấn luyện và đánh giá đồng bộ trên cùng tập `test` **4 mô hình** từ đơn giản đến nâng cao cùng **1 cặp Ablation Study** cho đóng góp của Milestone 2:

| Cấu hình thử nghiệm | Số đặc trưng | Cơ chế xếp hạng | Vai trò đối chứng |
| :--- | :---: | :--- | :--- |
| **`Title Fuzzy`** | 1 (`title_token_sort_ratio`) | Xếp hạng trực tiếp theo điểm `token_sort_ratio` + Hard Anchor | Baseline 1: Heuristic đối sánh chuỗi kinh điển |
| **`TF-IDF Cosine`** | 1 (`title_tfidf_cosine`) | Xếp hạng theo cosine n-gram ký tự 3–5 nội bộ bài báo + Hard Anchor | Baseline 2: Truy hồi thông tin không giám sát |
| **`Logistic Regression`** | 21 (`FEATURE_COLUMNS`) | `StandardScaler` (chỉ fit trên `Train`) + `LogisticRegression` có `sample_weight` | Baseline 3: Học máy tuyến tính phân loại cặp |
| **`LightGBM LambdaMART`** | 21 (`FEATURE_COLUMNS`) | `LGBMRanker(lambdarank, num_leaves=15, lr=0.05, n_estimators=100)` | Mô hình đề xuất chính thức |
| **`18 Features (No M2)`** | 18 (bỏ 3 cột AST M2) | `LGBMRanker` loại bỏ `cite_frequency`, `first_cite_section_type`, `first_cite_section_depth` | Thử nghiệm Ablation đo giá trị đóng góp của Milestone 2 |

### 4. Hậu xử lý Top-5 An toàn & Bất biến `groundtrutharxivid` (`ranker.py`)

Với mỗi truy vấn `(arxivid, citationkey)`, hàm `predict_top5_for_query` thực hiện chuỗi hậu xử lý tất định:

1. **Ưu tiên Mỏ neo cứng (*Hard Anchor Tier*):** Sắp xếp danh sách ứng viên theo bộ ba khóa `(-is_hard_anchor, -score, original_index)`, trong đó `is_hard_anchor = 1` nếu `arxiv_id_in_bib_text == 1` hoặc `doi_exact_match == 1`. Nhờ khóa ổn định này, các mục chứa arXiv ID hoặc DOI chính xác luôn đứng đầu bảng `cand1` mà vẫn bảo toàn trật tự điểm mô hình khi có nhiều ứng viên.
2. **Khử trùng lặp & Đệm `None` đủ 5 cột:** Loại bỏ các `ref_arxiv_id` trùng lặp giữ lại thứ hạng cao nhất; nếu số lượng ứng viên của bài $n < 5$ (kể cả trường hợp bài không có tham khảo arXiv nào, $n = 0$), điền **`None`** vào các vị trí `cand` còn trống.
3. **Bảo toàn tuyệt đối nhãn chuẩn (`groundtrutharxivid`):** Giá trị `groundtrutharxivid` trong bảng `predictions` được sao chép nguyên văn từ nhãn gốc (kể cả các ID có hậu tố phiên bản hoặc `None`), tuyệt đối không bị mô hình sửa đổi hoặc ghi đè.

---

## 10.3. Chỉ số Đánh giá `MRR@5` Hai Mẫu số & Đóng gói 6 Bảng Hugging Face

### 1. Minh bạch Hóa Công thức `MRR@5` Trên Dữ liệu Có Truy vấn Toàn âm (`evaluation.py`)

Theo phương trình (1) của đề bài, chỉ số Mean Reciprocal Rank tại 5 được định nghĩa:

$$
\text{MRR@5} = \frac{1}{|Q|} \sum_{i=1}^{|Q|} \frac{1}{\text{rank}_i}
$$

trong đó $\text{rank}_i \in \{1, 2, 3, 4, 5\}$ nếu `groundtrutharxivid` (chuẩn hóa versionless) xuất hiện trong `[cand1..cand5]`, ngược lại hạng nghịch đảo bằng $0$. Tuy nhiên, do tỷ lệ mục BibTeX **không có bản arXiv** trên thực tế thường chiếm từ $40\%$ đến $70\%$, các truy vấn toàn âm (`groundtrutharxivid = None`) luôn đóng góp chính xác $0$ vào tử số bất kể mô hình xếp hạng tốt tới đâu. Để tránh hiểu nhầm trần lý thuyết của thước đo, module `src/matching/evaluation.py` báo cáo song song **hai mẫu số** trên cả 3 lát cắt `overall`, `manual` và `auto`:

- **`mrr_at_5_all`:** Chia cho tổng số $|Q|$ toàn bộ truy vấn đã gán nhãn đúng theo chữ công thức (1) (trần lý thuyết tối đa bằng tỷ lệ truy vấn dương $|Q^+| / |Q|$).
- **`mrr_at_5_matchable`:** Chia riêng cho $|Q^+|$ — số truy vấn thực sự tồn tại bản arXiv khớp được trong `references` — phản ánh thuần túy năng lực xếp hạng của mô hình, kèm các chỉ số phụ trợ `hit_at_1`, `hit_at_3`, `hit_at_5` và `mean_average_precision`.

### 2. Kiến trúc Đóng gói 6 Bảng Hugging Face (`src/matching/export_hf.py`)

Module `export_hf.py` hỗ trợ lọc đồng bộ theo từng lát cắt 5.000 ID của mỗi thành viên (`--range-index <0..4>`) hoặc toàn kho (`--range-index all`), đóng gói trọn bộ **6 bảng Parquet nén `ZSTD`** ($\le 80\text{ MB}$/shard) kèm `README.md` Dataset Card YAML chuẩn Hugging Face Hub:

<div class="corpus-tree-card" role="region" aria-label="Cấu trúc Kho Dữ liệu Hugging Face 6 bảng">
  <div class="ct-header">
    <span>Cấu trúc kho dữ liệu công bố Hugging Face (<code>data/hf_range_0/</code>)</span>
    <span class="ct-dots" aria-hidden="true"><span></span><span></span><span></span></span>
  </div>
  <div class="ct-list">
    <div class="ct-row">
      <div class="ct-path"><span class="ct-dir">hf_range_0/</span></div>
      <div class="ct-desc">Thư mục gốc của Dataset Repository cho dải <code>range_0</code> (<code>2408.11045</code>–<code>2408.16044</code>)</div>
    </div>
    <div class="ct-row">
      <div class="ct-path"><span class="ct-branch">├── </span><span class="ct-file">README.md</span></div>
      <div class="ct-desc">Dataset Card với YAML <code>configs</code> khai báo 6 bảng &amp; <code>split: train</code></div>
    </div>
    <div class="ct-row">
      <div class="ct-path"><span class="ct-branch">└── </span><span class="ct-dir">data/</span></div>
      <div class="ct-desc">Thư mục chứa 6 bảng Parquet phân mảnh nén <code>ZSTD</code> (&le; 80 MB / shard)</div>
    </div>
    <div class="ct-row">
      <div class="ct-path"><span class="ct-branch">    ├── </span><span class="ct-dir">papers/</span><span class="ct-file">train-00000-of-00001.parquet</span></div>
      <div class="ct-desc">M1: Siêu dữ liệu 5.000 bài báo arXiv (khóa <code>arxiv_id</code>)</div>
    </div>
    <div class="ct-row">
      <div class="ct-path"><span class="ct-branch">    ├── </span><span class="ct-dir">references/</span><span class="ct-file">train-00000-of-00001.parquet</span></div>
      <div class="ct-desc">M1: Tham khảo Semantic Scholar &amp; fallback có arXiv ID</div>
    </div>
    <div class="ct-row">
      <div class="ct-path"><span class="ct-branch">    ├── </span><span class="ct-dir">elements/</span><span class="ct-file">train-00000-of-00010.parquet</span></div>
      <div class="ct-desc">M2: 10 phân mảnh phần tử văn bản/toán chuẩn hóa &amp; khử trùng lặp</div>
    </div>
    <div class="ct-row">
      <div class="ct-path"><span class="ct-branch">    ├── </span><span class="ct-dir">hierarchy/</span><span class="ct-file">train-00000-of-00003.parquet</span></div>
      <div class="ct-desc">M2: 3 phân mảnh cạnh cây phân cấp <code>(elementid &rarr; parentid)</code></div>
    </div>
    <div class="ct-row">
      <div class="ct-path"><span class="ct-branch">    ├── </span><span class="ct-dir">bibtex/</span><span class="ct-file">train-00000-of-00001.parquet</span></div>
      <div class="ct-desc">M2: Các mục BibTeX hợp nhất trường theo <code>(arxivid, citationkey)</code></div>
    </div>
    <div class="ct-row">
      <div class="ct-path"><span class="ct-branch">    └── </span><span class="ct-dir">predictions/</span><span class="ct-file">train-00000-of-00001.parquet</span></div>
      <div class="ct-desc">M3: Dự đoán Top-5 trên 515 bài thuộc <code>train</code> / <code>valid</code> / <code>test</code></div>
    </div>
  </div>
</div>

Hai chi tiết kỹ thuật bảo đảm tính tương thích hoàn toàn với trình xem (*Dataset Viewer*) và chế độ *streaming* của Hugging Face:
- **Ép kiểu lược đồ phẳng PyArrow:** Mọi bảng được căn chỉnh qua `_normalize_table_schema()` dùng duy nhất kiểu nguyên thủy phẳng, danh sách một cấp (`list<string>`) và kiểu từ điển nén `dictionary<int8, string>` cho `kind`, `entrytype`, `partition`; bảng `predictions` tự động lọc chỉ giữ các bài có `partition` thuộc `{'train', 'valid', 'test'}`.
- **Xử lý an toàn phân mảnh 0 dòng & Kiểm chứng `datasets.load_dataset`:** Khi một lát cắt không có bản ghi, `_write_sharded_table` ghi tệp Parquet hợp lệ qua `pq.ParquetWriter.close()` (0 row-group) để tránh lỗi `BatchSize must be greater than 0` trên `datasets 5.2.0`. Sau khi đóng gói, hàm `verify_hf_dataset()` kiểm tra khớp lược đồ từng shard và nạp thực tế cả 6 `config_name` qua `datasets.load_dataset(...)`.

````{admonition} Lệnh Vận hành Chuẩn Pipeline Milestone 3 (CLI run_matching.py)
:class: tip

```bash
# 1. Liệt kê bài đủ điều kiện & gán nhãn thủ công tương tác cho dải 0
PYTHONPATH=src python -m matching.labelling --range-index 0 --data-dir data
PYTHONPATH=src python -m matching.labelling --range-index 0 --data-dir data \
  --paper-ids 2408.11069 2408.11078 2408.11192 2408.11203 2408.11247

# 2. Kiểm tra nhanh đầu vào M1/M2 và nhãn tay không chạy ML
python src/run_matching.py --data-dir data --range-index 0 --dry-run

# 3. Chạy trọn gói: Preclean -> 21 Features -> LambdaMART + Baselines/Ablation
#    -> Đánh giá MRR@5 -> Đóng gói & Kiểm chứng 6 bảng HF -> Xuất 3 hình Poster 300 DPI
python src/run_matching.py --data-dir data --range-index 0 \
  --auto-fraction 0.12 --export-hf --verify-hf --plot-figures
```
````
