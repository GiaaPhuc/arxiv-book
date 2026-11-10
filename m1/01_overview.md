# Chương 1. Tổng quan & Phạm vi Thu thập Dữ liệu

```{admonition} Thông tin Dự án & Sản phẩm Bàn giao (Milestone 1)
:class: note
- **Môn học:** Nhập môn Khoa học Dữ liệu (*Introduction to Data Science*)
- **Repository mã nguồn pipeline:** [`GiaaPhuc/arxiv-pipeline`](https://github.com/GiaaPhuc/arxiv-pipeline) *(tài liệu hướng dẫn thiết lập môi trường, cấu hình khóa API và vận hành chi tiết được trình bày riêng trong `README.md` của repository mã nguồn theo đúng quy định đề bài)*.
- **Repository báo cáo trực tuyến (Jupyter Book):** [`GiaaPhuc/arxiv-book`](https://github.com/GiaaPhuc/arxiv-book) · **GitHub Pages:** <https://giaaphuc.github.io/arxiv-book/>
- **Nguyên tắc liêm chính dữ liệu:** Toàn bộ bảng tổng hợp và biểu đồ phân tích ở Chương 3 và Chương 4 đều được sinh tự động trực tiếp bằng Python trong quá trình biên dịch sách từ thư mục `stats/` (không sử dụng ảnh chụp tĩnh và không nhúng mã nguồn cài đặt của pipeline vào báo cáo).
```

## 1.1. Mục tiêu trong Chuỗi Dự án 3 Milestone

Báo cáo này trình bày thiết kế kỹ thuật, quá trình triển khai, kết quả thống kê dữ liệu và đánh giá hiệu năng của **Milestone 1 (Data Crawling)** thuộc dự án xây dựng kho ngữ liệu khoa học từ **arXiv** — kho lưu trữ bản thảo mở với hơn hai triệu công bố học thuật. Thay vì chỉ thu thập siêu dữ liệu bề mặt hoặc tải các tệp PDF khó bóc tách cấu trúc, hệ thống ở giai đoạn này thu thập trực tiếp **mã nguồn LaTeX toàn văn** cùng **mạng lưới trích dẫn có cấu trúc**, tạo nền tảng dữ liệu đầu vào cho toàn bộ chuỗi dự án ba cột mốc:

1. **Milestone 1 — Thu thập dữ liệu (Hiện tại):** Xác định chính xác các bài báo thuộc dải định danh được giao, tải xuống gói mã nguồn của **tất cả các phiên bản hiện có** ($v_1 \dots v_N$), loại bỏ hình ảnh nhị phân bằng phương pháp trích xuất chọn lọc chỉ giữ **`.tex`, `.bib` và `.bbl`** (bảo toàn tệp bibliography đã biên dịch phụ trợ), đồng thời thu thập siêu dữ liệu bài báo và tài liệu tham khảo qua **Semantic Scholar Academic Graph API** (kèm cơ chế gom lô, chia đôi lô đệ quy bisection và dự phòng bóc tách trích dẫn cục bộ từ `.bib`/`.bbl`).
2. **Milestone 2 — Phân tích cú pháp & Chuẩn hóa:** Đọc cây thư mục mã nguồn `.tex`/`.bib` từ Milestone 1 để phân tích cấu trúc phân cấp tài liệu, chuẩn hóa nội dung văn bản và biểu thức toán học, đồng thời thống nhất các mục trích dẫn về chuẩn BibTeX.
3. **Milestone 3 — Liên kết tham khảo & Công bố bộ dữ liệu:** Đối sánh các mục tài liệu tham khảo trích xuất từ LaTeX với tập ứng viên chuẩn trong bảng `references`, đánh giá mô hình liên kết và công bố bộ dữ liệu hoàn chỉnh lên Hugging Face.

Theo đúng quy định của Milestone 1, kho ngữ liệu làm việc được lưu giữ cục bộ trong nhóm để phục vụ hai giai đoạn kế tiếp; sản phẩm bàn giao ở cột mốc này bao gồm repository mã nguồn công khai [`GiaaPhuc/arxiv-pipeline`](https://github.com/GiaaPhuc/arxiv-pipeline) và cuốn sách báo cáo trực tuyến này.

---

## 1.2. Phạm vi Định danh Được Giao & Quy ước Bao phủ Phiên bản

Nhóm được phân công thu thập **25.000 định danh arXiv gốc** chia thành 5 dải liên tục, không chồng lấn (mỗi dải gồm đúng 5.000 ID tính cả hai đầu mút, khai báo trong `src/id_ranges.csv`) thuộc các tháng `2024-06`, `2024-07` và `2024-08`:

| Dải | Tháng nộp (`YYYY-MM`) | Định danh bắt đầu | Định danh kết thúc | Số lượng ID gốc | Trạng thái trong bản báo cáo hiện tại |
| :---: | :---: | :---: | :---: | :---: | :--- |
| **Dải 1** | `2024-08` | `2408.11045` | `2408.16044` | 5.000 | Đã hoàn tất thu thập & xuất thống kê (Snapshot hiện tại) |
| **Dải 2** | `2024-08` | `2408.06045` | `2408.11044` | 5.000 | Đang tiếp tục thu thập nối tiếp (sẽ cập nhật khi đủ 25.000 ID) |
| **Dải 3** | `2024-08` | `2408.01045` | `2408.06044` | 5.000 | Đang tiếp tục thu thập nối tiếp (sẽ cập nhật khi đủ 25.000 ID) |
| **Dải 4** | `2024-07` | `2407.07839` | `2407.12838` | 5.000 | Đang tiếp tục thu thập nối tiếp (sẽ cập nhật khi đủ 25.000 ID) |
| **Dải 5** | `2024-06` | `2406.07938` | `2406.12937` | 5.000 | Đang tiếp tục thu thập nối tiếp (sẽ cập nhật khi đủ 25.000 ID) |
| **Tổng cộng** | **06–08/2024** | — | — | **25.000** | **Đã cập nhật số liệu 5.000 / 25.000 ID (20% — Dải 1); 20.000 ID còn lại đang chạy nối tiếp** |

```{admonition} Ghi chú tiến độ thu thập dữ liệu (Snapshot 5.000 ID Dải 1 — sẽ cập nhật đầy đủ khi hoàn tất 25.000 ID)
:class: important
Sau các đợt nghiên cứu và tối ưu hóa chuyên sâu (kiến trúc đa luồng **Producer–Consumer**, đệm RAM Zero-Copy $96\text{ MiB}$, giải nén luồng tốc độ cao `_FastGzipStream` $512\text{ KiB}$ giữ trọn `.tex`/`.bib`/`.bbl`, điều nhịp **Start-to-Start $3{,}15\text{ s} + \text{jitter}$**, sàn nghỉ socket $\ge 3{,}05\text{ s}$, **Paced Streaming $4{,}5\text{ MiB/s}$**, thử lại Range tại chỗ cho file lớn $\ge 1\text{ MiB}$ với đệm sạc $12\text{–}14\text{ s}$, nạp hồi băng thông trượt $50\text{ MiB}$, **hàng đợi hoãn bài thông minh** và **Cooldown leo thang có khóa trần $240\text{ s}$**), tiến trình thu thập của nhóm trên Google Colab CPU đã hoàn tất trọn vẹn **5.000 định danh đầu tiên (Dải 1: `2408.11045` – `2408.16044`)**, bao gồm **8.200 phiên bản** ($v_1 \dots v_N$) và **206.813 mục tài liệu tham khảo**. Toàn bộ số liệu thống kê ở Chương 3 và số đo hiệu năng ở Chương 4 trong bản báo cáo này được đồng bộ trực tiếp từ đợt chạy 5.000 ID này.

Do tuân thủ nghiêm ngặt chính sách lịch sự của arXiv ($\ge 3{,}0\text{ s}$/yêu cầu), tiến trình thu thập đang tiếp tục chạy nối tiếp cho 4 dải còn lại (**20.000 ID**). Ngay khi cán mốc đủ 25.000 ID, nhóm sẽ cập nhật lại bộ tệp trong `stats/` và nâng cấp toàn bộ các bảng biểu, đồ thị và bài phân tích lên quy mô toàn cục 25.000 ID hoàn chỉnh.
```

Theo chuẩn đánh số 5 chữ số của arXiv áp dụng từ tháng 01/2015, các số thứ tự đầu tháng (như `1045`, `6045`, `7839`, `7938`) được chuẩn hóa đệm đủ chữ số `0` ở đầu thành `2408.01045`, `2408.06045`, `2407.07839`, `2406.07938`. Để đảm bảo tính nhất quán tuyệt đối của cơ sở dữ liệu trạng thái và tránh việc nhiều máy thành viên gửi yêu cầu chồng chéo lên máy chủ `export.arxiv.org`, nhóm gom toàn bộ 25.000 ID vào **một quy trình thu thập thống nhất** trên một máy chủ duy nhất (có khóa tiến trình cục bộ `_acquire_workspace_lock` tránh chạy trùng lặp).

Ba quy ước nghiệp vụ cốt lõi được áp dụng xuyên suốt quá trình thu thập:

- **Thu thập đầy đủ mọi phiên bản ($v_1 \dots v_N$):** Với mỗi bài báo tồn tại, bộ thu thập xác định hậu tố phiên bản mới nhất `vN` qua Atom API và truy xuất riêng lẻ từng bản nộp từ `v1` (bản gốc) đến `vN` qua endpoint `/src/{id}vK` có hậu tố phiên bản.
- **Loại bỏ hình ảnh bằng trích xuất chọn lọc, chỉ giữ lại `.tex`, `.bib` và `.bbl`:** Từ mỗi gói nguồn tải về, hệ thống **chỉ trích xuất các tệp `.tex`, `.bib` và `.bbl`** (giữ nguyên cấu trúc thư mục con tương đối để bảo toàn các liên kết `\input` và `\include`). Tệp `.bbl` (kết quả biên dịch danh mục tài liệu tham khảo) được bổ sung giữ lại nhằm hỗ trợ trực tiếp việc đối soát và trích xuất trích dẫn ở Milestone 2. Các tệp hình ảnh nhị phân (`.png`, `.jpg`, `.pdf`, `.eps`...) và tệp tạm khác (`.aux`, `.log`, `.out`, `.sty`, `.cls`...) không bao giờ được ghi vào kho ngữ liệu, nhưng mọi câu lệnh LaTeX định nghĩa hình ảnh bên trong tệp `.tex` (như môi trường `figure`, lệnh `\includegraphics`) đều được bảo toàn nguyên vẹn 100% cho bộ phân tích cấu trúc tài liệu ở Milestone 2.
- **Ngắt sớm 512 bytes cho phiên bản không có mã nguồn TeX (`no_source`):** Đối với các bài nộp chỉ cung cấp PDF biên dịch sẵn hoặc kho zip nhị phân (chẳng hạn ngay đầu Dải 3 là `2408.01045v1` — gói `804.208 B` mang chữ ký `%PDF`), hệ thống phát hiện magic bytes ngay ở 512 bytes đầu tiên và ngắt luồng tải sớm để tiết kiệm băng thông mạng, không loại bỏ công bố mà tạo bản ghi trạng thái `no_source` (`kept_bytes = 0`), giữ nguyên siêu dữ liệu bài báo (`paper.json`, `meta.json`) và toàn bộ danh sách tham khảo từ Semantic Scholar.

---

## 1.3. Tổ chức Dữ liệu Làm việc Cục bộ & Hai Bảng Dữ liệu Quy định

Tuân thủ quy ước tổ chức dữ liệu gợi ý của đề bài và hợp đồng dữ liệu khóa cố định trong `src/crawler/models.py` (`SCHEMA_VERSION = 1`), mỗi công bố được lưu trữ trong một thư mục làm việc riêng biệt đặt tên chuẩn hóa từ định danh gốc (`2408.11046` $\rightarrow$ `2408-11046`; định danh cũ trước năm 2007 như `hep-th/9901001` $\rightarrow$ `hep-th-9901001` nhưng trường `arxiv_id` trong JSON luôn giữ nguyên gốc):

<div class="corpus-tree-card" role="region" aria-label="Cấu trúc thư mục dữ liệu cục bộ">
  <div class="ct-header">
    <span>Cấu trúc kho ngữ liệu làm việc cục bộ (<code>data/</code>)</span>
    <span class="ct-dots" aria-hidden="true"><span></span><span></span><span></span></span>
  </div>
  <div class="ct-list">
    <div class="ct-row">
      <div class="ct-path"><span class="ct-dir">data/</span></div>
      <div class="ct-desc">Thư mục gốc của kho ngữ liệu làm việc cục bộ</div>
    </div>
    <div class="ct-row">
      <div class="ct-path"><span class="ct-branch">├── </span><span class="ct-file">manifest.sqlite</span></div>
      <div class="ct-desc">Sổ trạng thái SQLite (chế độ WAL) của mọi cặp <code>(arxiv_id, version)</code></div>
    </div>
    <div class="ct-row">
      <div class="ct-path"><span class="ct-branch">├── </span><span class="ct-dir">logs/</span></div>
      <div class="ct-desc">Nhật ký vận hành và tài nguyên hệ thống</div>
    </div>
    <div class="ct-row">
      <div class="ct-path"><span class="ct-branch">│   ├── </span><span class="ct-file">crawl.log</span></div>
      <div class="ct-desc">Nhật ký vận hành chi tiết (tự động che giấu API key qua bộ lọc bí mật)</div>
    </div>
    <div class="ct-row">
      <div class="ct-path"><span class="ct-branch">│   ├── </span><span class="ct-file">metrics.json</span></div>
      <div class="ct-desc">Số đo thời gian theo chặng, RAM RSS O(1) và dung lượng đĩa tích lũy</div>
    </div>
    <div class="ct-row">
      <div class="ct-path"><span class="ct-branch">│   ├── </span><span class="ct-file">diagnostics.jsonl</span></div>
      <div class="ct-desc">Nhật ký chẩn đoán ngoại lệ (HTTP 429/403/5xx, đứt stream, gói &ge; 50 MiB)</div>
    </div>
    <div class="ct-row">
      <div class="ct-path"><span class="ct-branch">│   └── </span><span class="ct-file">rate_state.json</span></div>
      <div class="ct-desc">Lưu mốc thời gian cooldown liên tiến trình (chống vi phạm khi khởi động lại)</div>
    </div>
    <div class="ct-row">
      <div class="ct-path"><span class="ct-branch">├── </span><span class="ct-dir">stats/</span></div>
      <div class="ct-desc">Đầu ra từ <code>export_data.py</code> (Parquet cục bộ + CSV/JSON cho báo cáo)</div>
    </div>
    <div class="ct-row">
      <div class="ct-path"><span class="ct-branch">└── </span><span class="ct-dir">papers/</span></div>
      <div class="ct-desc">Thư mục lưu trữ toàn bộ công bố đã thu thập</div>
    </div>
    <div class="ct-row">
      <div class="ct-path"><span class="ct-branch">    └── </span><span class="ct-dir">&lt;arxiv-id-chuan-hoa&gt;/</span></div>
      <div class="ct-desc">Ví dụ: <code>2408-11046/</code></div>
    </div>
    <div class="ct-row">
      <div class="ct-path"><span class="ct-branch">        ├── </span><span class="ct-file">paper.json</span></div>
      <div class="ct-desc">Siêu dữ liệu cấp bài báo (tiêu đề, tác giả, ngày nộp/sửa, venue)</div>
    </div>
    <div class="ct-row">
      <div class="ct-path"><span class="ct-branch">        ├── </span><span class="ct-file">s2_references.raw.json.gz</span></div>
      <div class="ct-desc">Phản hồi gốc nén gzip từ S2 (dấu hiệu hoàn tất chặng S2)</div>
    </div>
    <div class="ct-row">
      <div class="ct-path"><span class="ct-branch">        └── </span><span class="ct-dir">v1..vN/</span></div>
      <div class="ct-desc">Thư mục riêng cho từng phiên bản từ <code>v1</code> tới <code>vN</code></div>
    </div>
    <div class="ct-row">
      <div class="ct-path"><span class="ct-branch">            ├── </span><span class="ct-file">meta.json</span></div>
      <div class="ct-desc">Trạng thái phiên bản, dung lượng gốc/giữ lại &amp; mã băm SHA-256</div>
    </div>
    <div class="ct-row">
      <div class="ct-path"><span class="ct-branch">            ├── </span><span class="ct-file">references.json</span></div>
      <div class="ct-desc">Toàn bộ tham khảo đã crawl ở máy cục bộ (kể cả không có arXiv ID)</div>
    </div>
    <div class="ct-row">
      <div class="ct-path"><span class="ct-branch">            └── </span><span class="ct-dir">tex/</span></div>
      <div class="ct-desc">Cây thư mục tương đối chỉ chứa các tệp <code>.tex</code>, <code>.bib</code> và <code>.bbl</code></div>
    </div>
  </div>
</div>

Từ kho dữ liệu làm việc trên, module `export_data.py` (`crawler/export.py`) kết xuất hai bảng dữ liệu chuẩn dạng Apache Parquet theo đúng lược đồ cột và kiểu dữ liệu được quy định cho bộ dữ liệu công bố cuối khóa:

| Bảng | Đơn vị bản ghi | Lược đồ cột & Kiểu dữ liệu (`pyarrow`) | Quy tắc lọc và chuẩn hóa nghiệp vụ |
| :--- | :--- | :--- | :--- |
| **`papers`** | Một bài báo gốc (`arxiv_id`) | `arxiv_id` (`string`, không null); `title` (`string`); `authors` (`list<string>`); `submission_date` (`string` ISO); `revised_dates` (`list<string>`); `venue` (`string`, có thể null) | `submission_date` là ngày nộp bản `v1`; `revised_dates` chứa lần lượt ngày phát hành của các bản `v2..vN` (kết hợp tối ưu thẻ `<updated>` và cơ chế bù ngày trung gian OAI-PMH `arXivRaw` qua `--enable-oai-dates` đảm bảo đủ số lượng mốc thời gian); `venue` ưu tiên trường `journal_ref` trên arXiv, nếu khuyết mới lấy từ Semantic Scholar (đã loại bỏ giá trị tên kho `"arXiv"` / `"arXiv.org"`). |
| **`references`** | Một cặp trích dẫn–được trích dẫn | `arxiv_id` (`string`, không null — bài trích dẫn); `ref_arxiv_id` (`string`, không null); `ref_title` (`string`); `ref_authors` (`list<string>`); `ref_submission_date` (`string`); `ref_s2_id` (`string`) | **Chỉ giữ lại các tham khảo có `ref_arxiv_id` hợp lệ** (bảo toàn nguyên văn định danh cũ trước năm 2007 như `hep-th/9901001`) và khử trùng lặp theo khóa kép `(arxiv_id, ref_arxiv_id)` để tạo tập ứng viên đối sánh (*matching pool*) sạch cho Milestone 3. Toàn bộ tham khảo không có arXiv ID vẫn được lưu đầy đủ trong `references.json` tại máy cục bộ. |
