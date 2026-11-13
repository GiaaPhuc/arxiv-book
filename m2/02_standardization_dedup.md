# Chương 6. Chuẩn hóa Nội dung, Trích xuất BibTeX & Khử trùng lặp Hai tầng

Nếu Chương 5 giải quyết bài toán dựng bộ khung cấu trúc cây từ các tệp `.tex` rời rạc, thì các module trình bày trong chương này quyết định trực tiếp **độ sạch ngữ nghĩa của từng nút lá**, **tỷ lệ nén khử trùng lặp xuyên phiên bản** và **độ giàu siêu dữ liệu BibTeX** phục vụ bài toán liên kết trích dẫn ở Milestone 3.

---

## 6.1. Mở rộng Macro Preamble An toàn & Dọn sạch Lệnh Trình bày (`cleaner.py`)

Trên thực tế, hai phiên bản $v_1$ và $v_2$ của cùng một bài báo thường viết cùng một biểu thức toán học hoặc câu văn nhưng khác nhau cách gọi macro tự định nghĩa (ví dụ tác giả định nghĩa `\newcommand{\R}{\mathbb{R}}` ở đầu tệp), hoặc chỉ khác nhau ở các lệnh căn chỉnh bố cục trang khi biên tập lại cho hội nghị. Module `src/parsing/cleaner.py` chuẩn hóa triệt để hai nguồn nhiễu này trước khi dựng nút lá:

### 1. Giải nén Macro có Giới hạn ở Phần mở đầu (`extract_and_expand_macros`)

- **Thu thập định nghĩa an toàn từ Preamble:** Văn bản trước `\begin{document}` được quét bằng bộ đếm ngoặc nhọn cân bằng để trích xuất các khai báo `\newcommand{\foo}[k][default]{body}`, `\renewcommand`, `\providecommand` (với số tham số $0 \le k \le 3$, hỗ trợ tham số mặc định tùy chọn đầu tiên) cũng như các khai báo `\def\foo{body}` và `\def\foo#1{body}` tường minh.
- **Danh sách bảo vệ lệnh cấu trúc (Protected Primitives):** Để tránh việc các gói định dạng của tạp chí định nghĩa lại lệnh hệ thống làm sai lệch bộ phân tích cây, hệ thống chặn tuyệt đối không ghi đè các từ khóa cấu trúc cốt lõi: `\section`, `\subsection`, `\subsubsection`, `\paragraph`, `\item`, `\begin`, `\end`, `\cite`, `\bibitem`, `\caption`, `\label`, `\ref`, `\eqref`, `\url`, `\input`, `\include`.
- **Thay thế lặp có chặn độ sâu:** Các macro hợp lệ được thế trực tiếp vào phần thân tài liệu tối đa **5 vòng lặp** (dừng sớm ngay khi một vòng quét không còn phát sinh thay thế mới), qua đó vừa giải nén được macro lồng nhau 2–3 cấp (`\norm{\vx}` $\rightarrow$ `\|\mathbf{x}\|`), vừa miễn nhiễm hoàn toàn trước bẫy đệ quy vô hạn (`\def\a{\a}`).

### 2. Bóc tách Lệnh Trình bày & Chuẩn hóa Dòng Văn bản (`clean_latex_content`)

| Nhóm can thiệp | Các lệnh / Mẫu cú pháp mục tiêu | Quy tắc biến đổi chuẩn hóa |
| :--- | :--- | :--- |
| **Xóa tùy chọn vị trí & bố cục trang** | `[htbp!]`, `[H]`, `[!t]`, `\centering`, `\raggedright`, `\raggedleft`, `\noindent`, `\indent`, `\newpage`, `\clearpage`, `\pagebreak`, `\linebreak`, `\allowbreak`, `\sloppy`, `\fussy` | Loại bỏ hoàn toàn lệnh và tùy chọn ngoặc vuông đi kèm ngay sau `\begin{figure}` / `\begin{table}` vì chỉ phục vụ dàn trang PDF, không mang ngữ nghĩa học thuật. |
| **Xóa đường kẻ bảng & khoảng cách cứng** | `\toprule`, `\midrule`, `\bottomrule`, `\hline`, `\cline{...}`, `\vline`, `\vspace[*]{...}`, `\hspace[*]{...}`, `\smallskip`, `\medskip`, `\bigskip`, `\vfill`, `\hfill`, `\small`, `\footnotesize`, `\large`, `\Large`... | Xóa bỏ hoàn toàn khỏi nội dung văn bản và khối hình/bảng để tránh nhiễu trình bày. |
| **Bóc vỏ định dạng chữ (Unwrap)** | `\textbf{X}`, `\textit{X}`, `\emph{X}`, `\underline{X}`, `\textrm{X}`, `\textsf{X}`, `\texttt{X}`, `\textsc{X}`, `{\bf X}`, `{\it X}`, `{\em X}` | Bóc bỏ vỏ lệnh bên ngoài công thức toán nhưng **giữ nguyên vẹn phần nội dung `X` bên trong** (hỗ trợ ngoặc nhọn lồng nhau nhiều tầng); giải mã dấu trọng âm LaTeX (`\'e` $\rightarrow$ `é`, `\"o` $\rightarrow$ `ö`). |
| **Đồng nhất họ lệnh trích dẫn** | `\cite{...}`, `\citep{...}`, `\citet{...}`, `\citealp{...}`, `\citeauthor{...}`, `\parencite{...}`, `\textcite{...}` (kèm tùy chọn như `\cite[p.~4]{k1, k2}`) | Quy về cấu trúc chuẩn giữ nguyên danh sách khóa trích dẫn sạch để bước đổi tên khóa liên phiên bản (`dedup.py`) đạt độ chính xác 100%. |

Cuối cùng, mọi chuỗi khoảng trắng và ký tự tab liên tiếp được thu gọn về một dấu cách đơn chuẩn hóa, giúp hai câu văn ở $v_1$ và $v_2$ chỉ khác vị trí ngắt dòng trong trình soạn thảo của tác giả sẽ cho ra **cùng một chuỗi `content` khớp từng ký tự**.

---

## 6.2. Chuẩn hóa Biểu thức Toán học bằng Máy Trạng thái (`math_normalizer.py`)

Tuân thủ yêu cầu chuẩn hóa toán học của đề bài, module `src/parsing/math_normalizer.py` đưa toàn bộ biểu thức toán học trong bài báo về **đúng hai dạng chính tắc duy nhất**: toán nội dòng dùng cặp dấu đô-la đơn `` `$...$` `` và toán khối dùng môi trường `\begin{equation}...\end{equation}`.

1. **Bảo vệ ký tự tiền tệ thoát `\$` trước khi quét:** Trong các bài báo Khoa học Máy tính và Kinh tế lượng, ký hiệu chi phí như `\$100` hoặc `\$0.02/1K tokens` xuất hiện rất phổ biến. Nếu dùng biểu thức chính quy ngây thơ tìm cặp dấu đô-la, một dấu `\$` lẻ sẽ làm lệch pha đóng/mở toán học của toàn bộ đoạn văn phía sau. Bộ chuẩn hóa giải quyết bằng cách tạm thời che chắn mọi chuỗi `\$` (có số lẻ dấu `\` đứng trước) thành ký tự sentinel riêng biệt trước khi phân tích ranh giới toán, rồi hoàn trả về `\$` ở bước cuối cùng.
2. **Hợp nhất 9 họ môi trường toán khối về `\begin{equation}...\end{equation}`:**
   - Bộ quét trạng thái nhận diện và chuyển đổi toàn bộ các cấu trúc trưng bày công thức gồm: cặp đô-la kép `` `$$...$$` ``, `\[...\]`, `\begin{displaymath}...\end{displaymath}`, `\begin{equation*}...\end{equation*}`, `\begin{align[*]}...\end{align[*]}`, `\begin{gather[*]}...\end{gather[*]}`, `\begin{multline[*]}...\end{multline[*]}`, `\begin{flalign[*]}...\end{flalign[*]}` và `\begin{eqnarray[*]}...\end{eqnarray[*]}` về dạng thống nhất `\begin{equation}...\end{equation}`.
   - Bên trong thân phương trình, các thẻ chỉ phục vụ đánh số hình thức (`\nonumber`, `\notag`, `\allowdisplaybreaks`, `\label{...}`) được lược bỏ và khoảng trắng nhiều dòng được chuẩn hóa gọn gàng.
3. **Hợp nhất toán nội dòng về `` `$...$` ``:** Mọi cấu trúc `\(...\)`, `\begin{math}...\end{math}` và `\ensuremath{...}` được chuyển về `` `$...$` ``, đồng thời cắt bỏ khoảng trắng thừa sát rìa bên trong dấu phân cách (ví dụ `` `$ x + y $` `` $\rightarrow$ `` `$x + y$` ``).

---

## 6.3. Tách Câu Lá Ngữ cảnh `Protect–Mask–Split–Restore` (`sentence_splitter.py`)

Tách đoạn văn thành các nút lá `sentence` trên văn bản khoa học LaTeX là nơi dễ phát sinh lỗi cắt nhầm nhất nếu dùng bộ tách câu thông thường, trong khi các mô hình học sâu NLP nặng lại quá chậm khi xử lý hàng triệu câu trên CPU. Module `src/parsing/sentence_splitter.py` giải quyết bài toán với độ phức tạp thời gian tuyến tính $\mathcal{O}(N)$ thông qua kiến trúc **4 bước che chắn–khôi phục**:

1. **Bước 1 — Che chắn vùng bất khả xâm phạm (*Protect / Mask*):** Toàn bộ công thức toán nội dòng `` `$...$` ``, các lệnh LaTeX có đối số ngoặc nhọn (`\cite{...}`, `\ref{fig.1}`, `\eqref{eq.2}`, `\url{...}`, `\href{...}{...}`, `\footnote{...}`), đường dẫn URL trần (`https://...`) và các con số thập phân / số hiệu phiên bản (`3.14159`, `p < 0.05`, `v2.1.0`) được thay thế tạm thời bằng các thẻ định danh cố định không chứa dấu câu (`__M0__`, `__C0__`, `__U0__`, `__N0__`...). Nhờ đó, **mọi dấu chấm nằm bên trong toán học, lệnh LaTeX, số thực và URL đều hoàn toàn vô hình** trước bộ tách câu.
2. **Bước 2 — Bảo vệ từ viết tắt học thuật & tên riêng (*Abbreviation Guard*):** Hệ thống tra cứu danh mục hơn **60 từ viết tắt học thuật phổ biến** không phân biệt hoa thường:
   - *Cụm Latin & lập luận:* `i.e.`, `e.g.`, `et al.`, `cf.`, `vs.`, `viz.`, `etc.`, `w.r.t.`, `a.k.a.`, `i.i.d.`, `s.t.`, `w.l.o.g.`, `resp.`;
   - *Tham chiếu nội bộ bài báo:* `Fig.`, `Figs.`, `Eq.`, `Eqs.`, `Sec.`, `Secs.`, `Sect.`, `Tab.`, `Tabs.`, `Alg.`, `Thm.`, `Lem.`, `Prop.`, `Cor.`, `Def.`, `Ref.`, `Refs.`, `Ch.`, `App.`, `Vol.`, `No.`, `pp.`;
   - *Chức danh, học vị & chữ tắt tên người:* `Dr.`, `Prof.`, `Mr.`, `Mrs.`, `Jr.`, `Sr.`, `Ph.D.`, `U.S.`, cùng mẫu chữ cái đầu tên tác giả `\b[A-Z]\.(?=\s+[A-Z])` (như `A. Einstein`, `J. K. Rowling`) và dấu ba chấm `...`.
   Mọi dấu chấm thuộc các mẫu này được thay tạm bằng ký tự bảo vệ nội bộ trước khi phân đoạn.
3. **Bước 3 — Phát hiện biên câu thật (*Split*):** Văn bản chỉ được tách tại các dấu kết câu thật (`[.!?]+`) khi theo sau bởi khoảng trắng và ký tự mở đầu hợp lệ của câu kế tiếp (chữ cái in hoa, dấu mở ngoặc/ngoặc kép, chữ số, hoặc một token toán/lệnh `__M*__`, `__C*__` đứng đầu câu).
4. **Bước 4 — Hoàn nguyên & Kiểm chứng không rò rỉ (*Restore*):** Khôi phục toàn bộ ký tự bảo vệ và các thẻ `__M*__`, `__C*__`, `__U*__`, `__N*__` về nguyên bản 100%, đồng thời ghép nối các mảnh vụn suy biến (chỉ gồm dấu câu lẻ) để đảm bảo không có bất kỳ ký tự sentinel nội bộ nào tồn tại ở đầu ra.

---

## 6.4. Trích xuất Tham chiếu `.bib`, Khôi phục `.bbl` & Cascade 4 Tầng cho `\bibitem` (`bib_extractor.py`)

Để tối đa hóa chất lượng bảng `bibtex` (nguồn đầu vào trực tiếp để đối sánh với bảng `references` từ Semantic Scholar ở Milestone 3), module `src/parsing/bib_extractor.py` xử lý song song cả hai nguồn tài liệu tham khảo xuất hiện trên arXiv:

### Luồng 1 — Bộ phân tích `.bib` cân bằng ngoặc

- **Bảo toàn URL khi lọc comment `.bib`:** Chỉ loại bỏ comment ngoài phạm vi giá trị trường, bảo toàn tuyệt đối các chuỗi mã hóa phần trăm (`%20`, `%7E`) bên trong `{...}` hoặc `"..."`.
- **Giải biến `@string` & toán tử `#`:** Thu thập từ điển `@string{cvpr = "IEEE/CVF Conference on Computer Vision and Pattern Recognition"}` ở đầu tệp và tự động nối chuỗi qua toán tử `#` khi giải giá trị trường `journal` / `booktitle`.
- **Báo lỗi cú pháp tường minh:** Lỗi cú pháp `.bib` được báo bằng `ValueError` để pipeline cô lập theo bài/phiên bản (ghi vào `_errors.jsonl`) thay vì làm dừng toàn bộ tiến trình. Hạn chế hiện tại: bộ đọc chỉ hỗ trợ dạng `@type{...}` (chưa hỗ trợ `@type(...)`), chưa kế thừa `crossref`, chưa xử lý macro `@string` khai báo sau nơi dùng và chưa giải mã đầy đủ các dấu phụ tiếng nước ngoài của TeX.
- **Chuẩn hóa lược đồ đích:** Tách danh sách `authors` theo từ khóa `and` ở mức ngoặc ngoài cùng, ép kiểu `year` sang số nguyên 4 chữ số (`int32`), cắt bỏ tiền tố `https://doi.org/` khỏi `doi`, và tự động tổng hợp `url = "https://arxiv.org/abs/<id>"` khi phát hiện trường `eprint` / `arxivid`.

### Luồng 2 — Khôi phục `.bbl` & Chuyển đổi `\bibitem` bằng *Anchor-First + 4-Template Cascade*

Thực tế khảo sát kho ngữ liệu arXiv cho thấy rất nhiều bài báo không nộp kèm tệp `.bib` gốc mà dán trực tiếp `\begin{thebibliography}` vào `.tex` hoặc đính kèm tệp `.bbl` đã biên dịch sẵn. Với mỗi mục `\bibitem[label]{key} ...`, hệ thống áp dụng chiến lược **bắt mỏ neo cứng trước — phân đoạn mẫu ngữ pháp sau**:

1. **Tầng 0 — Trích xuất Mỏ neo Cứng & Thẻ `\bibinfo` (Anchor-First):**
   - Nhận diện trực tiếp các thẻ cấu trúc `\bibinfo{author}{...}`, `\bibinfo{title}{...}`, `\bibinfo{journal}{...}`, `\bibinfo{year}{...}` do các gói `revtex`/`apsrev` sinh ra trong tệp `.bbl` — giúp đạt độ chính xác gần như tuyệt đối trên nhóm bài Vật lý và Toán–Lý.
   - Quét biểu thức chính quy bắt cứng các trường có định dạng bất biến: `doi` (`10.\d{4,9}/...`), `url` (`\url{...}`, `\href{...}`, `https?://...`), định danh `arXiv:YYMM.NNNNN` / `hep-th/NNNNNNN` và năm xuất bản 4 chữ số `(19|20)\d{2}`.
2. **Tầng 1–4 — Chuỗi 4 Mẫu Ngữ pháp Học thuật (4-Template Cascade):** Với các mục `\bibitem` văn bản tự do không có thẻ `\bibinfo`, bộ phân tích thử tuần tự từ đặc thù đến tổng quát:
   - *Mẫu 1 (Tiêu đề đặt trong ngoặc kép — chuẩn IEEE / NeurIPS / Nature):* Bắt cụm `` ``Title'' ``, `"Title"` hoặc `\enquote{Title}`; phần đứng trước là danh sách tác giả, phần đứng sau là tên tạp chí/hội nghị.
   - *Mẫu 2 (Khối in nghiêng `\emph{...}` / `\textit{...}` — chuẩn APS / AMS / Springer):* Phân biệt thông minh xem khối in nghiêng là **tên tạp chí** (chứa từ khóa viết tắt như `Phys. Rev.`, `J.`, `Proc.`, `IEEE`, `Trans.`, `Lett.` hoặc đi kèm số tập in đậm `\textbf{42}`) hay là **tiêu đề bài báo**, từ đó suy ra hai thành phần còn lại.
   - *Mẫu 3 (Phân đoạn theo dấu chấm câu có bảo vệ tên tắt — chuẩn ACM / APA):* Bảo vệ chữ tắt tên tác giả (`A. Vaswani`) rồi phân tách theo ranh giới `. ` thành ba đoạn chuẩn `Authors` $\rightarrow$ `Title` $\rightarrow$ `Venue & Year`.
   - *Mẫu 4 (Định dạng bản thảo Preprint arXiv):* Xử lý mẫu rút gọn `Authors, Title, arXiv preprint arXiv:XXXX.XXXXX (Year)` và suy diễn tự động `entrytype` (`inproceedings`, `book`, `article`, hoặc `misc`).

---

## 6.5. Khử trùng lặp Hai tầng Xuyên Phiên bản theo "Thứ tự Vàng" (`dedup.py`)

Điểm nhấn thuật toán cốt lõi của Milestone 2 nằm ở **thứ tự thực hiện hai tầng khử trùng lặp** trong `src/parsing/dedup.py`. Nếu khử trùng lặp văn bản trước khi khử trùng lặp tài liệu tham khảo, hai câu văn giống hệt nhau ở $v_1$ và $v_2$ nhưng gọi hai khóa trích dẫn khác tên cho cùng một tài liệu (ví dụ `\cite{vaswani2017}` ở $v_1$ và `\cite{vit_transformer}` ở $v_2$) sẽ bị băm thành hai chuỗi khác nhau và không thể gộp chung!

Do đó, pipeline thực thi nghiêm ngặt **"Thứ tự Vàng" (Golden Order)**:

<div class="jb-dag-grid" role="region" aria-label="Minh họa Thứ tự Vàng trong Khử trùng lặp Hai tầng">
  <div class="jb-dag-panel">
    <div class="jb-dag-panel-title">
      <span>Tầng 1 — Gom cụm Tham chiếu &amp; Hợp nhất Trường</span>
      <span class="jb-badge-version">Trước</span>
    </div>
    <div>
      <strong>Đầu vào xuyên phiên bản:</strong><br/>
      &bull; <code>v1</code>: <code>@inproceedings{vaswani2017, title={Attention...}, year={2017}}</code><br/>
      &bull; <code>v2</code>: <code>@inproceedings{vit_transformer, title={Attention...}, year={2017}, doi={10.5555/3295222}}</code><br/>
      &bull; <code>v3</code>: <code>@inproceedings{vit_transformer, title={Attention...}, doi={10.5555/3295222}}</code> <em>(khuyết year)</em><br/>
      <strong>Kết quả Union-Find + Field Union:</strong><br/>
      &rarr; 1 dòng <code>bibtex</code> duy nhất với <code>citationkey = "vaswani2017"</code>, hội tụ đủ cả <code>title</code>, <code>authors</code>, <code>year = 2017</code> và <code>doi = "10.5555/3295222"</code>.<br/>
      &rarr; Ánh xạ đổi tên: <code>(v2, vit_transformer) &rarr; vaswani2017</code>, <code>(v3, vit_transformer) &rarr; vaswani2017</code>.
    </div>
  </div>
  <div class="jb-dag-panel">
    <div class="jb-dag-panel-title">
      <span>Tầng 2 — Viết lại <code>\cite{}</code> &amp; Băm Phần tử Toàn văn</span>
      <span class="jb-badge-shared">Sau</span>
    </div>
    <div>
      <strong>Trước khi đổi tên khóa trích dẫn:</strong><br/>
      &bull; Câu ở <code>v1</code>: <code>"...architecture \cite{vaswani2017}."</code><br/>
      &bull; Câu ở <code>v2</code>: <code>"...architecture \cite{vit_transformer}."</code><br/>
      <strong>Bước 2a — Đồng bộ hóa <code>\cite{}</code> trên cây:</strong><br/>
      &bull; Câu ở <code>v2</code> được viết lại thành <code>"...architecture \cite{vaswani2017}."</code> (đồng thời khử khóa lặp nếu gộp <code>\cite{a, b} &rarr; \cite{a}</code>).<br/>
      <strong>Bước 2b — Content-Addressed Hash Pool:</strong><br/>
      &rarr; Cặp khóa <code>(kind="sentence", content)</code> của <code>v1</code> và <code>v2</code> nay <strong>khớp chính xác 100%</strong> &rarr; dùng chung một <code>elementid</code> duy nhất trong bảng <code>elements</code>!
    </div>
  </div>
</div>

### Các cơ chế bảo vệ độ chính xác trong `dedup.py`

1. **Gom cụm tương đương bằng Union-Find có Chống Xung đột Khóa số (`\bibitem{1}` Shift Guard):**
   Hai mục tham chiếu $r_i, r_j$ thuộc các phiên bản của cùng một bài báo được hợp nhất vào cùng một lớp tương đương khi thỏa một trong bốn điều kiện: *(i)* trùng `DOI` chuẩn hóa khác rỗng; *(ii)* trùng `arXiv ID` chuẩn hóa khác rỗng; *(iii)* tiêu đề chuẩn hóa có độ tương đồng `difflib.SequenceMatcher` $\ge 0{,}85$ kèm cùng năm hoặc cùng họ tác giả đầu; *(iv)* trùng `citation_key` giữa hai phiên bản **chỉ được coi là tín hiệu yếu**: yêu cầu thêm tiêu đề chuẩn hóa giống nhau và không xung đột năm (bản ghi trống không bao giờ bị gộp chỉ vì trùng khóa). Quy tắc kiểm tra xung đột nội dung đặc biệt quan trọng đối với các bài dùng khóa đánh số thứ tự `\bibitem{1}`, `\bibitem{2}`: khi tác giả chèn thêm một tài liệu mới lên đầu danh sách ở $v_2$, khóa `1` ở $v_2$ thực chất trỏ sang một bài báo hoàn toàn khác so với khóa `1` ở $v_1$. Nếu tiêu đề và tác giả/năm giữa hai bản khác biệt rõ rệt, bộ gom cụm tự động tách riêng thay vì gộp nhầm.
2. **Chọn khóa đại diện tất định (`canonical_key`) & Hợp nhất trường (`Field Union`):** Trong mỗi cụm liên thông, hệ thống ưu tiên chọn khóa mang tính mô tả chữ–số từ phiên bản sớm nhất (phá hòa bằng thứ tự từ điển) và lấy hợp thông tin đầy đủ nhất trên từng trường (`title` đầy đủ nhất ưu tiên từ `.bib`, danh sách `authors` chi tiết nhất, `year` hợp lệ đầu tiên, `doi` và `url` không rỗng, `journal` ưu tiên nơi công bố chính thức hơn nhãn tạm `"arXiv preprint"`).
3. **Bảng băm phần tử nội dung (`element_pool`):** Duyệt tuần tự $v = 1 \dots N$, mọi nút khác `document` đều được tra cứu qua khóa băm `(node.kind, node.content)`. Chỉ những phần tử có nội dung thực sự mới mới được cấp `elementid` mới theo tiền tố trực quan (`#h`, `#p`, `#lst`, `#itm`, `#s`, `#eq`, `#fig`); các phần tử đã xuất hiện ở phiên bản trước được tái sử dụng ngay `elementid` sẵn có.
4. **Giới hạn đã biết:** Khi một phần tử dùng chung có nhiều cha, kết quả là DAG chứ không nhất thiết còn là cây theo từng lần xuất hiện (lược đồ không lưu thứ tự hay số lần xuất hiện trong cùng một cha); nếu gộp nội dung tạo chu trình, `dedup.py` báo lỗi thay vì xuất đồ thị sai. So khớp tham chiếu trong một bài là $O(R^2)$ theo số tham chiếu $R$ và các mẫu `\bibitem` là heuristic nên cần đánh giá trên corpus thật.

---

## 6.6. Xử lý Song song, Sharded Parquet & Kiểm chứng 8 Bất biến (`pipeline.py`, `validate_m2.py`)

Do mọi phép khử trùng lặp chỉ diễn ra giữa các phiên bản $v_1 \dots v_N$ **bên trong cùng một công bố `arxiv_id`**, các bài báo hoàn toàn độc lập về mặt dữ liệu. Hệ thống tận dụng đặc tính này để tối ưu hóa cả tốc độ lẫn bộ nhớ:

- **Đa tiến trình cấp bài báo & Xả luồng theo lô 500 bài (`pipeline.py`, `export_m2.py`):** Điều phối viên phân phối danh sách `arxiv_id` qua `ProcessPoolExecutor(..., chunksize=1)`. Thay vì tích trữ hàng triệu nút cây trong RAM của tiến trình chính, bộ xuất `ShardedParquetExporter` gom đúng mỗi lô **`batch_size = 500` bài báo** rồi xả ngay ra một bộ phân mảnh `part-000XX.parquet` (Parquet qua `pyarrow`, mỗi tệp ghi qua tệp tạm rồi đổi tên) với kiểu `pa.dictionary(pa.int8(), pa.string())` cho cột `kind` và `entrytype`, ghi nối các ID hoàn tất vào `_done.txt` rồi gọi `gc.collect()` giải phóng bộ nhớ tức thì.
- **Kiểm định toán học và toàn vẹn quan hệ độc lập (`validate_m2.py`):** Sau khi hoàn tất phân tích cú pháp, trình kiểm định độc lập quét dạng luồng qua toàn bộ các phân mảnh Parquet (giải phóng bộ đệm theo từng lô bài hoàn chỉnh để giữ RAM phẳng) nhằm xác nhận **8 bất biến bắt buộc** trước khi xuất số liệu sang sách báo cáo:

| # | Tên bất biến trong `validate_m2.py` | Điều kiện toán học & quan hệ được kiểm tra tự động |
| :---: | :--- | :--- |
| **1** | **Lược đồ & Kiểu dữ liệu Parquet** | Đúng tên cột trên cả 3 bảng; `kind` và `entrytype` dùng kiểu `dictionary`; `version` và `year` kiểu `int32`; `authors` kiểu `list<string>`; không có `null` ở các cột bắt buộc hoặc phần tử rỗng trong `authors`. |
| **2** | **Gốc cây duy nhất mỗi phiên bản** | Mỗi phiên bản có TeX sở hữu đúng 1 nút `document` (`<dirname>#root<v>`), và nút gốc này không bao giờ đứng làm nút con `elementid` trong bảng `hierarchy`. |
| **3** | **Toàn vẹn khóa ngoại & Không mồ côi** | Mọi `elementid` và `parentid` trong `hierarchy` đều tồn tại trong `elements` của cùng `arxivid`; mọi nút khác `document` trong `elements` đều xuất hiện trong ít nhất một phiên bản của `hierarchy`. |
| **4** | **Đồ thị không chu trình & Liên thông gốc** | Duyệt DFS 3 màu lặp (không bị giới hạn đệ quy Python) trên từng `(arxivid, version)` xác nhận 0 chu trình, 0 cạnh tự khuyên, 0 cạnh trùng lặp và 100% nút hội tụ đúng về `#root<version>`. |
| **5** | **Khử trùng lặp xuyên phiên bản nghiêm ngặt** | Trong phạm vi mỗi `arxivid`, không tồn tại hai dòng khác `document` trong `elements` trùng cả `(kind, content)`, và không tồn tại hai dòng `bibtex` trùng `citationkey`. |
| **6** | **Không rò rỉ mục `References` & Sentinel** | Không còn đề mục `References` / `Bibliography` / `Works Cited`, không còn lệnh `\bibitem` hay môi trường `thebibliography`, và 0 ký tự che chắn nội bộ (`\uE000`, `\uE001`) lọt vào `elements`. |
| **7** | **Đồng bộ hóa khóa trích dẫn `\cite{...}`** | Không còn khóa lặp ngay trong cùng một lệnh `\cite{k, k}` và không còn khóa cũ đã bị gộp (`_cite_aliases.json`) xuất hiện trong văn bản `elements`. |
| **8** | **Độ phủ 100% phiên bản so với Milestone 1** | Đối chiếu trực tiếp với `Corpus` (`data/papers`): tổng số bài và phiên bản khớp 100%; các phiên bản `no_source` / `ok_no_tex` có đúng `0` phần tử trong Parquet nhưng được ghi nhận đầy đủ trong thống kê độ bao phủ. |
