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

```{admonition} Phạm vi bộ số liệu hiện tại: 15.000 / 25.000 ID (Sẽ cập nhật khi hoàn tất đủ 25.000 ID)
:class: note
Số liệu và biểu đồ trong chương này hiện được tổng hợp trực tiếp từ **bản chụp 15.000 định danh đầu tiên đã thu thập hoàn chỉnh** (`2408.01045` – `2408.16044`, trọn vẹn Dải 1, Dải 2 và Dải 3 thuộc tháng `2024-08`, chiếm **60%** tổng phạm vi được giao). **Ngay khi tiến trình thu thập trên Google Colab CPU hoàn tất 10.000 ID còn lại (Dải 4 và Dải 5) để đạt đủ 25.000 ID, toàn bộ tệp trong `stats/` cùng các con số nhận xét dưới đây sẽ được cập nhật đồng bộ.**
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
    for candidate in (
        Path("../stats"),
        Path("stats"),
        *[parent / "stats" for parent in Path.cwd().parents],
    ):
        if candidate.is_dir():
            return candidate
    return Path("../stats")


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
        "<code>python src/export_data.py --data-dir data</code> vào <code>arxiv-book/stats/</code> "
        "và biên dịch lại sách (không cần chỉnh sửa mã).</div>"
        "</div>"
    )
    display(HTML(html))
    if preview_df is not None:
        show_table(preview_df, kv=kv)


if HAS_STATS:
    summary = json.loads((STATS_DIR / "summary.json").read_text(encoding="utf-8"))
    papers_df = pd.read_csv(STATS_DIR / "papers_stats.csv")
    versions_df = pd.read_csv(STATS_DIR / "versions_stats.csv")

    b_paper = summary.get("mean_bytes_per_paper", {})
    b_ver = summary.get("mean_bytes_per_extracted_version", {})
    req_count = int(summary.get("ids_requested") or 0)
    req_label = (
        "Tổng số ID yêu cầu trong 5 dải (ids_requested)"
        if req_count >= 25000
        else f"Tổng số ID yêu cầu trong đợt thống kê hiện tại (ids_requested — {req_count:,}/25,000 ID)"
    )

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
        ("Kích thước TB mỗi bài báo SAU khi bỏ ảnh — chỉ .tex/.bib (bytes)", fmt_bytes_dual(b_paper.get("kept_tex_bib"))),
        ("Tỷ lệ dung lượng giữ lại trên tổng dung lượng giải nén", fmt_pct(summary.get("kept_over_raw_uncompressed"))),
        ("Số tài liệu tham khảo trung bình mỗi bài báo", fmt_float(summary.get("mean_refs_per_paper"))),
        ("Độ phủ bài báo tìm thấy trên Semantic Scholar — tỷ lệ (a)", fmt_pct(summary.get("s2_coverage_papers"))),
        ("Tỷ lệ thành công TB thu thập đủ siêu dữ liệu tham khảo — tỷ lệ (b)", fmt_pct(summary.get("mean_refs_complete_ratio"))),
        ("Tỷ lệ tham khảo mang định danh arXiv ID — tỷ lệ (c)", fmt_pct(summary.get("share_refs_with_arxiv_id"))),
    ]
    show_table(pd.DataFrame(overview_rows, columns=["Chỉ số thống kê dữ liệu thu thập", "Giá trị đo đạc"]), kv=True)
else:
    pilot_preview = pd.DataFrame(
        [
            ("Tổng số ID yêu cầu trong 5 dải (ids_requested)", "⏳ Chờ stats/summary.json (Pilot: 30)"),
            ("Số bài báo thu thập thành công đủ mọi phiên bản (papers_success)", "⏳ Chờ stats/summary.json (Pilot: 30 / 30)"),
            ("Tỷ lệ thành công chung cấp bài báo (success_rate_papers)", "⏳ Chờ stats/summary.json (Pilot: 100.00%)"),
            ("Tổng số cặp (bài báo, phiên bản) đã khám phá (pairs_total)", "⏳ Chờ stats/summary.json (Pilot: 57; TB 1.90 bản/bài)"),
            ("Kích thước TB mỗi bài báo TRƯỚC khi bỏ ảnh (bytes)", "⏳ Chờ stats/summary.json (Pilot: 11,916,738 B — 11.36 MiB)"),
            ("Kích thước TB mỗi bài báo SAU khi bỏ ảnh — chỉ .tex/.bib (bytes)", "⏳ Chờ stats/summary.json (Pilot: 235,800 B — 230.3 KiB)"),
            ("Số tài liệu tham khảo trung bình mỗi bài báo", "⏳ Chờ stats/summary.json (Pilot: 33.63)"),
            ("Ba tỷ lệ siêu dữ liệu tham khảo S2: (a) / (b) / (c)", "⏳ Chờ stats/summary.json (Pilot: 100.00% / 78.02% / 50.35%)"),
        ],
        columns=["Chỉ số thống kê cốt lõi (Mục 3.1)", "Trạng thái / Đối chiếu Pilot 30 ID"],
    )
    show_pending_box("Bảng tổng hợp 16 chỉ số thu thập cốt lõi tại Mục 3.1", pilot_preview, kv=True)
```

**Phân tích kết quả tổng quan (trên bản chụp 15.000 ID hiện tại — sẽ cập nhật khi đủ 25.000 ID):**

- **Định nghĩa chặt chẽ về bài báo thu thập thành công:** Các định danh không tồn tại trên hệ thống arXiv (`ids_not_found` — HTTP `404` sau bước xác nhận đơn lẻ) được tách riêng khỏi mẫu số `papers_total`. Một bài báo chỉ được tính vào `papers_success` khi **mọi phiên bản từ $v_1$ tới $v_N$** của nó đều hoàn tất xử lý với trạng thái hợp lệ (`ok`, `ok_no_tex` hoặc `no_source`), đảm bảo không có bất kỳ phiên bản nào bị khuyết hoặc lỗi giữa chừng.
- **Độ bao phủ định danh và tỷ lệ hoàn tất cao:** Toàn bộ **`15.000 / 15.000` định danh yêu cầu** trong ba dải tháng `2024-08` (`2408.01045` – `2408.16044`) đều tồn tại hợp lệ trên hệ thống arXiv (`ids_not_found = 0`, `papers_total = 15.000`). Bộ thu thập hoàn tất trọn vẹn mọi phiên bản cho **`14.928` bài báo**, đạt **tỷ lệ thành công chung cấp bài báo `99,52%`** (`success_rate_papers`) và **cấp phiên bản `99,68%`** (`24.656 / 24.734` cặp phiên bản hợp lệ). Chỉ có `72` bài báo (`0,48%`) có ít nhất một phiên bản rơi vào ngoại lệ dữ liệu thượng nguồn (phiên bản rút bài trả về HTTP `404` hoặc tên tệp thiết bị dành riêng của Windows trong gói nén).
- **Tỷ trọng bài báo có mã nguồn LaTeX:** Có **`13.742 / 15.000` bài báo (`91,61%`)** sở hữu ít nhất một phiên bản chứa mã nguồn `.tex`/`.bib` (`papers_with_tex`) phục vụ trực tiếp cho bộ phân tích cấu trúc tài liệu ở Milestone 2; `1.258` bài còn lại (chủ yếu là các công bố chỉ nộp tệp PDF biên dịch sẵn) vẫn được bảo toàn đầy đủ siêu dữ liệu cấp bài báo và danh sách trích dẫn chuẩn hóa. *(Các chỉ số tổng hợp này sẽ được cập nhật lên toàn tập khi hoàn tất đủ 25.000 ID).*

---

## 3.2. Độ Bao phủ Phiên bản ($v_1 \dots v_N$) & Phân bố Trạng thái Nguồn

```{code-cell} ipython3
:tags: [remove-input]

if HAS_STATS:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.5, 3.8))

    status_keys = ["ok", "no_source", "ok_no_tex", "not_found", "corrupt", "failed"]
    status_names = ["ok (.tex/.bib)", "no_source (PDF)", "ok_no_tex", "not_found", "corrupt", "failed"]
    status_colors = ["#2b8a3e", "#1971c2", "#f08c00", "#868e96", "#e03131", "#c92a2a"]
    pairs_by_status = summary.get("pairs_by_status", {})
    s_counts = [int(pairs_by_status.get(k, 0)) for k in status_keys]
    total_p = max(sum(s_counts), 1)

    bars1 = ax1.barh(status_names, s_counts, color=status_colors)
    ax1.invert_yaxis()
    ax1.set_xlabel("Số lượng phiên bản")
    ax1.set_title("Phân bố trạng thái xử lý các phiên bản")
    for b, c in zip(bars1, s_counts):
        if c > 0:
            pct = c / total_p * 100
            pct_str = "<0.01%" if pct < 0.01 else f"{pct:.2f}%"
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

- **Phân bố trạng thái gói nguồn (`24.734` phiên bản):** Kết quả phân loại trên tập 15.000 ID hiện tại phản ánh sát đặc trưng xuất bản thực tế trên arXiv: **`22.921` phiên bản (`92,67%`)** trích xuất thành công cây mã nguồn `.tex`/`.bib` (`ok`), **`1.734` phiên bản (`7,01%`)** chỉ cung cấp tệp PDF biên dịch sẵn (`no_source`) [[4, 5]](#tai-lieu-tham-khao) và `1` phiên bản (`< 0,01%`) là gói nén hợp lệ không kèm tệp TeX (`ok_no_tex`). Nhóm ngoại lệ chỉ chiếm **`0,32%`** (`78` phiên bản), được bóc tách minh bạch thành ba nguyên nhân:
  - `63` phiên bản (`0,25%`, tập trung ở các bản sửa đổi `v2: 33`, `v3: 15`, `v4+: 12`, `v1: 3`) trả về HTTP `404` trên `/src/{id}vK` (`not_found`) do tác giả đã rút (*withdrawn*) phiên bản đó trên arXiv nên máy chủ không phát hành gói nguồn;
  - `14` phiên bản (`0,06%`) bị bộ giải nén an toàn cô lập sang `corrupt` vì gói nguồn chứa tên thiết bị dành riêng của Windows (`aux`, `con.tex`, `AAAI25/LaTeX/con.pdf`, `Sections/con.tex` — `10` bản) hoặc trùng đường dẫn đầu ra khi chuẩn hóa (`fig_texts/fig1.tex`, `Methodology.tex`, `JSSC.bib` — `4` bản);
  - Duy nhất `1` phiên bản (`< 0,01%`) ngắt luồng truyền tải giữa chừng (`ChunkedEncodingError` — trạng thái `failed`, sẽ tự động tải bù ở đợt cập nhật 25.000 ID).
- **Phân phối số phiên bản mỗi bài báo ($\bar{V} = 1{,}65$):** Chu kỳ hoàn thiện bản thảo khoa học tuân theo phân phối lệch phải điển hình với trung bình **`1,65` phiên bản/bài** (`24.734` phiên bản trên `15.000` bài): **`8.636` bài (`57,57%`)** dừng ở bản nộp gốc `v1`, **`4.176` bài (`27,84%`)** có `2` phiên bản, **`1.487` bài (`9,91%`)** có `3` phiên bản, **`430` bài (`2,87%`)** có `4` phiên bản, **`172` bài (`1,15%`)** có `5` phiên bản và giảm nhanh ở phần đuôi dài (nhóm `v8+` có `20` bài, cực đại đạt tới **`26` phiên bản**). *(Phân bố toàn cục sẽ được cập nhật khi hoàn tất đủ 25.000 ID).*

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
            "Sau khi lọc chỉ giữ .tex/.bib (bytes)": _safe_round(b_paper.get("kept_tex_bib")),
            "Mức giảm dung lượng": _reduction_pct(
                b_paper.get("raw_uncompressed_with_images"), b_paper.get("kept_tex_bib")
            ),
        },
        {
            "Đơn vị tính trung bình": "Mỗi phiên bản giải nén (ok / ok_no_tex)",
            "Gói nén tải về (bytes)": _safe_round(b_ver.get("raw_archive")),
            "Giải nén gốc kèm ảnh (bytes)": _safe_round(b_ver.get("raw_uncompressed_with_images")),
            "Sau khi lọc chỉ giữ .tex/.bib (bytes)": _safe_round(b_ver.get("kept_tex_bib")),
            "Mức giảm dung lượng": _reduction_pct(
                b_ver.get("raw_uncompressed_with_images"), b_ver.get("kept_tex_bib")
            ),
        },
    ])
    show_table(size_df)

    labels = [
        "Gói nén tải về\n(raw_archive)",
        "Giải nén kèm ảnh\n(raw_uncompressed)",
        "Chỉ giữ .tex & .bib\n(kept_tex_bib)",
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
            "Chỉ giữ .tex/.bib (bytes)": "235,800",
            "Mức giảm": "-98.02%",
        },
        {
            "Đơn vị tính (Đối chiếu Pilot 30 ID)": "Mỗi phiên bản giải nén (ok)",
            "Gói nén tải về (bytes)": "5,747,950",
            "Giải nén kèm ảnh (bytes)": "7,009,846",
            "Chỉ giữ .tex/.bib (bytes)": "138,706",
            "Mức giảm": "-98.02%",
        },
    ])
    show_pending_box(
        "Bảng đối chiếu kích thước byte và biểu đồ so sánh tuyến tính/logarit tại Mục 3.3",
        pilot_size_df,
    )
```

- **Tác động định lượng của việc loại bỏ hình ảnh nhị phân:** Bảng số liệu trình bày đồng thời ở cả cấp bài báo (tổng hợp mọi phiên bản $v_1 \dots v_N$) lẫn cấp phiên bản giải nén (`ok` / `ok_no_tex`) để đảm bảo tính minh bạch tuyệt đối:
  - **Tính trung bình trên mỗi bài báo (`15.000` bài):** Dung lượng gói nén tải về là **`7.266.080 B` (`6,93 MiB`)**, bung nén toàn phần kèm hình ảnh lên tới **`8.748.555 B` (`8,34 MiB`)**, nhưng sau khi lọc chọn lọc chỉ giữ `.tex` và `.bib` giảm mạnh xuống còn **`680.145 B` (`664,2 KiB`)**.
  - **Tính trung bình trên mỗi phiên bản giải nén (`22.922` bản):** Kích thước giảm từ **`5.724.994 B` (`5,46 MiB`)** giải nén gốc (gói nén `4.552.952 B` — `4,34 MiB`) xuống chỉ còn **`445.082 B` (`434,7 KiB`)**.
  - Kết quả thực nghiệm khẳng định các tệp hình minh họa độ phân giải cao, biểu đồ vector PDF/EPS và phụ lục nhị phân chiếm tới **`92,23%`** tổng dung lượng giải nén, trong khi toàn bộ mã nguồn văn bản `.tex` và cơ sở dữ liệu `.bib` chỉ chiếm **`7,77%`** dung lượng gốc (`kept_over_raw_uncompressed`).
- **Lợi ích thiết thực cho toàn chuỗi dự án:** Ngay trên 15.000 bài báo đầu tiên, phương pháp trích xuất chọn lọc đã loại bỏ hơn **`~112,7 GiB`** dữ liệu hình ảnh không cần thiết (so với `~122,2 GiB` nếu giải nén toàn phần), giữ gọn kho làm việc quanh ngưỡng `~10,1 GiB` (và ước tính tiết kiệm gần `~190 GiB` khi cập nhật đủ **25.000 ID**), vừa nằm gọn trong ổ SSD cục bộ của instance Google Colab CPU vừa giảm mạnh chi phí đọc I/O cho bộ phân tích cú pháp ở Milestone 2.

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
                "Trung bình / bài": round(float(refs_s.mean()), 2),
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

- **Phân phối số tham khảo trên mỗi bài báo (`620.210` mục tham khảo):** Trên tập 15.000 bài báo hiện tại, hệ thống thu thập được trung bình **`41,35` tham khảo/bài** (`41,41` tính riêng trên `14.978` bài được S2 lập chỉ mục), cao hơn giá trị trung vị **`36,0` tham khảo/bài** (`Q25 = 20,0`; `Q75 = 55,0`; `P95 = 96,0`; `P99 = 162,0`). Độ lệch giữa trung bình và trung vị phản ánh nhóm bài tổng quan (*survey/review*) có danh mục trích dẫn rất lớn (cực đại đạt **`770` tham khảo/bài**; có **`647` bài vượt ngưỡng `100` tham khảo** đã kích hoạt thành công cơ chế phân trang dự phòng `referenceCount > len(references)` để không bị cắt bớt dữ liệu). Ở chiều ngược lại, `1.159` bài trả về `0` tham khảo do trình trích xuất PDF tự động của S2 chưa bóc tách được danh mục tham khảo từ bản thảo mới và sẽ được đối chiếu trực tiếp với nguồn `.tex`/`.bib` ở Milestone 2.
- **Giải nghĩa và đánh giá ba tỷ lệ chất lượng siêu dữ liệu Semantic Scholar:** Thay vì gộp chung thành một con số dễ gây hiểu nhầm, nhóm bóc tách rành mạch ba chỉ số bổ trợ nhau (sẽ được cập nhật tiếp khi hoàn tất đủ 25.000 ID):
  - **Tỷ lệ (a) — Độ phủ bài báo (`s2_coverage_papers = 99,85%`):** Có **`14.978 / 15.000` bài báo** được Semantic Scholar lập chỉ mục và nhận diện thành công (`found`), chỉ có `22` bài (`0,15%`) chưa được lập chỉ mục (`not_indexed`).
  - **Tỷ lệ (b) — Độ hoàn chỉnh siêu dữ liệu tham khảo (`mean_refs_complete_ratio = 85,60%`):** Trung bình theo từng bài báo (trên tập bài có ít nhất 1 tham khảo), **`85,60%`** các mục tham khảo thu được đầy đủ cả ba trường cốt lõi gồm *tiêu đề, danh sách tác giả và ngày/năm công bố*; khoảng `14,40%` còn lại chủ yếu là trích dẫn trang web, kho mã nguồn, bộ dữ liệu hoặc tài liệu kỹ thuật không có năm/tác giả chuẩn.
  - **Tỷ lệ (c) — Tỷ trọng tham khảo có arXiv ID (`share_refs_with_arxiv_id = 46,19%`):** Có **`286.448 / 620.210` mục tham khảo** mang định danh `arXiv ID` hợp lệ (phần còn lại là công bố trên tạp chí/hội nghị truyền thống hoặc sách chuyên khảo không lưu bản thảo trên arXiv). Tập `286.448` liên kết trích dẫn này (sau khi khử trùng lặp khóa kép) chính là nguồn cấu thành bảng `references.parquet` phục vụ bài toán đối sánh tham khảo ở Milestone 3.
