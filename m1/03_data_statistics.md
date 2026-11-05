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
    "font.size": 9.5,
    "axes.titlesize": 11,
    "axes.titleweight": "bold",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.axisbelow": True,
    "axes.grid": True,
    "grid.alpha": 0.25,
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

    overview_rows = [
        ("Tổng số ID yêu cầu trong 5 dải (ids_requested)", fmt_int(summary.get("ids_requested"))),
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

**Phân tích kết quả tổng quan:**

- **Định nghĩa chặt chẽ về bài báo thu thập thành công:** Các định danh không tồn tại trên hệ thống arXiv (`ids_not_found` — HTTP `404` sau bước xác nhận đơn lẻ) được tách riêng khỏi mẫu số `papers_total`. Một bài báo chỉ được tính vào `papers_success` khi **mọi phiên bản từ $v_1$ tới $v_N$** của nó đều hoàn tất xử lý với trạng thái hợp lệ (`ok`, `ok_no_tex` hoặc `no_source`), đảm bảo không có bất kỳ phiên bản nào bị khuyết hoặc lỗi giữa chừng.

```{admonition} ⏳ Chờ cập nhật nhận xét độ bao phủ từ arxiv-book/stats/summary.json
:class: warning pending-stats
- **Tệp & trường cần đợi:** `arxiv-book/stats/summary.json` (`ids_requested`, `ids_not_found`, `papers_total`, `papers_success`, `success_rate_papers`, `papers_with_tex`).
- **Nội dung cần điền khi có tệp:** Bổ sung 2–3 câu nhận xét số bài thu thập thành công, tỷ lệ thành công chung và tỷ lệ bài báo có mã nguồn TeX trên toàn tập 25.000 ID *(đối chiếu tập Pilot 30 ID đầu Dải 1: thu thập thành công `30/30` bài = `100,00%`, trong đó `27/30` bài = `90,00%` có mã nguồn `.tex`/`.bib` và `3` bài nộp thuần PDF)*.
```

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
            ax1.text(
                b.get_width() + total_p * 0.015,
                b.get_y() + b.get_height() / 2,
                f"{c:,} ({c / total_p * 100:.1f}%)",
                va="center",
                fontsize=8.5,
            )
    ax1.set_xlim(0, max(s_counts) * 1.32 if max(s_counts) else 10)

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

- **Phân bố trạng thái gói nguồn:** Kết quả phân loại phản ánh sát đặc trưng xuất bản thực tế trên arXiv: đại đa số các phiên bản cung cấp đầy đủ gói nguồn LaTeX (`ok`), trong khi một tỷ lệ nhỏ chỉ có tệp PDF biên dịch sẵn (`no_source`) [[4, 5]](#tai-lieu-tham-khao). Nhờ cơ chế kiểm tra mã HTTP trước *magic bytes* và tự động chạy lại các phiên lỗi mạng tạm thời, kho dữ liệu tách bạch minh bạch giữa bản nộp không có mã nguồn và lỗi thu thập.
- **Phân phối số phiên bản mỗi bài báo:** Chu kỳ hoàn thiện bản thảo khoa học tuân theo phân phối lệch phải điển hình: phần lớn bài báo dừng ở `1` phiên bản (bản nộp đầu) hoặc `2` phiên bản (cập nhật sau phản biện hội nghị/tạp chí), và giảm nhanh từ `v3` trở đi. Hệ số phiên bản trung bình $\bar{V}$ nhân trực tiếp tổng số gói nguồn thực tế cần tải lên gần gấp đôi số định danh gốc được giao.

```{admonition} ⏳ Chờ cập nhật tỷ lệ trạng thái phiên bản từ arxiv-book/stats/summary.json
:class: warning pending-stats
- **Tệp & trường cần đợi:** `arxiv-book/stats/summary.json` (`pairs_total`, `pairs_by_status`, `versions_per_paper`, `mean_versions_per_paper`).
- **Nội dung cần điền khi có tệp:** Ghi tỷ lệ phần trăm chính xác của trạng thái `ok`, `no_source`, `ok_no_tex` (và `corrupt`/`failed` nếu có) cùng $\bar{V}$ trên toàn tập 25.000 ID *(đối chiếu Pilot 30 ID: `51/57` bản `ok` = `89,47%`, `6/57` bản `no_source` = `10,53%`, `0` lỗi; $\bar{V} = 1{,}90$ phiên bản/bài, phân bố `v1: 13`, `v2: 10`, `v3: 5`, `v4: 1`, `v5: 1`)*.
```

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

- **Tác động của việc loại bỏ hình ảnh nhị phân:** Bảng số liệu trình bày đồng thời ở cả cấp bài báo (tổng hợp mọi phiên bản $v_1 \dots v_N$) lẫn cấp phiên bản giải nén để đảm bảo tính minh bạch tuyệt đối. Kết quả đo đạc bằng byte khẳng định các tệp hình minh họa độ phân giải cao, biểu đồ vector PDF/EPS và phụ lục nhị phân chiếm tới **96% – 98%** tổng dung lượng giải nén, trong khi toàn bộ mã nguồn văn bản `.tex` và dữ liệu `.bib` chỉ chiếm khoảng **`~2%`** dung lượng gốc.
- **Lợi ích thiết thực cho toàn chuỗi dự án:** Việc lọc bỏ hình ảnh ngay trong luồng giải nén giúp tiết kiệm hàng trăm GiB không gian lưu trữ cho 25.000 bài báo, giữ trọn vẹn kho ngữ liệu trong giới hạn ổ đĩa cục bộ của instance Google Colab CPU và giảm mạnh chi phí đọc I/O cho bộ phân tích cú pháp ở Milestone 2.

```{admonition} ⏳ Chờ cập nhật số byte trung bình từ arxiv-book/stats/summary.json
:class: warning pending-stats
- **Tệp & trường cần đợi:** `arxiv-book/stats/summary.json` (`mean_bytes_per_paper`, `mean_bytes_per_extracted_version`, `kept_over_raw_uncompressed`).
- **Nội dung cần điền khi có tệp:** Cập nhật câu nhận xét với số byte trung bình chính thức trước và sau khi lọc ảnh của 25.000 bài báo *(đối chiếu Pilot 30 ID: trung bình mỗi bài báo giảm từ `11.916.738 B` xuống `235.800 B`, và mỗi phiên bản giải nén giảm từ `7.009.846 B` xuống `138.706 B` — tiết kiệm `98,02%` dung lượng)*.
```

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

- **Phân phối số tham khảo trên mỗi bài báo:** Khoảng cách giữa giá trị trung bình và trung vị phản ánh sự hiện diện của các bài báo tổng quan (*survey/review*) chứa hàng trăm tài liệu trích dẫn — nhóm bài này minh chứng hiệu quả thực tế của cơ chế kiểm tra `referenceCount > len(references)` để tự động gọi phân trang lấy trọn danh sách trên Semantic Scholar. Ngược lại, một số ít bài báo trả về `0` tham khảo do trình phân tích tự động của Semantic Scholar chưa tách được mục tài liệu tham khảo từ bố cục PDF gốc.
- **Giải nghĩa ba tỷ lệ thành công siêu dữ liệu tham khảo:** Thay vì gộp chung thành một con số dễ gây hiểu nhầm, nhóm bóc tách rành mạch ba chỉ số bổ trợ nhau:
  - **Tỷ lệ (a) — Độ phủ bài báo (`s2_coverage_papers`):** Tỷ phần bài báo gốc trong kho được Semantic Scholar lập chỉ mục và nhận diện thành công.
  - **Tỷ lệ (b) — Độ hoàn chỉnh siêu dữ liệu tham khảo (`mean_refs_complete_ratio`):** Trung bình theo từng bài báo (trên tập bài có ít nhất 1 tham khảo) của tỷ lệ các mục tham khảo thu được đầy đủ cả ba trường cốt lõi gồm *tiêu đề, danh sách tác giả và ngày/năm công bố* (khoảng `~20%` còn lại thường là trích dẫn trang web, kho phần mềm, tiêu chuẩn kỹ thuật hoặc mục trích dẫn không chuẩn khiến S2 khuyết năm/tác giả).
  - **Tỷ lệ (c) — Tỷ trọng tham khảo có arXiv ID (`share_refs_with_arxiv_id`):** Tỷ phần các tài liệu được trích dẫn có bản lưu trên arXiv (phần còn lại là công bố trên tạp chí/hội nghị truyền thống hoặc sách chuyên khảo không đăng tải lên arXiv). Đây chính là tập cặp trích dẫn cấu thành bảng `references` phục vụ đối sánh ở Milestone 3.

```{admonition} ⏳ Chờ cập nhật thống kê tham khảo từ arxiv-book/stats/summary.json & papers_stats.csv
:class: warning pending-stats
- **Tệp & trường cần đợi:** `arxiv-book/stats/summary.json` (`refs_total`, `refs_with_arxiv_id`, `mean_refs_per_paper`, `s2_coverage_papers`, `mean_refs_complete_ratio`, `share_refs_with_arxiv_id`) và `arxiv-book/stats/papers_stats.csv` (cột `n_refs`).
- **Nội dung cần điền khi có tệp:** Chốt nhận xét ngắn gọn với số tham khảo trung bình/trung vị và 3 tỷ lệ `(a)`, `(b)`, `(c)` của toàn tập 25.000 ID *(đối chiếu Pilot 30 ID: tổng `1.009` tham khảo, `508` tham khảo có arXiv ID, trung bình `33,63` tham khảo/bài; `(a) = 100,00%`, `(b) = 78,02%`, `(c) = 50,35%`)*.
```
