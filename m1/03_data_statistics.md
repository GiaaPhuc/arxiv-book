---
jupytext:
  text_representation:
    extension: .md
    format_name: myst
kernelspec:
  display_name: Python 3
  language: python
  name: python3
---

# Chương 3. Thống kê & Phân tích Dữ liệu Thu thập

Toàn bộ bảng tổng hợp và biểu đồ trực quan trong chương này được tính toán và kết xuất tự động ngay trong quá trình biên dịch sách (`jupyter-book build .`) từ bộ tệp thống kê xuất ra bởi `export_data.py` đặt tại thư mục `arxiv-book/stats/` (`summary.json`, `papers_stats.csv`, `versions_stats.csv`).

```{admonition} Phạm vi bộ số liệu: Toàn bộ 25.000 Định danh (Hoàn tất 5 Dải)
:class: note
Hệ thống pipeline thu thập đã hoàn tất xử lý trọn vẹn **25.000 định danh** trên **5 dải dữ liệu (`06/2024 – 08/2024`: `2406.07938` – `2408.16044`)** trên nền kiến trúc chuẩn hóa **`arxiv-pipeline v3.18`** (khám phá ngoại tuyến Kaggle Snapshot `--snapshot`, quy trình 2 giai đoạn tách rời `--skip-s2` / `--s2-only`, nhịp Start-to-Start `3,05 s` + Deficit Breather, tùy chọn HTTP/2 + Zero-Body Header Early-Reject, Cut-Through In-Flight Extraction `O(1)` RAM giữ `.tex`/`.bib`/`.bbl`, Traffic-Shaping `360 MiB / 180 s`, Range Resume tại chỗ và Semantic Scholar High-Density Batch `150` + Save-First Isolation).

Toàn bộ các bảng tổng hợp và biểu đồ phân tích trong chương này được kết xuất động trực tiếp từ bộ tệp thống kê quy mô **25.000 ID** trong thư mục `stats/m1/` (`summary.json`, `papers_stats.csv`, `versions_stats.csv`).
```

## 3.1. Bảng Tổng hợp Các Chỉ số Thu thập Cốt lõi

```{code-cell} ipython3
:tags: [remove-input]

from pathlib import Path
import json
import pandas as pd
import matplotlib.pyplot as plt
from IPython.display import HTML, display

plt.rcParams.update({
    "figure.dpi": 160,
    "figure.facecolor": "#ffffff",
    "axes.facecolor": "#fafbfc",
    "axes.edgecolor": "#cbd5e1",
    "axes.labelcolor": "#1e293b",
    "xtick.color": "#334155",
    "ytick.color": "#334155",
    "font.size": 9.5,
    "axes.titlesize": 11,
    "axes.titleweight": "bold",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.axisbelow": True,
    "axes.grid": True,
    "grid.color": "#cbd5e1",
    "grid.alpha": 0.45,
})


def _find_stats_dir() -> Path:
    for base in (
        Path("../stats"),
        Path("stats"),
        *[parent / "stats" for parent in Path.cwd().parents],
    ):
        for candidate in (base / "m1", base):
            if candidate.is_dir() and (candidate / "summary.json").is_file():
                return candidate
    return Path("../stats/m1")


STATS_DIR = _find_stats_dir()
REQUIRED_STATS_FILES = ("summary.json", "papers_stats.csv", "versions_stats.csv")
MISSING_STATS_FILES = [
    name for name in REQUIRED_STATS_FILES if not (STATS_DIR / name).is_file()
]
HAS_STATS = len(MISSING_STATS_FILES) == 0


def fmt_int(val):
    return f"{int(val):,}" if val is not None else "N/A"


def fmt_float(val, digits=2):
    return f"{float(val):.{digits}f}" if val is not None else "N/A"


def fmt_pct(val):
    return f"{float(val) * 100:.2f}%" if val is not None else "N/A"


def fmt_bytes_dual(val):
    if val is None:
        return "N/A"
    val = float(val)
    if val >= 1024**2:
        return f"{val:,.0f} B ({val / 1024**2:.2f} MiB)"
    return f"{val:,.0f} B ({val / 1024:.1f} KiB)"


def show_table(df: pd.DataFrame, *, kv: bool = False) -> None:
    classes = "dataframe jb-stats-table jb-kv-table" if kv else "dataframe jb-stats-table"
    display(HTML(df.to_html(index=False, border=0, classes=classes)))


def show_pending_box(section_desc: str, preview_df: pd.DataFrame | None = None, *, kv: bool = False) -> None:
    missing_html = ", ".join(f"<code>stats/{name}</code>" for name in MISSING_STATS_FILES)
    html = (
        '<div class="jb-pending-card">'
        '<div class="jb-pending-title">⏳ Đang chờ tệp thống kê trong thư mục <code>arxiv-book/stats/</code></div>'
        f"<div>Hiện chưa tìm thấy: {missing_html}. "
        f"{section_desc} sẽ <strong>tự động sinh đầy đủ</strong> ngay khi chép đầu ra từ lệnh "
        "<code>python src/crawler/export_data.py --data-dir data</code> vào <code>arxiv-book/stats/</code> "
        "và biên dịch lại sách (không cần chỉnh sửa mã).</div>"
        "</div>"
    )
    display(HTML(html))
    if preview_df is not None:
        show_table(preview_df, kv=kv)


if HAS_STATS:
    summary = json.loads((STATS_DIR / "summary.json").read_text(encoding="utf-8"))
    papers_df = pd.read_csv(STATS_DIR / "papers_stats.csv", dtype={"arxiv_id": str})
    versions_df = pd.read_csv(STATS_DIR / "versions_stats.csv", dtype={"arxiv_id": str})

    b_paper = summary.get("mean_bytes_per_paper", {})
    b_ver = summary.get("mean_bytes_per_extracted_version", {})
    req_count = int(summary.get("ids_requested") or 0)
    req_label = (
        "Tổng số ID yêu cầu trong 5 dải (ids_requested)"
        if req_count >= 25000
        else f"Tổng số ID yêu cầu trong đợt thống kê hiện tại (ids_requested — {req_count:,}/25,000 ID)"
    )
    s2_states = summary.get("s2_states", {})
    s2_found = int(s2_states.get("found", 0) or 0)
    s2_not_indexed = int(s2_states.get("not_indexed", 0) or 0)
    s2_local_bib = int(s2_states.get("local_bib", 0) or 0)

    overview_rows = [
        (req_label, fmt_int(summary.get("ids_requested"))),
        ("Số ID không tồn tại trên arXiv (ids_not_found — HTTP 404)", fmt_int(summary.get("ids_not_found"))),
        ("Số bài báo thực tế tồn tại (papers_total)", fmt_int(summary.get("papers_total"))),
        ("Số bài báo thu thập thành công đủ mọi phiên bản (papers_success)", fmt_int(summary.get("papers_success"))),
        ("Tỷ lệ thành công chung cấp bài báo (success_rate_papers)", fmt_pct(summary.get("success_rate_papers"))),
        ("Số bài báo có ít nhất 1 phiên bản chứa mã nguồn TeX (papers_with_tex)", fmt_int(summary.get("papers_with_tex"))),
        ("Tổng số cặp (bài báo, phiên bản) đã khám phá (pairs_total)", fmt_int(summary.get("pairs_total"))),
        ("Tỷ lệ thành công chung cấp phiên bản (success_rate_pairs)", fmt_pct(summary.get("success_rate_pairs"))),
        ("Số phiên bản trung bình trên mỗi bài báo", fmt_float(summary.get("mean_versions_per_paper"))),
        ("Kích thước TB mỗi bài báo TRƯỚC khi bỏ ảnh — giải nén (bytes)", fmt_bytes_dual(b_paper.get("raw_uncompressed_with_images"))),
        ("Kích thước TB mỗi bài báo SAU khi bỏ ảnh — giữ .tex/.bib/.bbl (bytes)", fmt_bytes_dual(b_paper.get("kept_tex_bib"))),
        ("Tỷ lệ dung lượng giữ lại trên tổng dung lượng giải nén", fmt_pct(summary.get("kept_over_raw_uncompressed"))),
        ("Số tài liệu tham khảo trung bình mỗi bài báo", fmt_float(summary.get("mean_refs_per_paper"))),
        ("Độ phủ bài báo có dữ liệu tham khảo — tỷ lệ (a)", f"{fmt_pct(summary.get('s2_coverage_papers'))} ({fmt_int(s2_found)} bài)"),
        ("Số bài khuyết tham khảo sau dự phòng cục bộ (not_indexed — S2 404)", fmt_int(s2_not_indexed)),
    ]
    if s2_local_bib > 0:
        overview_rows.append(("Số bài S2 404 bù từ .bib/.bbl cục bộ (local_bib — tách riêng)", fmt_int(s2_local_bib)))
    overview_rows.extend([
        ("Tỷ lệ thành công TB thu thập đủ siêu dữ liệu tham khảo — tỷ lệ (b)", fmt_pct(summary.get("mean_refs_complete_ratio"))),
        ("Tỷ lệ tham khảo mang định danh arXiv ID — tỷ lệ (c)", fmt_pct(summary.get("share_refs_with_arxiv_id"))),
    ])
    show_table(pd.DataFrame(overview_rows, columns=["Chỉ số thống kê dữ liệu thu thập", "Giá trị đo đạc"]), kv=True)
else:
    pilot_preview = pd.DataFrame(
        [
            ("Tổng số ID yêu cầu trong 5 dải (ids_requested)", "⏳ Chờ stats/summary.json (Pilot: 30)"),
            ("Số bài báo thu thập thành công đủ mọi phiên bản (papers_success)", "⏳ Chờ stats/summary.json (Pilot: 30 / 30)"),
            ("Tỷ lệ thành công chung cấp bài báo (success_rate_papers)", "⏳ Chờ stats/summary.json (Pilot: 100.00%)"),
            ("Tổng số cặp (bài báo, phiên bản) đã khám phá (pairs_total)", "⏳ Chờ stats/summary.json (Pilot: 57; TB 1.90 bản/bài)"),
            ("Kích thước TB mỗi bài báo TRƯỚC khi bỏ ảnh (bytes)", "⏳ Chờ stats/summary.json (Pilot: 11,916,738 B — 11.36 MiB)"),
            ("Kích thước TB mỗi bài báo SAU khi bỏ ảnh — giữ .tex/.bib/.bbl (bytes)", "⏳ Chờ stats/summary.json (Pilot: 235,800 B — 230.3 KiB)"),
            ("Số tài liệu tham khảo trung bình mỗi bài báo", "⏳ Chờ stats/summary.json (Pilot: 33.63)"),
            ("Ba tỷ lệ siêu dữ liệu tham khảo S2: (a) / (b) / (c)", "⏳ Chờ stats/summary.json (Pilot: 100.00% / 78.02% / 50.35%)"),
        ],
        columns=["Chỉ số thống kê cốt lõi (Mục 3.1)", "Trạng thái / Đối chiếu Pilot 30 ID"],
    )
    show_pending_box("Bảng tổng hợp 16 chỉ số thu thập cốt lõi tại Mục 3.1", pilot_preview, kv=True)
```

**Phân tích kết quả tổng quan:**

- **Định nghĩa chặt chẽ về bài báo thu thập thành công:** Các định danh không tồn tại trên hệ thống arXiv (`ids_not_found` — HTTP `404` sau bước xác nhận sub-batch 50 ID) được tách riêng khỏi mẫu số `papers_total`. Một bài báo chỉ được tính vào `papers_success` khi **mọi phiên bản từ $v_1$ tới $v_N$** của nó đều hoàn tất xử lý với trạng thái hợp lệ (`ok`, `ok_no_tex` hoặc `no_source`), bảo đảm không có bất kỳ phiên bản nào bị khuyết hoặc lỗi giữa chừng.
- **Đánh giá độ bao phủ thực tế trên toàn bộ 25.000 ID (5 Dải):** Trong suốt 5 dải thu thập (`06/2024 – 08/2024`: `2406.07938` – `2408.16044`), toàn bộ 25.000 ID đều tồn tại thực tế trên arXiv (`ids_not_found = 0`). Hệ thống đã thu thập thành công trọn vẹn **24.878 / 25.000 bài báo** với đầy đủ mọi phiên bản hiện có, đạt tỷ lệ thành công cấp bài báo **99,51%**. Trong đó, có **23.029 bài báo (92,12%)** sở hữu ít nhất một phiên bản cung cấp mã nguồn TeX (`.tex`, `.bib`, `.bbl`), còn lại **1.971 bài báo (7,88%)** không có mã nguồn TeX (gồm 1.950 bài nộp thuần PDF hợp lệ `no_source` ở mọi phiên bản và 21 bài gặp lỗi trên mọi phiên bản). Chỉ có **122 bài báo (0,49%)** chưa đạt `papers_success` do chứa phiên bản không tìm thấy gói nguồn (`not_found`) hoặc xung đột tên tệp dành riêng của Windows (`corrupt`), hoàn toàn nằm trong dung sai kiểm soát lỗi của hệ thống.

---

## 3.2. Độ Bao phủ Phiên bản ($v_1 \dots v_N$) & Phân bố Trạng thái Nguồn

```{code-cell} ipython3
:tags: [remove-input]

if HAS_STATS:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.5, 3.8))

    status_keys = ["ok", "no_source", "ok_no_tex", "not_found", "corrupt", "failed"]
    status_names = ["ok (.tex/.bib/.bbl)", "no_source (PDF)", "ok_no_tex", "not_found", "corrupt", "failed"]
    status_colors = ["#2b8a3e", "#1971c2", "#f08c00", "#868e96", "#e03131", "#c92a2a"]
    pairs_by_status = summary.get("pairs_by_status", {})
    s_counts = [int(pairs_by_status.get(k, 0)) for k in status_keys]
    total_p = max(sum(s_counts), 1)

    bars1 = ax1.barh(status_names, s_counts, color=status_colors)
    ax1.invert_yaxis()
    ax1.set_xlabel("Số lượng phiên bản")
    ax1.set_title("Phân bố trạng thái xử lý các phiên bản")
    for b, c in zip(bars1, s_counts):
        pct = c / total_p * 100
        pct_str = "0.00%" if c == 0 else ("<0.01%" if pct < 0.01 else f"{pct:.2f}%")
        ax1.text(
            b.get_width() + total_p * 0.015,
            b.get_y() + b.get_height() / 2,
            f"{c:,} ({pct_str})",
            va="center",
            fontsize=8.5,
        )
    ax1.set_xlim(0, max(s_counts) * 1.44 if max(s_counts) else 10)

    ver_dist = {int(k): int(v) for k, v in summary.get("versions_per_paper", {}).items()}
    if max(ver_dist, default=0) > 8:
        bar_labels = [f"v{k}" for k in range(1, 8)] + ["v8+"]
        ys = [ver_dist.get(k, 0) for k in range(1, 8)] + [
            sum(v for k, v in ver_dist.items() if k >= 8)
        ]
    else:
        xs = sorted(ver_dist)
        bar_labels = [f"v{k}" for k in xs]
        ys = [ver_dist[k] for k in xs]
    mean_v = summary.get("mean_versions_per_paper") or 0.0
    bars2 = ax2.bar(bar_labels, ys, color="#1c7ed6", width=0.55)
    ax2.set_xlabel("Tổng số phiên bản của bài báo (N)")
    ax2.set_ylabel("Số lượng bài báo")
    ax2.set_title(f"Phân phối số phiên bản / bài (TB = {mean_v:.2f})")
    for b, y in zip(bars2, ys):
        if y > 0:
            ax2.text(
                b.get_x() + b.get_width() / 2,
                b.get_height() + max(ys) * 0.015,
                f"{y:,}",
                ha="center",
                fontsize=8.5,
            )
    ax2.set_ylim(0, max(ys) * 1.18 if ys else 10)

    plt.tight_layout()
    plt.show()
    plt.close(fig)
else:
    show_pending_box("Cặp biểu đồ phân bố trạng thái gói nguồn và phân phối số phiên bản v1..vN tại Mục 3.2")
```

- **Phân bố trạng thái gói nguồn:** Kết quả phân loại trên tổng số **41.615 phiên bản** phản ánh sát đặc trưng xuất bản thực tế trên arXiv [[4, 5]](#tai-lieu-tham-khao):
  - Có **38.725 phiên bản (93,06%)** ở trạng thái `ok` (cung cấp đầy đủ mã nguồn `.tex`, `.bib` và `.bbl` xuyên suốt cả 5 dải), cùng **5 phiên bản (0,01%)** ở trạng thái `ok_no_tex` (giải nén thành công nhưng gói nguồn không chứa tệp `.tex` hợp lệ).
  - Có **2.749 phiên bản (6,61%)** ở trạng thái `no_source` (bài báo nộp trực tiếp tệp PDF biên dịch sẵn hoặc kho zip nhị phân; ở kiến trúc `v3.18` được ngắt sớm ngay tại HTTP Header `Content-Type` với `wire_bytes = 0` và lớp dự phòng 512 bytes magic `%PDF`/`PK` nhằm tiết kiệm băng thông).
  - **Giải trình minh bạch `121` phiên bản `not_found (0,29%)` trên `/src/<id>v<n>`:** Dù siêu dữ liệu bài báo có liệt kê đủ các phiên bản `v1..vN`, máy chủ nguồn `export.arxiv.org/src/<id>v<n>` vẫn trả `HTTP 404` trên một số ít bản nháp (thường do bản nháp bị rút/ẩn nguồn hoặc lỗi AutoTeX phía arXiv). Tuân thủ đúng quy ước bản ghi rỗng của đề bài, hệ thống **vẫn khởi tạo thư mục phiên bản và lưu tệp rỗng `v<n>/meta.json` (`kept_bytes = 0`, kèm `error = "HTTP 404 on /src/"`)** giống như bản chỉ có PDF (`no_source`) để bảo đảm dãy `v1..vN` liên tục, nhưng gắn trạng thái `not_found` và **không tính vào số bài/phiên bản thu thập thành công (`papers_success`, `success_rate_pairs`)**.
  - **Cô lập an toàn `15` phiên bản `corrupt (0,04%)`:** Toàn bộ 15 ca `corrupt` ghi nhận trong `summary.json["top_errors"]` đều xuất phát từ gói nguồn chứa tên tệp trùng thiết bị hệ thống dành riêng của Windows (`aux` 6 ca, `weixiang/con.tex` 2 ca, `con.tex` 2 ca, `AAAI25/LaTeX/con.pdf` 2 ca, `img/aux.pdf`, `Sections/con.tex`, và 1 đường dẫn bảng đặt tên đặc biệt). Cơ chế kiểm tra an toàn đường dẫn `_safe_member_path` cùng kiểm tra CRC32/ISIZE tầng C của `_FastGzipStream` giúp cô lập từng gói lỗi này mà không làm gián đoạn quá trình thu thập 25.000 bài báo; ghi nhận **0 phiên bản (0,00%)** `failed` do đứt kết nối chưa phục hồi.
  - Tỷ lệ thành công cấp phiên bản hợp lệ (`ok` + `ok_no_tex` + `no_source`) đạt mức rất cao: **99,67%** (**41.479 / 41.615** phiên bản).
- **Phân phối số phiên bản mỗi bài báo ($\bar{V}$):** Biểu đồ bên phải thể hiện quy luật lệch phải điển hình của chu kỳ hoàn thiện bản thảo khoa học: hơn một nửa số bài báo dừng ở bản nộp gốc $v_1$ (**14.160 bài**, chiếm **56,64%**), tiếp theo là $v_2$ (**7.071 bài**, **28,28%**) và $v_3$ (**2.582 bài**, **10,33%**); nhóm từ $v_4$ đến $v_{30}$ chỉ chiếm **1.187 bài (4,75%)** (`v4 = 733`, `v5 = 282`, `v6 = 96`, `v7 = 40`, `v8+ = 36`). Số phiên bản trung bình thực tế đạt **$\bar{V} = 1{,}66$ phiên bản/bài** (`1,6646`), với phiên bản cao nhất ghi nhận được trong toàn tập là **$N = 30$** (`v30`, mã bài `2406.10476`).

---

## 3.3. Kích thước Trung bình Trước và Sau Khi Loại bỏ Hình ảnh

```{code-cell} ipython3
:tags: [remove-input]

def _safe_round(v):
    return f"{round(v):,}" if v is not None else "N/A"


def _reduction_pct(raw_val, kept_val):
    if not raw_val or kept_val is None:
        return "N/A"
    return f"-{(1.0 - kept_val / raw_val) * 100:.2f}%"


if HAS_STATS:
    size_df = pd.DataFrame([
        {
            "Đơn vị tính trung bình": "Mỗi bài báo (gộp mọi phiên bản v1..vN)",
            "Gói nén tải về (bytes)": _safe_round(b_paper.get("raw_archive")),
            "Giải nén gốc kèm ảnh (bytes)": _safe_round(b_paper.get("raw_uncompressed_with_images")),
            "Sau khi lọc chỉ giữ .tex/.bib/.bbl (bytes)": _safe_round(b_paper.get("kept_tex_bib")),
            "Mức giảm dung lượng": _reduction_pct(
                b_paper.get("raw_uncompressed_with_images"), b_paper.get("kept_tex_bib")
            ),
        },
        {
            "Đơn vị tính trung bình": "Mỗi phiên bản giải nén (ok / ok_no_tex)",
            "Gói nén tải về (bytes)": _safe_round(b_ver.get("raw_archive")),
            "Giải nén gốc kèm ảnh (bytes)": _safe_round(b_ver.get("raw_uncompressed_with_images")),
            "Sau khi lọc chỉ giữ .tex/.bib/.bbl (bytes)": _safe_round(b_ver.get("kept_tex_bib")),
            "Mức giảm dung lượng": _reduction_pct(
                b_ver.get("raw_uncompressed_with_images"), b_ver.get("kept_tex_bib")
            ),
        },
    ])
    show_table(size_df)

    labels = [
        "Gói nén tải về\n(raw_archive)",
        "Giải nén kèm ảnh\n(raw_uncompressed)",
        "Chỉ giữ .tex, .bib & .bbl\n(kept_tex_bib)",
    ]
    vals_kb = [
        (b_paper.get("raw_archive") or 0.0) / 1024,
        (b_paper.get("raw_uncompressed_with_images") or 0.0) / 1024,
        (b_paper.get("kept_tex_bib") or 0.0) / 1024,
    ]

    fig, (ax_lin, ax_log) = plt.subplots(1, 2, figsize=(10.2, 3.6))
    colors_sz = ["#495057", "#ae3ec9", "#2b8a3e"]
    for ax, is_log, title in [
        (ax_lin, False, "Kích thước TB mỗi bài báo (Thang tuyến tính)"),
        (ax_log, True, "Kích thước TB mỗi bài báo (Thang Logarit)"),
    ]:
        plot_vals = [max(v, 0.01) if is_log else v for v in vals_kb]
        bars = ax.bar(labels, plot_vals, color=colors_sz, width=0.5)
        if is_log:
            ax.set_yscale("log")
        ax.set_ylabel("Kích thước trung bình (KiB)")
        ax.set_title(title)
        for b, v in zip(bars, vals_kb):
            txt = f"{v / 1024:.2f} MiB" if v >= 1024 else f"{v:.1f} KiB"
            ax.text(
                b.get_x() + b.get_width() / 2,
                b.get_height() * (1.16 if is_log else 1.03),
                txt,
                ha="center",
                va="bottom",
                fontsize=8.5,
                fontweight="bold",
            )
        ax.set_ylim(top=max(plot_vals) * (2.4 if is_log else 1.18) if max(plot_vals) > 0 else 10)

    plt.tight_layout()
    plt.show()
    plt.close(fig)
else:
    pilot_size_df = pd.DataFrame([
        {
            "Đơn vị tính (Đối chiếu Pilot 30 ID)": "Mỗi bài báo (gộp v1..vN)",
            "Gói nén tải về (bytes)": "10,393,685",
            "Giải nén kèm ảnh (bytes)": "11,916,738",
            "Chỉ giữ .tex/.bib/.bbl (bytes)": "235,800",
            "Mức giảm": "-98.02%",
        },
        {
            "Đơn vị tính (Đối chiếu Pilot 30 ID)": "Mỗi phiên bản giải nén (ok)",
            "Gói nén tải về (bytes)": "5,747,950",
            "Giải nén kèm ảnh (bytes)": "7,009,846",
            "Chỉ giữ .tex/.bib/.bbl (bytes)": "138,706",
            "Mức giảm": "-98.02%",
        },
    ])
    show_pending_box(
        "Bảng đối chiếu kích thước byte và biểu đồ so sánh tuyến tính/logarit tại Mục 3.3",
        pilot_size_df,
    )
```

- **Tác động định lượng của việc loại bỏ hình ảnh nhị phân & Bảo toàn `.tex / .bib / .bbl`:** Bảng số liệu trình bày đồng thời ở cả cấp bài báo lẫn cấp phiên bản giải nén để bảo đảm tính minh bạch tuyệt đối:
  - Ở cấp bài báo (tổng hợp mọi phiên bản), kích thước gói nén tải về trung bình là `7.440.290 B (~7,10 MiB/bài)` và kích thước giải nén gốc kèm ảnh là **9.104.284 B (~8,68 MiB/bài)**. Sau khi trích xuất chọn lọc loại bỏ toàn bộ ảnh nhị phân và chỉ giữ lại **`.tex`, `.bib` và `.bbl`**, dung lượng lưu trữ chỉ còn **924.821 B (~903,1 KiB/bài)**, đạt mức giảm dung lượng thực tế **-89,84%** (chỉ giữ lại **10,16%** dung lượng ban đầu). Việc bảo toàn đầy đủ tệp `.bbl` xuyên suốt cả 5 dải chỉ chiếm tỷ trọng dung lượng rất nhỏ nhưng khôi phục nguyên vẹn nguồn trích dẫn cho hàng trăm bài báo không đính kèm `.bib`, phục vụ trực tiếp quá trình chuyển đổi ngược về `BibtexRow` ở Milestone 2.
  - Ở cấp phiên bản giải nén, dung lượng gói nén tải về trung bình là `4.610.562 B (~4,40 MiB/phiên bản)` và dung lượng giải nén gốc giảm mạnh từ **5.876.765 B (~5,60 MiB/phiên bản)** xuống còn **596.967 B (~583,0 KiB/phiên bản)**, cũng ghi nhận mức giảm **-89,84%**.
  - Kết quả này chứng minh hình ảnh nhị phân (ảnh biểu đồ `.pdf`, vector `.eps`, bitmap `.png`/`.jpg`) chiếm tới gần **90%** (**89,84%**) tổng trọng lượng giải nén của các gói nguồn trên arXiv.
- **Khử trùng lặp liên phiên bản (`cross_version_dedup`):** Phân tích hàm băm SHA-256 trên tập **10.276 bài báo đa phiên bản có mã nguồn** cho thấy có tới **35.458 tệp** hoàn toàn trùng khớp nội dung giữa các phiên bản (chiếm **6.444.652.027 B (~6,00 GiB)**, tương đương tỷ lệ trùng lặp **38,86%** dung lượng mã nguồn). Ngoài ra, có **694 cặp phiên bản** hoàn toàn không thay đổi bất kỳ tệp mã nguồn nào (chỉ cập nhật metadata hoặc lời nhận xét trên arXiv). Đây là phát hiện thực nghiệm quý giá làm đầu vào trực tiếp cho mô-đun Deduplication ở Milestone 2.
- **Lợi ích thiết thực cho toàn chuỗi dự án:** Việc lọc bỏ hình ảnh ngay trong luồng giải nén Cut-Through / `_FastGzipStream` giúp gói gọn toàn bộ kho ngữ liệu **25.000 bài báo** (**41.615 phiên bản**) chỉ còn **22,52 GiB** (`22,517 GiB`) trên đĩa thay vì hàng trăm GiB, bảo toàn hoàn toàn dung lượng khả dụng của máy ảo và tối ưu hóa vượt bậc tốc độ I/O cho bộ phân tích cú pháp LaTeX ở Milestone 2.

---

## 3.4. Thống kê Tài liệu Tham khảo & Tỷ lệ Thành công Siêu dữ liệu Semantic Scholar

```{code-cell} ipython3
:tags: [remove-input]

if HAS_STATS:
    fig, (ax_ref, ax_rate) = plt.subplots(1, 2, figsize=(10.5, 3.8))

    refs_s = papers_df["n_refs"].dropna() if "n_refs" in papers_df else pd.Series(dtype=float)
    x_label_ref = "Số lượng tham khảo mỗi bài báo"
    if not refs_s.empty:
        plot_refs = refs_s
        if len(refs_s) >= 100:
            p99 = float(refs_s.quantile(0.99))
            if p99 > 0 and float(refs_s.max()) > p99 * 1.8:
                plot_refs = refs_s.clip(upper=p99)
                x_label_ref = f"Số lượng tham khảo / bài (gộp đuôi >= P99 = {p99:.0f})"
        ax_ref.hist(
            plot_refs,
            bins=min(30, max(int(plot_refs.nunique()), 5)),
            color="#0ca678",
            edgecolor="white",
        )
        ax_ref.axvline(
            refs_s.mean(),
            color="#e03131",
            linestyle="--",
            linewidth=1.4,
            label=f"TB: {refs_s.mean():.2f}",
        )
        ax_ref.axvline(
            refs_s.median(),
            color="#1864ab",
            linestyle="-.",
            linewidth=1.4,
            label=f"Trung vị: {refs_s.median():.1f}",
        )
        ax_ref.legend()
    ax_ref.set_xlabel(x_label_ref)
    ax_ref.set_ylabel("Số lượng bài báo")
    ax_ref.set_title("Phân phối số tài liệu tham khảo / bài")

    rate_labels = [
        "(a) Độ phủ bài báo\ntrên S2",
        "(b) TB tham khảo đủ\nTiêu đề+Tác giả+Năm",
        "(c) Tham khảo có\nđịnh danh arXiv ID",
    ]
    rate_vals = [
        (summary.get("s2_coverage_papers") or 0.0) * 100,
        (summary.get("mean_refs_complete_ratio") or 0.0) * 100,
        (summary.get("share_refs_with_arxiv_id") or 0.0) * 100,
    ]
    bars_r = ax_rate.bar(rate_labels, rate_vals, color=["#1971c2", "#2f9e44", "#f08c00"], width=0.48)
    ax_rate.set_ylim(0, 115)
    ax_rate.set_ylabel("Tỷ lệ (%)")
    ax_rate.set_title("Ba tỷ lệ siêu dữ liệu tham khảo S2")
    for b, v in zip(bars_r, rate_vals):
        ax_rate.text(
            b.get_x() + b.get_width() / 2,
            b.get_height() + 2,
            f"{v:.2f}%",
            ha="center",
            fontweight="bold",
            fontsize=9,
        )

    plt.tight_layout()
    plt.show()
    plt.close(fig)

    if not refs_s.empty:
        q = refs_s.quantile([0.25, 0.5, 0.75, 0.95, 1.0])
        ref_stats_df = pd.DataFrame([
            {
                "Tổng tham khảo thu được": fmt_int(summary.get("refs_total")),
                "Tham khảo có arXiv ID (vào bảng references)": fmt_int(summary.get("refs_with_arxiv_id")),
                "Trung bình / bài": f"{float(refs_s.mean()):.2f}",
                "Q25": round(float(q[0.25]), 1),
                "Trung vị (Q50)": round(float(q[0.5]), 1),
                "Q75": round(float(q[0.75]), 1),
                "P95": round(float(q[0.95]), 1),
                "Cực đại (Max)": int(q[1.0]),
            }
        ])
        show_table(ref_stats_df)
else:
    show_pending_box(
        "Biểu đồ phân phối tham khảo, biểu đồ 3 tỷ lệ S2 (a)(b)(c) và bảng phân vị Q25–Max tại Mục 3.4"
    )
```

- **Phân phối số tham khảo trên mỗi bài báo:**
  - Tổng số tài liệu tham khảo thu được trên toàn bộ 25.000 bài báo là **1.055.072 mục**.
  - Giá trị trung vị ($Q_{50}$) đạt **37,0 mục/bài**, với các phân vị $Q_{25} = 21{,}0$, $Q_{75} = 56{,}0$, $P_{95} = 97{,}0$ và $P_{99} = 160{,}0$, phản ánh rằng đại đa số công bố khoa học có từ 21 đến 56 trích dẫn (có `1.677` bài ghi nhận `0` tham khảo, gồm `1.665` bài ở trạng thái `found` chưa có liên kết trích dẫn trích xuất trên S2 và `12` bài `not_indexed`).
  - Giá trị trung bình toàn cục đạt **42,20 mục/bài** (`42,22` trên nhóm `found`), bám sát trung vị `37,0` và tuân theo đúng quy luật phân phối lệch phải tự nhiên của văn bản khoa học: giá trị cực đại là **770 mục** (bài khảo sát `2408.15323`) và **không có bất kỳ bài báo nào vượt quá `1.000` tham khảo** — chứng minh việc siết điều kiện phân trang `_references_truncated()` trong `v3.18` đã triệt tiêu hoàn toàn hiện tượng lặp trang giả tạo từng gặp ở phiên bản cũ.
- **Giải nghĩa, đánh giá ba tỷ lệ chất lượng & Minh bạch hóa `HTTP 404` trên Semantic Scholar:** Nhóm bóc tách rành mạch ba chỉ số bổ trợ nhau cùng tỷ lệ `HTTP 404` thực tế của S2 API:
  - **Tỷ lệ (a) — Độ phủ bài báo (`s2_coverage_papers`) & Tách bạch `HTTP 404` của S2 API so với nhánh dự phòng cục bộ:** Trong `summary.json`, có **24.988 / 25.000 bài báo (`99,95%`)** có dữ liệu ở trạng thái `found` và **12 bài (`0,05%`)** giữ nguyên trạng thái `not_indexed` (`raw: {"status": 404}`). Đối chiếu trực tiếp toàn bộ `25.000` tệp phản hồi gốc `s2_references.raw.json.gz` cho thấy: có **24.972 / 25.000 bài báo (`99,89%`)** nhận phản hồi `HTTP 200 OK` trực tiếp từ **Semantic Scholar Graph API** (`24.968` bài qua `POST /paper/batch` và `4` bài gọi phân trang `GET /references`), trong khi tổng cộng **28 bài (`0,11%`)** bị S2 API trả `HTTP 404` (do độ trễ lập chỉ mục đối với một số bản thảo mới hoặc chuyên ngành hẹp). Trong `28` bài S2 trả `404` này, có **16 bài (`0,06%`)** sở hữu danh mục `.bib`/`.bbl` hợp lệ đã được khôi phục cục bộ qua nhánh dự phòng `--enable-bib-fallback` (được đóng dấu nguồn gốc riêng `source: "local_bib"` trong dữ liệu thô) và **12 bài (`0,05%`)** không có tham chiếu `.bib`/`.bbl` nên giữ nguyên `not_indexed`. Cách báo cáo tách lớp này bảo đảm phản ánh trung thực độ phủ thực tế `99,89%` (`28` ca `404`) của S2 API mà không bị che khuất bởi nguồn dự phòng cục bộ.
  - **Tỷ lệ (b) — Độ hoàn chỉnh siêu dữ liệu tham khảo (`mean_refs_complete_ratio`):** Đạt **85,55%**. Trung bình mỗi bài báo có tới 85,55% số trích dẫn thu thập được đầy đủ cả ba trường thông tin nòng cốt: *tiêu đề, danh sách tác giả và năm công bố*.
  - **Tỷ lệ (c) — Tỷ trọng tham khảo có arXiv ID (`share_refs_with_arxiv_id`):** Toàn tập ghi nhận **499.378 / 1.055.072** trích dẫn mang định danh arXiv hợp lệ, tương ứng tỷ trọng toàn cục rất cao là **47,33%**, cung cấp tập ứng viên đối sánh (*matching pool*) dồi dào và sạch nhiễu cho bài toán liên kết tham khảo ở Milestone 3.
