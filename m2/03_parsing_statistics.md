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

# Chương 7. Thống kê Phân tích Cú pháp & Hiệu quả Khử trùng lặp

Toàn bộ bảng tổng hợp và biểu đồ trực quan trong chương này được tính toán và kết xuất tự động ngay trong quá trình biên dịch sách (`jupyter-book build .`) từ bộ tệp thống kê đầu ra của Milestone 2 đặt tại `arxiv-book/stats/m2/` (`m2_summary.json`, `m2_papers_stats.csv`, `m2_elements_kind.csv`, `m2_performance.json`).

```{admonition} Phạm vi bộ số liệu Milestone 2: Toàn bộ 25.000 Định danh (41.629 Phiên bản)
:class: note
Bộ phân tích cú pháp Milestone 2 đã hoàn tất xử lý **100% kho ngữ liệu 25.000 bài báo** (**41.629 phiên bản**, `2406.07938` – `2408.16044`) kế thừa từ Milestone 1 với **0 lỗi ngoại lệ (`25.000 / 25.000` bài báo hoàn tất)**. Kết quả kết xuất thành **50 phân mảnh Parquet cho mỗi bảng**, tổng hợp **14.880.359** phần tử nội dung duy nhất (`elements`), **22.516.391** cạnh phân cấp (`hierarchy`) và **1.390.532** mục tài liệu tham khảo chuẩn hóa (`bibtex`).
```

```{code-cell} ipython3
:tags: [remove-input]

from pathlib import Path
import json
import numpy as np
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
    "axes.titlesize": 10.8,
    "axes.titleweight": "bold",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.axisbelow": True,
    "axes.grid": True,
    "grid.color": "#cbd5e1",
    "grid.alpha": 0.45,
})


def _find_stats_dir(subdir: str = "m2", marker: str = "m2_summary.json") -> Path:
    for base in (
        Path("../stats"),
        Path("stats"),
        *[parent / "stats" for parent in Path.cwd().parents],
    ):
        for candidate in (base / subdir, base):
            if candidate.is_dir() and (candidate / marker).is_file():
                return candidate
    return Path(f"../stats/{subdir}")


STATS_DIR = _find_stats_dir("m2", "m2_summary.json")
M1_STATS_DIR = _find_stats_dir("m1", "summary.json")
REQUIRED_M2_STATS = ("m2_summary.json", "m2_papers_stats.csv", "m2_elements_kind.csv")
MISSING_M2_STATS = [
    name for name in REQUIRED_M2_STATS if not (STATS_DIR / name).is_file()
]
HAS_M2_STATS = len(MISSING_M2_STATS) == 0

M1_SUMMARY = {}
if (M1_STATS_DIR / "summary.json").is_file():
    try:
        M1_SUMMARY = json.loads((M1_STATS_DIR / "summary.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        M1_SUMMARY = {}

M2_PERF = {}
if (STATS_DIR / "m2_performance.json").is_file():
    try:
        M2_PERF = json.loads((STATS_DIR / "m2_performance.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        M2_PERF = {}


def pick(mapping: dict, *keys, default=None):
    for key in keys:
        if isinstance(mapping, dict) and key in mapping and mapping[key] is not None:
            return mapping[key]
    return default


def fmt_int(val) -> str:
    return f"{int(round(float(val))):,}" if val is not None else "N/A"


def fmt_float(val, digits: int = 2) -> str:
    return f"{float(val):.{digits}f}" if val is not None else "N/A"


def fmt_pct(val) -> str:
    return f"{float(val) * 100:.2f}%" if val is not None else "N/A"


def show_table(df: pd.DataFrame, *, kv: bool = False) -> None:
    classes = "dataframe jb-stats-table jb-kv-table" if kv else "dataframe jb-stats-table"
    display(HTML(df.to_html(index=False, border=0, classes=classes)))


def show_pending_m2_banner(section_desc: str) -> None:
    missing_html = ", ".join(f"<code>stats/m2/{name}</code>" for name in MISSING_M2_STATS)
    html = (
        '<div class="jb-pending-card">'
        '<div class="jb-pending-title">Đang chờ bộ tệp thống kê Milestone 2 trong <code>arxiv-book/stats/m2/</code></div>'
        f"<div>Hiện chưa tìm thấy: {missing_html}. "
        f"{section_desc} sẽ <strong>tự động sinh đầy đủ</strong> khi bổ sung các tệp thống kê M2 và biên dịch lại sách.</div>"
        "</div>"
    )
    display(HTML(html))
```

## 7.1. Tổng hợp Chỉ số Phân tích Cú pháp, Độ phủ Phiên bản & Lọc Đa tệp `.tex`

```{code-cell} ipython3
:tags: [remove-input]

if HAS_M2_STATS:
    m2_summary = json.loads((STATS_DIR / "m2_summary.json").read_text(encoding="utf-8"))
    m2_papers = pd.read_csv(STATS_DIR / "m2_papers_stats.csv", dtype={"arxivid": str})
    m2_kinds = pd.read_csv(STATS_DIR / "m2_elements_kind.csv")

    err_series = m2_papers["error"] if "error" in m2_papers.columns else pd.Series([""] * len(m2_papers))
    has_err = err_series.notna() & (err_series.astype(str).str.strip() != "")

    n_papers = int(pick(m2_summary, "papers", "papers_total", default=len(m2_papers)))
    n_papers_ok = int(pick(m2_summary, "papers_parsed", "papers_success", default=pick(M2_PERF, "papers_parsed", default=int((~has_err).sum()))))
    n_papers_tex = int((m2_papers["n_versions_with_tex"] > 0).sum())
    n_ver_total = int(pick(m2_summary, "versions", "versions_total", "n_versions_total", default=m2_papers["n_versions"].sum()))
    n_ver_tex = int(pick(m2_summary, "versions_with_tex", "n_versions_with_tex", default=m2_papers["n_versions_with_tex"].sum()))
    n_ver_empty = int(pick(m2_summary, "empty_versions", "versions_empty", "n_versions_empty", default=m2_papers["n_versions_empty"].sum()))

    tot_tex = int(pick(m2_summary, "total_tex_files", default=m2_papers["total_tex_files"].sum()))
    used_tex = int(pick(m2_summary, "used_tex_files", default=m2_papers["used_tex_files"].sum()))
    unused_tex = int(pick(m2_summary, "unused_tex_files", default=m2_papers["unused_tex_files"].sum()))

    nodes_raw = int(pick(m2_summary, "nodes_before_dedup", default=m2_papers["nodes_before_dedup"].sum()))
    elems_dedup = int(pick(m2_summary, "elements", "n_elements", "elements_total", default=m2_papers["n_elements"].sum()))
    hier_edges = int(pick(m2_summary, "hierarchy", "n_hierarchy", "hierarchy_total", default=m2_papers["n_hierarchy"].sum()))
    bib_raw = int(pick(m2_summary, "n_bib_raw", "bib_before_dedup", default=m2_papers["n_bib_raw"].sum()))
    bib_dedup = int(pick(m2_summary, "bibtex", "n_bibtex", "bibtex_total", default=m2_papers["n_bibtex"].sum()))
    shards_per_table = pick(m2_summary, "shards_per_table")

    elem_saved_ratio = 1.0 - (elems_dedup / max(nodes_raw, 1))
    bib_saved_ratio = 1.0 - (bib_dedup / max(bib_raw, 1))
    unused_tex_ratio = unused_tex / max(tot_tex, 1)

    kpi_rows = [
        ("Tổng số bài báo đưa vào bộ phân tích cú pháp (papers)", fmt_int(n_papers)),
        ("Số bài báo phân tích thành công không ngoại lệ (papers_parsed)", f"{fmt_int(n_papers_ok)} ({fmt_pct(n_papers_ok / max(n_papers, 1))})"),
        ("Số bài báo có ít nhất 1 phiên bản sinh cây phân cấp (n_versions_with_tex > 0)", f"{fmt_int(n_papers_tex)} ({fmt_pct(n_papers_tex / max(n_papers, 1))})"),
        ("Tổng số phiên bản đối chiếu độ bao phủ với Milestone 1 (versions)", fmt_int(n_ver_total)),
        ("Số phiên bản có mã nguồn TeX sinh cây phân cấp (n_versions_with_tex)", f"{fmt_int(n_ver_tex)} ({fmt_pct(n_ver_tex / max(n_ver_total, 1))})"),
        ("Số phiên bản rỗng bảo toàn 0 phần tử (empty_versions)", f"{fmt_int(n_ver_empty)} ({fmt_pct(n_ver_empty / max(n_ver_total, 1))})"),
        ("Tổng số tệp .tex quét được trên mọi phiên bản (total_tex_files)", fmt_int(tot_tex)),
        ("Số tệp .tex thuộc đường biên dịch chính từ gốc (used_tex_files)", f"{fmt_int(used_tex)} ({fmt_pct(used_tex / max(tot_tex, 1))})"),
        ("Số tệp .tex dư thừa/nháp đã lọc bỏ (unused_tex_files)", f"{fmt_int(unused_tex)} ({fmt_pct(unused_tex_ratio)})"),
        ("Tổng số nút cây trước khử trùng lặp toàn văn (nodes_before_dedup)", fmt_int(nodes_raw)),
        ("Tổng số dòng bảng elements sau khử trùng lặp xuyên phiên bản (elements)", f"{fmt_int(elems_dedup)} (giảm {fmt_pct(elem_saved_ratio)})"),
        ("Tổng số cạnh quan hệ con -> cha trong bảng hierarchy (hierarchy)", fmt_int(hier_edges)),
        ("Tổng số mục tham chiếu thô từ .bib/.bbl/\\bibitem (n_bib_raw)", fmt_int(bib_raw)),
        ("Tổng số dòng bảng bibtex sau Union-Find & Field Union (bibtex)", f"{fmt_int(bib_dedup)} (giảm {fmt_pct(bib_saved_ratio)})"),
    ]
    if shards_per_table is not None:
        kpi_rows.append(("Số phân mảnh Parquet đầu ra cho mỗi bảng (shards_per_table)", f"{fmt_int(shards_per_table)} shard (3 × {fmt_int(shards_per_table)} tệp)"))
    show_table(pd.DataFrame(kpi_rows, columns=["Chỉ số thống kê phân tích cú pháp (Mục 7.1)", "Giá trị đo đạc"]), kv=True)

    fig, (ax_cov, ax_tex) = plt.subplots(1, 2, figsize=(9.8, 3.45))

    cov_labels = ["Có nguồn TeX hợp lệ\n(sinh cây phân cấp)", "Phiên bản rỗng\n(no_source / 0 nút)"]
    cov_vals = [n_ver_tex, n_ver_empty]
    b_cov = ax_cov.bar(cov_labels, cov_vals, color=["#1971c2", "#94a3b8"], width=0.46)
    ax_cov.set_ylabel("Số lượng phiên bản")
    ax_cov.set_title("Độ bao phủ phiên bản so với Milestone 1")
    top_cov = max(cov_vals + [1])
    for bar, val in zip(b_cov, cov_vals):
        pct = val / max(sum(cov_vals), 1) * 100
        ax_cov.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + top_cov * 0.025,
            f"{val:,}\n({pct:.2f}%)",
            ha="center",
            fontsize=8.5,
            fontweight="bold",
        )
    ax_cov.set_ylim(0, top_cov * 1.28)

    tex_labels = ["Tệp trên đường biên dịch\n(used_tex_files)", "Tệp nháp / rời bị loại\n(unused_tex_files)"]
    tex_vals = [used_tex, unused_tex]
    b_tex = ax_tex.bar(tex_labels, tex_vals, color=["#2b8a3e", "#f59f00"], width=0.46)
    ax_tex.set_ylabel("Số lượng tệp .tex")
    ax_tex.set_title("Hiệu quả lọc đa tệp của gathering.py")
    top_tex = max(tex_vals + [1])
    for bar, val in zip(b_tex, tex_vals):
        pct = val / max(sum(tex_vals), 1) * 100
        ax_tex.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + top_tex * 0.025,
            f"{val:,}\n({pct:.2f}%)",
            ha="center",
            fontsize=8.5,
            fontweight="bold",
        )
    ax_tex.set_ylim(0, top_tex * 1.28)

    plt.tight_layout()
    plt.show()
    plt.close(fig)
else:
    show_pending_m2_banner("Bảng tổng hợp chỉ số phân tích cú pháp & biểu đồ độ phủ tại Mục 7.1")
```

**Phân tích kết quả độ bao phủ và lọc đa tệp trên toàn tập 25.000 bài báo:**

- **Đối soát độ bao phủ 100% với Milestone 1:** Toàn bộ **25.000 / 25.000 bài báo** và **41.629 / 41.629 phiên bản** của Milestone 1 đều đi qua pipeline Milestone 2 với **0 bài báo gặp ngoại lệ (`papers_failed = 0`)**. Trong đó, **23.029 bài báo (92,12%)** có ít nhất một phiên bản sinh cây phân cấp (khớp chính xác con số `papers_with_tex = 23.029` của Milestone 1), còn lại **1.971 bài báo (7,88%)** có toàn bộ phiên bản ở trạng thái rỗng (`0` nút).
- **Giải phẫu 2.894 phiên bản rỗng (`6,95%`):** Có **38.735 phiên bản (93,05%)** sinh cây thành công (khớp từng đơn vị với **38.735** nút gốc `document` trong bảng `elements`). Tập **2.894 phiên bản rỗng** bao gồm **2.892 phiên bản** không có mã nguồn TeX hợp lệ từ Milestone 1 (`2.751 no_source`, `121 not_found`, `15 corrupt`, `5 ok_no_tex`) cộng thêm đúng **2 phiên bản** (`2406.09978` và `2406.12868`, mỗi bài có 1 phiên bản tuy Milestone 1 đánh dấu `ok` nhưng không có tệp gốc `.tex` biên dịch được trong `gathering.py`). Việc bảo toàn đầy đủ các phiên bản rỗng giúp loại bỏ hoàn toàn thiên kiến sống sót (*survivorship bias*).
- **Hiệu quả cô lập tệp dư thừa của `elect_root_tex` & DFS:** Trên tổng số **151.228 tệp `.tex`** được quét, bộ thu thập chỉ đưa **127.057 tệp (84,02%)** thuộc đường biên dịch chính từ gốc vào cây phân cấp và loại bỏ **24.171 tệp `.tex` dư thừa (15,98%)** trên **4.019 bài báo** chứa tệp phụ trợ/nháp (điển hình như bài `2406.11779` gồm 14 phiên bản với `2.245` tệp `.tex`, trong đó `1.462` tệp dư thừa đã được tách lọc sạch).
- **Tổng nén đồ thị & tham chiếu toàn kho:** Khử trùng lặp hai tầng giảm số nút nội dung từ **22.856.948** xuống **14.880.359** dòng trong `elements` (**-34,90%**), và giảm số mục tham chiếu thô từ **3.292.097** xuống **1.390.532** dòng trong `bibtex` (**-57,76%**). Bảng `hierarchy` lưu **22.516.391** cạnh quan hệ (trung bình **1,51 cạnh/phần tử** duy nhất; trong tổng `22.818.213` lần xuất hiện nút khác gốc trước khử trùng, có `301.822` cạnh trùng `(version, elementid, parentid)` đã được gộp thành đồ thị DAG sạch).

---

## 7.2. Phân bố 8 Loại Phần tử (`kind`) & Quy mô Phần tử Cấp Bài báo

```{code-cell} ipython3
:tags: [remove-input]

if HAS_M2_STATS:
    k_col = "kind" if "kind" in m2_kinds.columns else m2_kinds.columns[0]
    c_col = next(
        (c for c in ("count", "n_elements", "after_dedup", "elements") if c in m2_kinds.columns),
        m2_kinds.columns[1],
    )
    kinds_sorted = m2_kinds[[k_col, c_col]].copy()
    kinds_sorted[k_col] = kinds_sorted[k_col].astype(str)
    kinds_sorted[c_col] = kinds_sorted[c_col].astype(int)
    kinds_sorted = kinds_sorted.sort_values(c_col, ascending=False).reset_index(drop=True)

    kind_names = kinds_sorted[k_col].tolist()
    kind_counts = kinds_sorted[c_col].tolist()
    tot_kind = max(sum(kind_counts), 1)

    role_map = {
        "document": "Nút gốc phiên bản (#root<v>)",
        "sentence": "Nút lá nội dung (câu văn xuôi)",
        "block_formula": "Nút lá nội dung (công thức khối)",
        "figure": "Nút lá nội dung (hình, bảng, thuật toán)",
        "paragraph": "Nút cấu trúc trung gian (đoạn văn)",
        "heading": "Nút cấu trúc trung gian (đề mục)",
        "item": "Nút cấu trúc trung gian (mục liệt kê)",
        "list": "Nút cấu trúc trung gian (khối danh sách)",
    }

    kind_table = pd.DataFrame(
        [
            (
                k,
                f"{cnt:,}",
                f"{cnt / tot_kind * 100:.2f}%",
                role_map.get(k, "Nút cấu trúc"),
            )
            for k, cnt in zip(kind_names, kind_counts)
        ],
        columns=["Loại phần tử (kind)", "Số dòng trong elements", "Tỷ trọng (%)", "Vai trò trong đồ thị phân cấp"],
    )
    show_table(kind_table)

    fig, (ax_k, ax_d) = plt.subplots(1, 2, figsize=(10.3, 3.75))

    color_map = {
        "sentence": "#1864ab",
        "paragraph": "#1971c2",
        "block_formula": "#2b8a3e",
        "heading": "#0b7285",
        "item": "#5c940d",
        "figure": "#e67700",
        "list": "#862e9c",
        "document": "#64748b",
    }
    bars_k = ax_k.barh(
        kind_names,
        [c / 1e6 for c in kind_counts],
        color=[color_map.get(k, "#1971c2") for k in kind_names],
    )
    ax_k.invert_yaxis()
    ax_k.set_xlabel("Số lượng phần tử duy nhất (triệu dòng)")
    ax_k.set_title("Phân bố 8 loại nút trong bảng elements")
    max_k = max([c / 1e6 for c in kind_counts] + [0.1])
    for b, cnt in zip(bars_k, kind_counts):
        pct = cnt / tot_kind * 100
        ax_k.text(
            b.get_width() + max_k * 0.018,
            b.get_y() + b.get_height() / 2,
            f"{cnt:,} ({pct:.2f}%)",
            va="center",
            fontsize=8.0,
        )
    ax_k.set_xlim(0, max_k * 1.48)

    elem_tex = m2_papers.loc[m2_papers["n_versions_with_tex"] > 0, "n_elements"]
    p99 = float(np.percentile(elem_tex, 99)) if len(elem_tex) else 3000.0
    clipped = np.clip(elem_tex, 0, p99)
    ax_d.hist(clipped, bins=32, color="#0b7285", edgecolor="#ffffff", alpha=0.92)
    mean_e = float(elem_tex.mean())
    med_e = float(elem_tex.median())
    ax_d.axvline(mean_e, color="#e03131", linestyle="--", linewidth=1.4, label=f"TB: {mean_e:,.1f}")
    ax_d.axvline(med_e, color="#1864ab", linestyle="-.", linewidth=1.4, label=f"Trung vị: {med_e:,.0f}")
    ax_d.legend(loc="upper right", fontsize=8.4)
    ax_d.set_xlabel(f"Số phần tử duy nhất / bài (gộp đuôi >= P99 = {p99:,.0f})")
    ax_d.set_ylabel("Số lượng bài báo có TeX")
    ax_d.set_title("Phân phối quy mô phần tử cấp bài báo (23.029 bài)")

    plt.tight_layout()
    plt.show()
    plt.close(fig)

    q_e = elem_tex.quantile([0.25, 0.5, 0.75, 0.95, 0.99, 1.0])
    q_h = m2_papers.loc[m2_papers["n_versions_with_tex"] > 0, "n_hierarchy"].quantile([0.25, 0.5, 0.75, 0.95, 0.99, 1.0])
    scale_df = pd.DataFrame([
        {
            "Chỉ số cấp bài báo (nhóm 23.029 bài có TeX)": "Số phần tử duy nhất (n_elements)",
            "Trung bình": f"{elem_tex.mean():,.2f}",
            "Q25": f"{q_e[0.25]:,.0f}",
            "Trung vị (Q50)": f"{q_e[0.5]:,.0f}",
            "Q75": f"{q_e[0.75]:,.0f}",
            "P95": f"{q_e[0.95]:,.0f}",
            "P99": f"{q_e[0.99]:,.0f}",
            "Cực đại (Max)": f"{int(q_e[1.0]):,}",
        },
        {
            "Chỉ số cấp bài báo (nhóm 23.029 bài có TeX)": "Số cạnh phân cấp (n_hierarchy)",
            "Trung bình": f"{m2_papers.loc[m2_papers['n_versions_with_tex'] > 0, 'n_hierarchy'].mean():,.2f}",
            "Q25": f"{q_h[0.25]:,.0f}",
            "Trung vị (Q50)": f"{q_h[0.5]:,.0f}",
            "Q75": f"{q_h[0.75]:,.0f}",
            "P95": f"{q_h[0.95]:,.0f}",
            "P99": f"{q_h[0.99]:,.0f}",
            "Cực đại (Max)": f"{int(q_h[1.0]):,}",
        },
    ])
    show_table(scale_df)
else:
    show_pending_m2_banner("Bảng và biểu đồ phân bố 8 loại nút kind tại Mục 7.2")
```

**Nhận xét cấu trúc phân cấp và quy mô nút lá thực nghiệm:**

- **Nút lá câu văn (`sentence`) chiếm 61,45% toàn kho:** Với **9.144.698 câu** tách bằng thuật toán `Protect–Mask–Split–Restore` (theo sau bởi **3.473.190 đoạn văn `paragraph` — 23,34%**), dữ liệu đạt độ mịn chuẩn xác để ở Milestone 3 có thể trích xuất trực tiếp **ngữ cảnh câu chứa `\cite{key}`** làm đặc trưng đối sánh tài liệu tham khảo.
- **Tách bạch triệt để phương trình và hình/bảng:** Toàn kho thu được **997.127 công thức khối (`block_formula` — 6,70%)** và **297.146 khối hình/bảng/thuật toán (`figure` — 2,00%)**, cùng **528.205 đề mục (`heading` — 3,55%)**, **96.617 danh sách (`list` — 0,65%)** với **304.641 mục liệt kê (`item` — 2,05%)**, và đúng **38.735 nút gốc phiên bản (`document` — 0,26%)**.
- **Quy mô phần tử mỗi bài báo:** Trong **23.029 bài báo có mã nguồn TeX**, mỗi bài chứa trung vị **483** phần tử duy nhất (`Q25 = 314`, `Q75 = 763`, trung bình **646,16**) và **601** cạnh phân cấp (`Q25 = 348`, `Q75 = 1.144`, trung bình **977,74**). Nhóm đuôi dài (`P99 = 2.998` phần tử) đạt cực đại **15.439** phần tử duy nhất ở bài `2408.07915` (một chuyên khảo dài 36 tệp `.tex`) và **35.011** cạnh phân cấp ở các bài nhiều phiên bản dài hơi.

---

## 7.3. Hiệu quả Khử trùng lặp Toàn văn Xuyên Phiên bản ($v_1 \dots v_N$)

```{code-cell} ipython3
:tags: [remove-input]

BUCKETS = ["N = 1", "N = 2", "N = 3", "N ≥ 4"]

if HAS_M2_STATS:
    def _bucket(v: int) -> str:
        if v <= 1:
            return "N = 1"
        if v == 2:
            return "N = 2"
        if v == 3:
            return "N = 3"
        return "N ≥ 4"

    m2_papers["v_bucket"] = m2_papers["n_versions"].apply(_bucket)
    all_grp = m2_papers.groupby("v_bucket", observed=False)["arxivid"].count()

    tex_papers = m2_papers[m2_papers["n_versions_with_tex"] > 0].copy()
    grp = tex_papers.groupby("v_bucket", observed=False).agg(
        papers_tex=("arxivid", "count"),
        ver_tex=("n_versions_with_tex", "sum"),
        before=("nodes_before_dedup", "sum"),
        after=("n_elements", "sum"),
        bib_before=("n_bib_raw", "sum"),
        bib_after=("n_bibtex", "sum"),
    )
    b_papers_all = [int(all_grp.get(b, 0)) for b in BUCKETS]
    b_papers = [int(grp.loc[b, "papers_tex"]) if b in grp.index else 0 for b in BUCKETS]
    b_ver_tex = [int(grp.loc[b, "ver_tex"]) if b in grp.index else 0 for b in BUCKETS]
    b_before = [int(grp.loc[b, "before"]) if b in grp.index else 0 for b in BUCKETS]
    b_after = [int(grp.loc[b, "after"]) if b in grp.index else 0 for b in BUCKETS]
    bib_b_before = [int(grp.loc[b, "bib_before"]) if b in grp.index else 0 for b in BUCKETS]
    bib_b_after = [int(grp.loc[b, "bib_after"]) if b in grp.index else 0 for b in BUCKETS]

    b_saved_pct = [(1.0 - a / max(bf, 1)) * 100.0 for bf, a in zip(b_before, b_after)]
    dedup_df = pd.DataFrame(
        [
            (
                b,
                f"{p:,} / {p_all:,}",
                f"{vt:,}",
                f"{bf:,}",
                f"{af:,}",
                f"{sv:.2f}%",
            )
            for b, p, p_all, vt, bf, af, sv in zip(
                BUCKETS, b_papers, b_papers_all, b_ver_tex, b_before, b_after, b_saved_pct
            )
        ],
        columns=[
            "Nhóm số phiên bản",
            "Số bài có TeX / Tổng bài",
            "Số phiên bản có TeX",
            "Nút cây trước khử trùng (nodes_before_dedup)",
            "Dòng elements sau khử trùng (n_elements)",
            "Tỷ lệ giảm dòng lưu trữ (%)",
        ],
    )
    show_table(dedup_df)

    x = np.arange(len(BUCKETS))
    width = 0.34
    fig, ax1 = plt.subplots(figsize=(9.4, 3.85))
    ax1.bar(x - width / 2, [v / 1e6 for v in b_before], width, label="Trước khử trùng (nodes_before_dedup)", color="#94a3b8")
    ax1.bar(x + width / 2, [v / 1e6 for v in b_after], width, label="Sau khử trùng (bảng elements)", color="#1971c2")
    ax1.set_xticks(x)
    ax1.set_xticklabels(BUCKETS)
    ax1.set_ylabel("Số lượng nút / dòng (triệu)")
    ax1.set_title("So sánh quy mô phần tử Trước vs. Sau khử trùng lặp theo số phiên bản")
    ax1.set_ylim(0, max([v / 1e6 for v in b_before] + [0.1]) * 1.30)

    ax2 = ax1.twinx()
    ax2.spines["top"].set_visible(False)
    ax2.grid(False)
    ax2.plot(x, b_saved_pct, color="#2b8a3e", marker="o", linewidth=2.2, label="Tỷ lệ giảm dòng elements (%)")
    ax2.set_ylabel("Tỷ lệ giảm số dòng (%)", color="#2b8a3e")
    ax2.tick_params(axis="y", colors="#2b8a3e")
    ax2.set_ylim(0, 96)
    for xi, sv in zip(x, b_saved_pct):
        ax2.text(xi, sv + 3.2, f"-{sv:.1f}%", ha="center", color="#2b8a3e", fontweight="bold", fontsize=8.8)

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(
        lines1 + lines2,
        labels1 + labels2,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.14),
        ncol=3,
        frameon=True,
        fontsize=8.3,
    )

    plt.tight_layout()
    plt.show()
    plt.close(fig)
else:
    show_pending_m2_banner("Bảng phân tầng và biểu đồ Trước vs. Sau khử trùng lặp theo số phiên bản N tại Mục 7.3")
```

**Phân tích động học khử trùng lặp theo lịch sử sửa đổi ($N = 1 \dots \ge 4$):**

- **Nhóm bài chỉ có một phiên bản ($N = 1$, `12.616` bài có TeX):** Ngay cả khi chỉ tồn tại một bản nộp duy nhất, số nút giảm nhẹ **3,09%** (từ `6.343.860` xuống `6.147.674` dòng) nhờ hợp nhất các đề mục chuẩn lặp tên, câu ghi chú bảng biểu hoặc thông báo bản quyền giống hệt nhau trong cùng bài báo (còn lại `1.540` bài $N=1$ không có mã nguồn TeX nên đóng góp `0` nút).
- **Bước nhảy nén theo số vòng chỉnh sửa ($N = 2, 3, \ge 4$):** Tỷ lệ loại bỏ phần tử trùng lặp tăng mạnh theo lịch sử phiên bản: đạt **37,91%** ở nhóm $N = 2$ (`6.774` bài có TeX; `7.949.649` $\rightarrow$ `4.935.580`), lên **51,35%** ở nhóm $N = 3$ (`2.497` bài; `4.938.215` $\rightarrow$ `2.402.331`) và đạt **61,53%** ở nhóm $N \ge 4$ (`1.142` bài; `3.625.224` $\rightarrow$ `1.394.774`). Kết quả này khẳng định hiệu quả của **Thứ tự Vàng**: đồng bộ khóa `\cite{...}` trước khi băm toàn văn giúp các câu chứa trích dẫn vẫn khớp chính xác 100% giữa các bản thảo $v_1 \dots v_N$.

---

## 7.4. Khử trùng lặp Tài liệu Tham khảo & Độ lấp đầy Trường nhờ `Field Union`

```{code-cell} ipython3
:tags: [remove-input]

BIB_FIELDS = ["title", "authors", "year", "journal", "url", "doi"]

if HAS_M2_STATS:
    tot_bib_before = max(int(m2_papers["bibtex_before"].sum()), 1)
    tot_bib_after = max(int(m2_papers["bibtex_after"].sum()), 1)

    has_bib_papers = m2_papers[m2_papers["bibtex_after"] > 0].copy()
    field_rows = []
    fc_before = []
    fc_after = []

    for f in BIB_FIELDS:
        b_cnt = int(m2_papers[f"{f}_before"].sum())
        a_cnt = int(m2_papers[f"{f}_after"].sum())
        r_b = b_cnt / tot_bib_before * 100.0
        r_a = a_cnt / tot_bib_after * 100.0
        fc_before.append(r_b)
        fc_after.append(r_a)

        per_b = has_bib_papers[f"{f}_before"] / has_bib_papers["bibtex_before"]
        per_a = has_bib_papers[f"{f}_after"] / has_bib_papers["bibtex_after"]
        improved_cnt = int((per_a > per_b + 1e-9).sum())

        field_rows.append(
            (
                f,
                f"{b_cnt:,} ({r_b:.2f}%)",
                f"{a_cnt:,} ({r_a:.2f}%)",
                f"{r_a - r_b:+.2f} điểm %",
                f"{per_b.mean() * 100:.2f}% → {per_a.mean() * 100:.2f}%",
                f"{improved_cnt:,} bài",
            )
        )

    show_table(
        pd.DataFrame(
            field_rows,
            columns=[
                "Trường BibTeX",
                "Trước Field Union (trên 3.292.097 mục)",
                "Sau Field Union (trên 1.390.532 mục)",
                "Chênh lệch toàn kho",
                "TB theo bài (Macro: Trước → Sau)",
                "Số bài tăng độ phủ",
            ],
        )
    )

    fig, (ax_b1, ax_b2) = plt.subplots(1, 2, figsize=(10.3, 3.75))

    xb = np.arange(len(BUCKETS))
    bars_bib_b = ax_b1.bar(xb - 0.17, [v / 1e3 for v in bib_b_before], 0.34, label="Mục thô (n_bib_raw)", color="#fcc419")
    bars_bib_a = ax_b1.bar(xb + 0.17, [v / 1e3 for v in bib_b_after], 0.34, label="Sau Union-Find (n_bibtex)", color="#0b7285")
    ax_b1.set_xticks(xb)
    ax_b1.set_xticklabels(BUCKETS)
    ax_b1.set_ylabel("Số mục tham khảo (nghìn)")
    ax_b1.set_title("Gộp trùng tham chiếu theo nhóm phiên bản")
    top_bib = max([v / 1e3 for v in bib_b_before] + [1.0])
    ax_b1.set_ylim(0, top_bib * 1.24)
    for bar, bf, af in zip(bars_bib_a, bib_b_before, bib_b_after):
        pct_saved = (1.0 - af / max(bf, 1)) * 100.0
        ax_b1.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + top_bib * 0.025,
            f"-{pct_saved:.1f}%",
            ha="center",
            fontsize=8.2,
            fontweight="bold",
            color="#0b7285",
        )
    ax_b1.legend(loc="upper right", fontsize=8.3)

    yf = np.arange(len(BIB_FIELDS))
    ax_b2.barh(yf - 0.17, fc_before, 0.33, label="Trước Field Union", color="#cbd5e1")
    ax_b2.barh(yf + 0.17, fc_after, 0.33, label="Sau Field Union", color="#2b8a3e")
    ax_b2.set_yticks(yf)
    ax_b2.set_yticklabels(BIB_FIELDS)
    ax_b2.invert_yaxis()
    ax_b2.set_xlabel("Tỷ lệ mục có dữ liệu hợp lệ (%)")
    ax_b2.set_xlim(0, 122)
    ax_b2.set_title("Độ lấp đầy trường BibTeX Trước vs. Sau Field Union")
    for idx, (vb, va) in enumerate(zip(fc_before, fc_after)):
        ax_b2.text(vb + 1.2, idx - 0.17, f"{vb:.1f}%", va="center", fontsize=7.6, color="#475569")
        ax_b2.text(va + 1.2, idx + 0.17, f"{va:.1f}%", va="center", fontsize=8.0, fontweight="bold", color="#1e293b")
    ax_b2.legend(loc="lower right", fontsize=8.2)

    plt.tight_layout()
    plt.show()
    plt.close(fig)

    q_bib = has_bib_papers["n_bibtex"].quantile([0.25, 0.5, 0.75, 0.95, 0.99, 1.0])
    bib_quant_df = pd.DataFrame([
        {
            "Tập bài báo có trích xuất BibTeX": f"{len(has_bib_papers):,} / {len(m2_papers):,} bài (89,48%)",
            "Trung bình / bài": f"{has_bib_papers['n_bibtex'].mean():,.2f}",
            "Q25": f"{q_bib[0.25]:,.0f}",
            "Trung vị (Q50)": f"{q_bib[0.5]:,.0f}",
            "Q75": f"{q_bib[0.75]:,.0f}",
            "P95": f"{q_bib[0.95]:,.0f}",
            "P99": f"{q_bib[0.99]:,.0f}",
            "Cực đại (Max)": f"{int(q_bib[1.0]):,}",
        }
    ])
    show_table(bib_quant_df)
else:
    show_pending_m2_banner("Biểu đồ gộp cụm tham chiếu BibTeX và tỷ lệ lấp đầy trường nhờ Field Union tại Mục 7.4")
```

**Đánh giá định lượng hiệu quả khử trùng lặp và `Field Union` cho Milestone 3:**

- **Nén 57,76% kho tài liệu tham khảo (`3.292.097` $\rightarrow$ `1.390.532` mục):** Ngay ở nhóm bài chỉ có một phiên bản ($N = 1$), tỷ lệ gộp trùng đã đạt **-35,43%** (`1.011.375` $\rightarrow$ `653.039`) do nhiều bài báo đính kèm đồng thời tệp `.bib` gốc lẫn tệp `.bbl` đã biên dịch (hoặc khối `\begin{thebibliography}`). Ở nhóm đa phiên bản, tỷ lệ gộp trùng tăng dần lên **-59,06%** ($N = 2$: `1.206.850` $\rightarrow$ `494.123`), **-74,69%** ($N = 3$: `640.749` $\rightarrow$ `162.187`) và **-81,26%** ($N \ge 4$: `433.123` $\rightarrow$ `81.183`).
- **Tăng vọt độ lấp đầy các trường định danh thưa nhờ `Field Union`:** Khi hợp nhất các trường khuyết từ nhiều nguồn/phiên bản trong cùng cụm tương đương, tỷ lệ bản ghi có `journal` tăng mạnh **+11,93 điểm phần trăm** (`65,84%` $\rightarrow$ `77,77%`, cải thiện trên **13.368 bài báo**), trường `url` (bao gồm cả URL `https://arxiv.org/abs/<id>` được tổng hợp tự động) tăng **+10,62 điểm phần trăm** (`37,95%` $\rightarrow$ `48,57%`, cải thiện trên **14.139 bài báo**), và trường `doi` tăng **+4,11 điểm phần trăm** (`29,96%` $\rightarrow$ `34,06%`, cải thiện trên **7.686 bài báo**). Các trường nòng cốt giữ mức phủ gần tuyệt đối (`title` `99,55%`, `authors` `98,79%`, `year` `98,54%`); xét trung bình trên từng bài báo (*macro-average*), **cả 6/6 trường** đều cải thiện sau `Field Union` (dao động vi mô `-0,05` và `-0,22` điểm phần trăm trên tổng toàn kho ở `title` và `authors` chỉ phản ánh việc mẫu số của các bó `.bib` đầy đủ bị nén mạnh hơn so với các mục đơn lẻ).
- **Quy mô danh mục tham khảo cấp bài báo & hiện tượng đuôi cực nặng:** Trong **22.369 bài báo** trích xuất được tài liệu tham khảo (còn **660** bài có TeX không chứa khối tham chiếu và **1.971** bài không có TeX), số mục `bibtex` trung vị là **44 mục/bài** (`Q25 = 29`, `Q75 = 66`, `P95 = 119`). Cá biệt tồn tại hai bài ngoại lai là `2408.01285` (**102.109** mục sau dedup từ `104.336` mục thô) và `2408.09430` (**90.079** mục sau dedup từ `92.168` mục thô) do tác giả đính kèm toàn bộ kho cơ sở dữ liệu `.bib` cá nhân/nhóm nghiên cứu vào gói nguồn arXiv dù chỉ trích dẫn thực tế vài chục bài. Hai trường hợp cực trị này chiếm `13,82%` tổng số dòng bảng `bibtex` toàn kho và là tâm điểm phân tích độ trễ $\mathcal{O}(R^2)$ tại Chương 8.
