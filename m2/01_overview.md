# Chương 5. Kế hoạch & Kiến trúc Milestone 2 (Phân tích Cú pháp)

```{admonition} Trạng thái Giai đoạn: Đang Triển khai Tích cực (Cập nhật 10/11/2026)
:class: warning
Milestone 2 tập trung vào nhiệm vụ **Phân tích Cú pháp LaTeX, Chuẩn hóa Văn bản/Biểu thức Toán học & Khử Trùng lặp**. Hiện tại nhóm đã hoàn thành **Giai đoạn 0 (Khóa Hợp đồng Dữ liệu `SCHEMA_VERSION = 1` & Khung Pipeline Đa nhân)** và vừa tích hợp thành công **Phần C của Giai đoạn 1 (Gom nguồn thông minh `gathering.py` & Dựng cây phân cấp tài liệu `hierarchy.py`)** với 98 bài unit test chuyên sâu (toàn suite 394 passed). Các module làm sạch (B), trích xuất tham khảo & khử trùng lặp (D) đang được đẩy nhanh tiến độ.
```

## 5.1. Mục tiêu & Phạm vi của Milestone 2

Sau khi Milestone 1 hoàn tất việc thu thập toàn bộ các phiên bản ($v_1 \dots v_N$) của 25.000 định danh arXiv và lưu trữ cục bộ tại `data/papers/<dirname>/vK/`, Milestone 2 chịu trách nhiệm đọc cây mã nguồn `.tex`, `.bib` và `.bbl` để chuyển đổi tài liệu thô thành cơ sở dữ liệu học thuật có cấu trúc phân cấp:

1. **Phân tích cấu trúc phân cấp tài liệu (Document Hierarchy Parsing):**
   - Đọc và làm phẳng các tệp LaTeX thông qua việc giải quyết đệ quy các lệnh `\input{...}` và `\include{...}`.
   - Nhận diện cây cấu trúc hoàn chỉnh của văn bản: phần mở đầu (preamble), các cấp tiêu đề (section, subsection, subsubsection), các đoạn văn bản (paragraphs), các khối công thức toán học đứng độc lập (block formulas), các môi trường hình ảnh/bảng biểu (figures, tables), danh sách và từng mục danh sách (lists, items), và tách câu tự nhiên (sentences).
2. **Làm sạch nội dung LaTeX & Chuẩn hóa Toán học (Content Cleaning & Math Normalization):**
   - Mở rộng các macro tùy biến do tác giả định nghĩa trong phần mở đầu (`\def`, `\newcommand`).
   - Loại bỏ các lệnh định dạng phông chữ, ngắt trang, khoảng trắng thừa mà không làm thay đổi ý nghĩa ngữ nghĩa.
   - Chuẩn hóa các biểu thức toán học nội dòng (`$...$`) và toán học khối (`\[...\]`, `equation`, `align`) về dạng biểu diễn KaTeX/LaTeX thống nhất.
   - Tách câu tiếng Anh học thuật chính xác, xử lý các từ viết tắt thông dụng (`et al.`, `i.e.`, `e.g.`, `Fig.`, `Ref.`) để tránh cắt câu sai.
3. **Trích xuất & Hợp nhất Danh mục Tham khảo (BibTeX Extraction & Alignment):**
   - Bóc tách toàn bộ các mục tài liệu tham khảo từ tệp `.bib` và các khối `\begin{thebibliography}...\end{thebibliography}` bên trong mã nguồn `.tex`.
   - Đối chiếu với tệp danh mục tham khảo đã biên dịch `.bbl` (được bảo tồn từ Milestone 1) để chuẩn hóa các trường thông tin: tiêu đề, tác giả, năm công bố, tạp chí/hội nghị và định danh liên kết.
4. **Khử trùng lặp Nội dung Đa phiên bản (Cross-Version Deduplication):**
   - Băm SHA-256 nội dung từng câu, đoạn văn và công thức toán học.
   - Xác định chính xác các thành phần dữ liệu được kế thừa nguyên vẹn hoặc chỉnh sửa giữa các phiên bản liên tiếp ($v_1 \rightarrow v_2 \dots \rightarrow v_N$), giảm thiểu dung lượng lưu trữ và chuẩn bị dữ liệu đầu vào sắc nét cho Milestone 3.

---

## 5.2. Hợp đồng Dữ liệu Khóa (`src/parsing/models.py`)

Nhóm đã hoàn thành việc đóng băng hợp đồng dữ liệu chuẩn hóa (`SCHEMA_VERSION = 1`) làm nền tảng giao tiếp bất biến giữa các thành viên:

```text
[CompilationUnit: Mã nguồn .tex/.bib gộp của 1 phiên bản]
        │
        ├──> hierarchy.py (Phân tích Cấu trúc Phân cấp)
        │         └──> RawNode Tree (section, paragraph, formula, sentence)
        │
        ├──> cleaning.py & math_normalizer.py (Làm sạch & Chuẩn hóa Toán)
        │         └──> RawNode Tree (Nội dung đã chuẩn hóa LaTeX)
        │
        └──> bib_extractor.py (Bóc tách Tham khảo LaTeX)
                  └──> RawBibEntry (Mục trích dẫn từ .bib / thebibliography)
                            │
                            ▼
          [dedup.py: Khử Trùng lặp Đa Phiên bản]
                            │
       ┌────────────────────┼────────────────────┐
       ▼                    ▼                    ▼
[ElementRow]        [HierarchyRow]         [BibtexRow]
(Bảng phần tử)      (Bảng phân cấp)        (Bảng trích dẫn)
```

### Các lớp thực thể cốt lõi trong mô hình dữ liệu:

| Lớp dữ liệu (`dataclass`) | Ý nghĩa & Cấu trúc trường dữ liệu | Vai trò trong hệ thống |
| :--- | :--- | :--- |
| **`CompilationUnit`** | `arxiv_id`, `version`, `root_relpath`, `merged_tex`, `bib_files`, `raw_bibitems_blocks`, `total_tex_files`, `used_tex_files` | Đại diện cho toàn bộ mã nguồn của một phiên bản sau khi gom cụm và làm phẳng các liên kết `\input`. |
| **`RawNode`** | `node_id`, `parent_node_id`, `kind`, `content` (`kind` thuộc: `document`, `heading`, `paragraph`, `list`, `item`, `sentence`, `block_formula`, `figure`) | Nút phân cấp thô trong cây cấu trúc tài liệu của một phiên bản sau khi được làm sạch nội dung. |
| **`RawBibEntry`** | `bib_key`, `entry_type`, `raw_text`, `fields: dict[str, str]` | Đại diện cho một mục trích dẫn bóc tách được từ tệp `.bib` hoặc mục `\bibitem`. |
| **`ElementRow`** | `element_id`, `arxiv_id`, `version`, `kind`, `cleaned_text`, `sha256`, `is_reused_from_prev` | Bảng dữ liệu đầu ra chứa nội dung đã làm sạch của từng câu/đoạn/công thức, có cờ nhận diện tái sử dụng. |
| **`HierarchyRow`** | `parent_element_id`, `child_element_id`, `order_index`, `section_depth` | Bảng phản ánh mối quan hệ phân cấp hình cây giữa các phần tử trong bài báo. |
| **`BibtexRow`** | `arxiv_id`, `version`, `bib_key`, `title`, `authors`, `year`, `venue`, `matched_s2_id` | Bảng trích dẫn chuẩn hóa sẵn sàng cho việc đối sánh liên kết đồ thị ở Milestone 3. |

---

## 5.3. Khung Pipeline Phân tích Đa nhân CPU & Luồng Xử lý Module C (`run_parse.py`)

Tương tự như tầng giải nén của Milestone 1, việc phân tích cú pháp hàng chục nghìn bài báo đòi hỏi năng lực xử lý tính toán lớn. Hệ thống được thiết kế theo mô hình xử lý đa tiến trình (`ProcessPoolExecutor`) trên đa nhân CPU. Tính đến ngày **10/11/2026**, pipeline phân tích (`parsing.pipeline.process_paper`) đã hoàn tất tích hợp hai module cốt lõi của **Phần C**:

```text
Corpus.tex_files(id, version)
  └──> gathering.gather_compilation_unit(id, version, raw_files)
         └──> CompilationUnit (Mã nguồn hợp nhất & Root chính thức)
                └──> hierarchy.build_raw_hierarchy(unit, CleanerHooks)
                       └──> RawNode[] (Cây phân cấp) + bibliography bổ sung
                              └──> Chuyển tiếp tới các stage D (Tham khảo / Dedup)
```

1. **Gom nguồn thông minh & Lựa chọn Root đa tín hiệu (`gathering.py`):**
   - Chỉ đọc từ điển bytes đầu vào từ kho M1: giải mã văn bản an toàn, khử comment TeX có cơ chế bảo vệ literal (`\%`).
   - Lựa chọn tệp nguồn chính (root TeX) bằng thuật toán chấm điểm đa tín hiệu (phát hiện `\documentclass`, cấu trúc văn bản, số lượng lệnh `\input`/`\include`), khắc phục triệt để lỗi chọn nhầm tệp mẫu template (điển hình như bài `2408.11049` từ template 1/14 TeX sang `main.tex` dùng 8/14 TeX và nhận đúng bibliography).
   - Duyệt DFS include có cơ chế ngăn chặn vòng lặp vô hạn (chu trình) và chặn độ sâu tối đa 15 cấp, đếm tệp duy nhất. Không gọi mạng và không thực thi mã TeX.
2. **Xây dựng Cây Cấu trúc Phân cấp Tài liệu (`hierarchy.py`):**
   - Sử dụng stack cấp bậc đa tầng, hỗ trợ nhận diện các môi trường khối, danh sách (`list`/`item`) lồng nhau và các nút lá (`sentence`, `block_formula`, `figure`, `table`).
   - Tích hợp lỏng lẻo qua dependency injection (`CleanerHooks`), không import trực tiếp module làm sạch B.
   - Bảo toàn trọn vẹn các phần đặc thù: Abstract, Acknowledgements và Appendix; tách bạch hoàn toàn phần References ra khỏi nội dung các nút.
   - Khả năng tự phục hồi lỗi cú pháp: môi trường thiếu dấu đóng `\end{...}` được tự động khép kín ở đề mục kế tiếp; cấu trúc lồng vượt quá 64 mức được phát hiện và báo lỗi rõ ràng.
3. **Kiểm thử Đơn vị & Thực nghiệm Tập Mẫu Thật:**
   - Bảo vệ bằng **98 bài kiểm thử đơn vị** cho riêng Module C, nâng tổng số bài kiểm thử toàn repository lên **394 passed (100% offline)**.
   - Thử nghiệm trực tiếp trên tập mẫu thật gồm **26 phiên bản + 3 đối chứng** (trích xuất từ kho ngữ liệu 1.000 bài / 1.678 phiên bản): cấu trúc cây và điểm đánh dấu References đạt chuẩn, làm phẳng thành công **265/324** tệp TeX liên kết.

---

## 5.4. Lộ trình Triển khai Chi tiết

| Giai đoạn | Nội dung công việc trọng tâm | Trạng thái kỹ thuật |
| :---: | :--- | :---: |
| **Giai đoạn 0** | Khóa hợp đồng dữ liệu `src/parsing/models.py`, xây dựng khung pipeline đa nhân và bộ đo tài nguyên CPU/RAM. | **Đã hoàn thành ✅** *(06/11/2026)* |
| **Giai đoạn 1C** | Gom tệp thông minh, khử comment, chọn root đa tín hiệu (`gathering.py`) & Dựng cây phân cấp tài liệu (`hierarchy.py`). | **Đã hoàn thành ✅** *(10/11/2026 — 98 tests pass)* |
| **Giai đoạn 1B, 1D** | Hoàn thiện module làm sạch/chuẩn hóa toán học (`cleaning.py`, `math_normalizer.py`), trích xuất BibTeX (`bib_extractor.py`) và khử trùng lặp (`dedup.py`). | **Đang thực hiện 🟡** |
| **Giai đoạn 2** | Tích hợp toàn diện pipeline end-to-end, đối soát chất lượng trên tập mẫu Pilot 30 ID và chạy thử nghiệm quy mô lớn. | **Kế hoạch ⬜** |
| **Giai đoạn 3** | Xuất các bảng dữ liệu Parquet hoàn chỉnh, kiểm chứng tính nhất quán và hoàn thiện báo cáo phân tích cú pháp cho Milestone 2. | **Kế hoạch ⬜** |
