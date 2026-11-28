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

# Chương 11. Thống kê Gán nhãn, Kiểm toán & Phân tích Đặc trưng

Toàn bộ bảng tổng hợp và biểu đồ phân tích trong chương này được tính toán và kết xuất tự động ngay trong quá trình biên dịch sách (`jupyter-book build .`) từ bộ tệp thống kê đầu ra của Milestone 3 tại `arxiv-book/stats/m3/` (`m3_summary.json`, `m3_evaluation.json`, `m3_papers_stats.csv`).

```{admonition} Phạm vi bộ số liệu Milestone 3: Dải range_0 (2408.11045 – 2408.16044 · 5.000 ID)
:class: note
Pipeline đối sánh tham chiếu (`src/run_matching.py --range-index 0`) đã chạy hoàn chỉnh trên dữ liệu thực tế của lát cắt **`range_0`** (**5.000** định danh được giao: `2408.11045`–`2408.16044`, phần phụ trách công bố Hugging Face của thành viên **A — Võ Gia Phúc**). Kết quả thực nghiệm Milestone 3 trên sách minh họa trực tiếp phân vùng `range_0` (5.000 ID) đã đóng băng cho đợt nộp bộ dữ liệu Hugging Face cá nhân, trong khi tổng hợp liên dải trên cả 5 thành viên (`range_0..range_4`, 25.000 ID) được trình bày trên Poster A2 chung của nhóm. Trên `4.247` bài báo có danh mục BibTeX, hệ thống đã gán nhãn và đối sánh đầy đủ cho **`515` bài báo** (`5` bài thủ công + `510` bài tự động), tạo ra **`26.959` dòng dự đoán** (`predictions.parquet`) từ **`519.700` cặp vector 21 đặc trưng**.
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
    "axes.titlesize": 10.6,
    "axes.titleweight": "bold",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.axisbelow": True,
    "axes.grid": True,
    "grid.color": "#cbd5e1",
    "grid.alpha": 0.45,
})


def _find_stats_dir(subdir: str = "m3", marker: str = "m3_summary.json") -> Path:
    for base in (
        Path("../stats"),
        Path("stats"),
        *[parent / "stats" for parent in Path.cwd().parents],
    ):
        for candidate in (base / subdir, base):
            if candidate.is_dir() and (candidate / marker).is_file():
                return candidate
    return Path(f"../stats/{subdir}")


STATS_DIR = _find_stats_dir("m3", "m3_summary.json")
REQUIRED_M3_STATS = ("m3_summary.json", "m3_evaluation.json", "m3_papers_stats.csv")
MISSING_M3_STATS = [name for name in REQUIRED_M3_STATS if not (STATS_DIR / name).is_file()]
HAS_M3_STATS = len(MISSING_M3_STATS) == 0


def fmt_int(val) -> str:
    return f"{int(round(float(val))):,}" if val is not None else "N/A"


def fmt_float(val, digits: int = 2) -> str:
    return f"{float(val):.{digits}f}" if val is not None else "N/A"


def fmt_pct(val) -> str:
    return f"{float(val) * 100:.2f}%" if val is not None else "N/A"


def show_table(df: pd.DataFrame, *, kv: bool = False) -> None:
    classes = "dataframe jb-stats-table jb-kv-table" if kv else "dataframe jb-stats-table"
    display(HTML(df.to_html(index=False, border=0, classes=classes)))


def show_pending_m3_banner(section_desc: str) -> None:
    missing_html = ", ".join(f"<code>stats/m3/{name}</code>" for name in MISSING_M3_STATS)
    html = (
        '<div class="jb-pending-card">'
        '<div class="jb-pending-title">Đang chờ bộ tệp thống kê Milestone 3 trong <code>arxiv-book/stats/m3/</code></div>'
        f"<div>Hiện chưa tìm thấy: {missing_html}. "
        f"{section_desc} sẽ <strong>tự động sinh đầy đủ</strong> khi bổ sung các tệp thống kê M3 và biên dịch lại sách.</div>"
        "</div>"
    )
    display(HTML(html))
```

## 11.1. Tổng hợp Quy mô Không gian Đối sánh & Độ bao phủ Gán nhãn

```{code-cell} ipython3
:tags: [remove-input]

if HAS_M3_STATS:
    m3_sum = json.loads((STATS_DIR / "m3_summary.json").read_text(encoding="utf-8"))
    m3_eval = json.loads((STATS_DIR / "m3_evaluation.json").read_text(encoding="utf-8"))
    m3_papers = pd.read_csv(STATS_DIR / "m3_papers_stats.csv", dtype={"arxivid": str})

    n_ids = int(m3_sum["n_ids_assigned"])
    n_m1_ok = int(m3_sum["n_papers_m1_success"])
    n_tex = int(m3_sum["n_papers_with_tex"])
    n_bib_p = int(m3_sum["n_papers_in_range"])
    n_lbl_p = int(m3_sum["n_papers_labeled_total"])
    n_man_p = int(m3_sum["n_papers_manual"])
    n_auto_p = int(m3_sum["n_papers_auto"])
    n_preds = int(m3_sum["n_predictions"])
    n_pos = int(m3_sum["n_predictions_positive"])
    n_neg = int(m3_sum["n_predictions_negative"])
    n_feats = int(m3_sum["n_features"])

    kpi_rows = [
        ("Dải dữ liệu xử lý & Thành viên phụ trách", f"{m3_sum['range']} · {m3_sum['member']}"),
        ("Số ID arXiv được giao trong dải (n_ids_assigned)", fmt_int(n_ids)),
        ("Số bài báo hoàn tất thu thập M1 / có TeX (n_papers_m1_success / with_tex)", f"{fmt_int(n_m1_ok)} ({fmt_pct(n_m1_ok / n_ids)}) / {fmt_int(n_tex)} ({fmt_pct(n_tex / n_ids)})"),
        ("Số bài báo có mục BibTeX đủ điều kiện đối sánh (n_papers_in_range)", f"{fmt_int(n_bib_p)} ({fmt_pct(n_bib_p / n_ids)})"),
        ("Tổng tham khảo S2 / Tham khảo có arXiv ID trong dải", f"{fmt_int(m3_sum['n_references_total_in_range'])} / {fmt_int(m3_sum['n_references_with_arxiv_id'])} ({fmt_pct(m3_sum['n_references_with_arxiv_id'] / max(m3_sum['n_references_total_in_range'], 1))})"),
        ("Tổng mục BibTeX chuẩn hóa M2 trong dải (n_bibtex_in_range)", fmt_int(m3_sum["n_bibtex_in_range"])),
        ("Số bài báo gán nhãn thủ công (Manual Gold)", f"{fmt_int(n_man_p)} bài ({fmt_int(m3_sum['n_queries_manual'])} truy vấn · {fmt_int(m3_sum['n_qualified_eval_manual'])}/5 bài đạt chuẩn eval)"),
        ("Số bài báo gán nhãn tự động (Auto Silver)", f"{fmt_int(n_auto_p)} bài ({fmt_int(m3_sum['n_queries_auto'])} truy vấn)"),
        ("Độ phủ Auto-Matcher trên tập đủ điều kiện có BibTeX (4.242 bài)", fmt_pct(m3_sum["eligible_coverage"])),
        ("Độ phủ Auto-Matcher trên tổng số bài còn lại của dải (4.995 ID)", f"{fmt_pct(m3_sum['assigned_coverage'])} (đạt chuẩn >= 10,00% với --auto-fraction 0.12)"),
        ("Tổng số bài báo & dòng trong bảng predictions", f"{fmt_int(n_lbl_p)} bài · {fmt_int(n_preds)} truy vấn"),
        ("Tỷ trọng nhãn dương (matchable) vs. toàn âm (negative-only)", f"{fmt_int(n_pos)} dương ({fmt_pct(n_pos / n_preds)}) / {fmt_int(n_neg)} âm ({fmt_pct(n_neg / n_preds)})"),
        ("Tổng số cặp ứng viên đã trích 21 đặc trưng sau Blocking (n_features)", f"{fmt_int(n_feats)} cặp (TB {n_feats / max(n_preds, 1):.2f} ứng viên / truy vấn)"),
        ("Số dòng & nhóm truy vấn đưa vào huấn luyện LambdaMART (positive_only)", f"{fmt_int(m3_sum['train_rows'])} dòng / {fmt_int(m3_sum['train_groups'])} nhóm truy vấn"),
        ("Kết quả kiểm toán Auto-Matcher trên 114 truy vấn Manual Gold", f"Precision = {fmt_pct(m3_sum['audit_auto_matcher']['precision'])} · Recall = {fmt_pct(m3_sum['audit_auto_matcher']['recall'])} · F1 = {fmt_pct(m3_sum['audit_auto_matcher']['f1'])}"),
    ]
    show_table(pd.DataFrame(kpi_rows, columns=["Chỉ số thống kê đầu vào & gán nhãn Milestone 3 (Mục 11.1)", "Giá trị đo đạc trên range_0"]), kv=True)

    fig, (ax_f, ax_cov) = plt.subplots(1, 2, figsize=(10.3, 3.65))

    funnel_labels = [
        "ID được giao\n(range_0)",
        "M1 thu thập\nthành công",
        "Có mã nguồn\nTeX (M2)",
        "Có BibTeX\n(đủ ĐK M3)",
        "Đưa vào tập\nđối sánh M3",
    ]
    funnel_vals = [n_ids, n_m1_ok, n_tex, n_bib_p, n_lbl_p]
    funnel_colors = ["#64748b", "#339af0", "#1971c2", "#0b7285", "#2b8a3e"]
    bars_f = ax_f.barh(funnel_labels, funnel_vals, color=funnel_colors, height=0.56)
    ax_f.invert_yaxis()
    ax_f.set_xlabel("Số lượng bài báo (arXiv ID)")
    ax_f.set_title("Phễu thu hẹp dữ liệu từ M1 đến M3 (range_0)")
    max_fv = max(funnel_vals + [1])
    for b, v in zip(bars_f, funnel_vals):
        ax_f.text(
            b.get_width() + max_fv * 0.02,
            b.get_y() + b.get_height() / 2,
            f"{v:,} ({v / n_ids * 100:.2f}%)",
            va="center",
            fontsize=8.2,
            fontweight="bold",
        )
    ax_f.set_xlim(0, max_fv * 1.42)

    cov_labels = [
        f"Trên toàn bộ ID\ncòn lại ({int(m3_sum['n_assigned_nonmanual']):,} ID)",
        f"Trên bài có BibTeX\n({int(m3_sum['n_eligible_nonmanual']):,} bài)",
    ]
    cov_vals = [
        m3_sum["assigned_coverage"] * 100.0,
        m3_sum["eligible_coverage"] * 100.0,
    ]
    bars_c = ax_cov.bar(cov_labels, cov_vals, color=["#1971c2", "#2b8a3e"], width=0.45)
    ax_cov.axhline(10.0, color="#e03131", linestyle="--", linewidth=1.5, label="Ngưỡng tối thiểu đề bài (10,00%)")
    ax_cov.set_ylabel("Tỷ lệ bao phủ Auto-Matcher (%)")
    ax_cov.set_title("Độ bao phủ gán nhãn tự động (510 bài)")
    ax_cov.set_ylim(0, max(cov_vals + [12.0]) * 1.28)
    for b, v in zip(bars_c, cov_vals):
        ax_cov.text(
            b.get_x() + b.get_width() / 2,
            b.get_height() + 0.35,
            f"{v:.2f}%",
            ha="center",
            fontsize=9.0,
            fontweight="bold",
        )
    ax_cov.legend(loc="upper left", fontsize=8.2)

    plt.tight_layout()
    plt.show()
    plt.close(fig)
else:
    show_pending_m3_banner("Bảng tổng hợp 15 chỉ số gán nhãn và phễu bao phủ Milestone 3 tại Mục 11.1")
```

**Nhận xét quy mô dữ liệu và độ phủ trên dải `range_0`:**

- **Độ phủ bài có BibTeX đạt `84,94%` dải 5.000 ID (bản đóng băng Hugging Face `hf_range_0`):** Từ `5.000` định danh (`2408.11045`–`2408.16044`), có `4.979` bài thu thập thành công từ M1 (`99,58%`) và `4.580` bài có mã nguồn TeX (`91,60%` — khớp từng bài với bản thu thập `v3.18` ở Chương 3); trên bản snapshot đóng băng để xuất bản bộ dữ liệu Hugging Face cá nhân `hf_range_0`, có **`4.247` bài (`84,94%`)** trích xuất được bảng `bibtex` (`229.161` mục trích dẫn và `104.529` tham khảo có `arXiv ID` trong bảng `references`). Phần chênh lệch `753` bài không tham gia đối sánh đến từ các bài chỉ nộp PDF (`no_source`) hoặc không có danh mục tài liệu tham khảo.
- **Tỷ lệ lấy mẫu `--auto-fraction 0.12` bảo đảm đạt chuẩn kép $\ge 10\%$:** Do chỉ có `4.242` bài ngoài tập thủ công sở hữu BibTeX, nếu đặt `--auto-fraction 0.10` trên tập đủ điều kiện thì số lượng bài chỉ đạt `425 / 4.995 = 8,51%` trên tổng dải được giao. Nhờ tăng tham số lên `0.12`, hệ thống thu được **`510` bài tự động**, thỏa mãn đồng thời **12,02%** trên tập bài có BibTeX và **10,21%** trên toàn bộ `4.995` ID còn lại của dải.
- **Hiệu quả cô đọng của Stage-1 Blocking:** Tổng số ứng viên sau blocking là **`519.700` cặp** trên `26.959` truy vấn (trung bình **`19,28` ứng viên/truy vấn**), giữ bộ dữ liệu đặc trưng đủ gọn nhẹ để hoàn tất trích xuất và huấn luyện trên CPU chỉ trong vài phút.

---

## 11.2. Giải phẫu Tập Nhãn Thủ công & Kiểm toán Bộ Đối sánh Tự động

```{code-cell} ipython3
:tags: [remove-input]

if HAS_M3_STATS:
    manual_df = m3_papers[m3_papers["source"] == "manual"].copy().sort_values("arxivid")
    man_table_rows = []
    for _, r in manual_df.iterrows():
        tp = int(r["audit_tp"])
        fp = int(r["audit_fp"])
        fn = int(r["audit_fn"])
        tn = int(r["audit_tn"])
        prec = tp / (tp + fp) * 100.0 if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) * 100.0 if (tp + fn) > 0 else 0.0
        man_table_rows.append({
            "arXiv ID": str(r["arxivid"]),
            "Phân vùng": str(r["partition"]),
            "Tổng mục BibTeX": int(r["n_queries"]),
            "Nhãn Dương": int(r["n_positive"]),
            "Nhãn Âm": int(r["n_negative"]),
            "Ứng viên S2 arXiv": int(r["n_candidates_pool"]),
            "Audit TP / FP / FN / TN": f"{tp} / {fp} / {fn} / {tn}",
            "Precision / Recall": f"{prec:.1f}% / {rec:.1f}%",
        })
    show_table(pd.DataFrame(man_table_rows))

    fig, (ax_m, ax_a) = plt.subplots(1, 2, figsize=(10.3, 3.65))

    x_m = np.arange(len(manual_df))
    m_ids = manual_df["arxivid"].tolist()
    m_pos = manual_df["n_positive"].to_numpy()
    m_neg = manual_df["n_negative"].to_numpy()
    ax_m.bar(x_m, m_pos, width=0.52, label="Dương (có arXiv ID)", color="#1971c2")
    ax_m.bar(x_m, m_neg, bottom=m_pos, width=0.52, label="Âm (ngoài arXiv)", color="#cbd5e1")
    ax_m.axhline(20, color="#2b8a3e", linestyle="--", linewidth=1.3, label="Ngưỡng tối thiểu (>= 20 mục)")
    ax_m.set_xticks(x_m)
    ax_m.set_xticklabels(
        [f"{pid}\n({part})" for pid, part in zip(m_ids, manual_df["partition"])],
        fontsize=8.0,
    )
    ax_m.set_ylabel("Số mục BibTeX đã gán nhãn")
    ax_m.set_title(f"Phân bố nhãn trên {len(manual_df)} bài Manual Gold ({int((m_pos + m_neg).sum()):,} mục)")
    ax_m.set_ylim(0, max(m_pos + m_neg) * 1.24)
    for xi, p, n in zip(x_m, m_pos, m_neg):
        ax_m.text(xi, p / 2, f"{p}", ha="center", va="center", color="white", fontweight="bold", fontsize=8.4)
        ax_m.text(xi, p + n / 2, f"{n}", ha="center", va="center", color="#334155", fontweight="bold", fontsize=8.2)
        ax_m.text(xi, p + n + 0.6, f"Q={p+n}", ha="center", fontsize=8.0, fontweight="bold")
    ax_m.legend(loc="upper center", bbox_to_anchor=(0.5, -0.20), ncol=2, fontsize=7.6)

    aud = m3_sum["audit_auto_matcher"]
    a_labels = ["Precision\n(Độ chính xác)", "Recall\n(Độ phủ)", "F1-Score\n(Tổng hợp)"]
    a_vals = [aud["precision"] * 100.0, aud["recall"] * 100.0, aud["f1"] * 100.0]
    bars_a = ax_a.bar(a_labels, a_vals, color=["#2b8a3e", "#1971c2", "#0b7285"], width=0.45)
    ax_a.set_ylim(0, 122)
    ax_a.set_ylabel("Tỷ lệ (%)")
    ax_a.set_title(
        f"Kiểm toán Auto-Matcher trên 114 truy vấn Gold\n(TP={int(aud['tp'])}, FP={int(aud['fp'])}, FN={int(aud['fn'])}, TN={int(aud['tn'])})"
    )
    for b, v in zip(bars_a, a_vals):
        ax_a.text(
            b.get_x() + b.get_width() / 2,
            b.get_height() + 2.5,
            f"{v:.2f}%",
            ha="center",
            fontsize=8.8,
            fontweight="bold",
        )

    plt.tight_layout()
    plt.show()
    plt.close(fig)
else:
    show_pending_m3_banner("Bảng chi tiết 5 bài Manual Gold và biểu đồ kiểm toán Auto-Matcher tại Mục 11.2")
```

**Phân tích kết quả kiểm toán chất lượng nhãn (`audit_auto_matcher`):**

- **Toàn bộ 5/5 bài Manual Gold đều đạt chuẩn kép (`n_qualified_eval_manual = 5`):** Năm bài báo `2408.11069` (`23` mục), `2408.11078` (`22` mục), `2408.11192` (`25` mục), `2408.11203` (`24` mục) và `2408.11247` (`20` mục) có tổng cộng **`114` mục BibTeX** (`43` nhãn dương arXiv, `71` nhãn âm). Tất cả `5/5` bài đều sở hữu tối thiểu `8` nhãn dương và `11` nhãn âm, vượt xa ngưỡng bắt buộc `>= 3` dương và `>= 3` âm cho phân vùng `valid`/`test`.
- **Precision đạt tuyệt đối `100,00%` (`0` dương giả trên 114 truy vấn):** Khi kiểm toán đối chứng trên toàn bộ `114` truy vấn thủ công, `auto_matcher` khớp chính xác **`28 / 28`** dự đoán dương (**FP = 0**) trên tổng số **43** liên kết dương thật (**FN = 15**, Recall **65,12%**) và giữ đúng **`71 / 71`** nhãn âm (**TN = 71**). Điều này xác nhận chính sách ngưỡng bảo thủ ở Tầng 1–3 đã loại bỏ hoàn toàn nguy cơ đầu độc tập huấn luyện bằng nhãn dương sai.
- **Giải phẫu `15` trường hợp bỏ sót (`FN = 15`, Recall = `65,12%`):** Các ca bỏ sót tập trung hoàn toàn ở hai bài Vật lý – Toán lý `2408.11078` (`6` FN) và `2408.11192` (`9` FN), xuất phát từ hai nguyên nhân thực tế của dữ liệu `\bibitem`: *(i)* bài `2408.11078` dùng chuẩn trích dẫn Vật lý rút gọn chỉ ghi số tạp chí (`"Phys. Rev. D 104, 123517 (2021)"`) mà không kèm tên bài báo, khiến bộ lọc heuristic tiêu đề chủ động từ chối đoán; *(ii)* một số mục `\bibitem` văn bản tự do trong `2408.11192` gộp tên đồng tác giả và tiêu đề vào cùng chuỗi `authors` khi tách dấu phẩy, làm sai lệch `first_surname`. Nhờ `sample_weight = 3,0` cho nhãn Manual và dừng sớm trên `Valid-Manual` (chứa chính bài `2408.11078`), mô hình học máy có cơ hội học vượt qua giới hạn của bộ heuristic.

---

## 11.3. Phân chia Tập Dữ liệu Cấp Bài báo & Phân phối Truy vấn

```{code-cell} ipython3
:tags: [remove-input]

if HAS_M3_STATS:
    sb = m3_sum["splits_breakdown"]
    split_rows = []
    for part in ("train", "valid", "test"):
        for src_key, src_lbl in (("manual", "Thủ công (Manual)"), ("auto", "Tự động (Auto)"), ("overall", "Tổng phân vùng")):
            d = sb[part][src_key]
            q_cnt = d["queries"]
            pos_cnt = d["positive_queries"]
            neg_cnt = d["negative_only_queries"]
            split_rows.append({
                "Phân vùng (partition)": part,
                "Nguồn nhãn": src_lbl,
                "Số bài báo": f"{d['papers']:,}",
                "Tổng truy vấn": f"{q_cnt:,}",
                "Truy vấn dương (matchable)": f"{pos_cnt:,} ({pos_cnt / max(q_cnt, 1) * 100:.1f}%)",
                "Truy vấn toàn âm (null)": f"{neg_cnt:,} ({neg_cnt / max(q_cnt, 1) * 100:.1f}%)",
            })
    show_table(pd.DataFrame(split_rows))

    fig, (ax_q, ax_sp) = plt.subplots(1, 2, figsize=(10.3, 3.65))

    q_series = m3_papers["n_queries"]
    p99_q = float(np.percentile(q_series, 99))
    clipped_q = np.clip(q_series, 0, p99_q)
    ax_q.hist(clipped_q, bins=28, color="#1971c2", edgecolor="#ffffff", alpha=0.90)
    ax_q.axvline(float(q_series.mean()), color="#e03131", linestyle="--", linewidth=1.4, label=f"TB: {q_series.mean():.1f}")
    ax_q.axvline(float(q_series.median()), color="#2b8a3e", linestyle="-.", linewidth=1.4, label=f"Trung vị: {q_series.median():.0f}")
    ax_q.set_xlabel(f"Số truy vấn BibTeX / bài (gộp đuôi >= P99 = {p99_q:.0f})")
    ax_q.set_ylabel("Số lượng bài báo")
    ax_q.set_title(f"Phân phối số truy vấn / bài ({len(m3_papers):,} bài · TB={q_series.mean():.1f})")
    ax_q.legend(loc="upper right", fontsize=8.2)

    parts = ["train", "valid", "test"]
    pos_shares = [sb[p]["overall"]["positive_queries"] / max(sb[p]["overall"]["queries"], 1) * 100.0 for p in parts]
    neg_shares = [100.0 - ps for ps in pos_shares]
    xp = np.arange(len(parts))
    ax_sp.bar(xp, pos_shares, width=0.46, label="Có đáp án arXiv (matchable)", color="#2b8a3e")
    ax_sp.bar(xp, neg_shares, bottom=pos_shares, width=0.46, label="Ngoài arXiv (negative-only)", color="#94a3b8")
    ax_sp.set_xticks(xp)
    ax_sp.set_xticklabels([
        f"train\n({sb['train']['overall']['papers']} bài · {sb['train']['overall']['queries']:,} q)",
        f"valid\n({sb['valid']['overall']['papers']} bài · {sb['valid']['overall']['queries']} q)",
        f"test\n({sb['test']['overall']['papers']} bài · {sb['test']['overall']['queries']} q)",
    ], fontsize=8.3)
    ax_sp.set_ylabel("Tỷ trọng truy vấn (%)")
    ax_sp.set_ylim(0, 118)
    ax_sp.set_title("Tỷ trọng Matchable vs. Negative-only theo Split")
    for xi, ps, ns in zip(xp, pos_shares, neg_shares):
        ax_sp.text(xi, ps / 2, f"{ps:.1f}%", ha="center", va="center", color="white", fontweight="bold", fontsize=8.5)
        ax_sp.text(xi, ps + ns / 2, f"{ns:.1f}%", ha="center", va="center", color="#0f172a", fontweight="bold", fontsize=8.5)
    ax_sp.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=2, fontsize=8.0)

    plt.tight_layout()
    plt.show()
    plt.close(fig)
else:
    show_pending_m3_banner("Bảng phân rã splits và biểu đồ phân phối truy vấn tại Mục 11.3")
```

**Phân tích cấu trúc tập `train / valid / test` và quy luật nhãn:**

- **Tuân thủ tuyệt đối quy tắc tách cấp bài báo (`seed = 42`):** Tập `valid` gồm đúng 2 bài báo (`2408.11078` thủ công với `22` mục và `2408.13851` tự động với `50` mục — tổng `72` truy vấn), và tập `test` gồm đúng 2 bài báo (`2408.11203` thủ công với `24` mục và `2408.15325` tự động với `74` mục — tổng `98` truy vấn). Không có bất kỳ bài báo nào giao thoa giữa ba phân vùng.
- **Sự biến động tự nhiên của tỷ trọng nhãn dương giữa các bài báo:** Trên toàn bộ `515` bài đã gán nhãn, trung vị mỗi bài có **`42` mục BibTeX** (trung bình **`52,35`** mục), trong đó tỷ lệ trích dẫn khớp arXiv đạt **`31,70%`** (`8.547 / 26.959`). Tỷ trọng này thay đổi rõ theo chuyên ngành: bài vật lý toán `2408.11078` (`valid/manual`) và bài xác suất `2408.13851` (`valid/auto`) trích dẫn nhiều tài liệu sách/tạp chí cổ điển nên tỷ lệ dương chỉ là `36,4%` và `14,0%` (tổng hợp `valid = 20,8%`), trong khi bài `2408.15325` (`test/auto`) có tới `90,5%` trích dẫn trên arXiv (tổng hợp `test = 77,6%`). Sự khác biệt này lý giải trực tiếp vì sao chỉ số `MRR@5_all` dao động mạnh theo mẫu bài (`0,1609` trên `valid` vs `0,7755` trên `test`), khẳng định tầm quan trọng của việc báo cáo song song `MRR@5_matchable`.

---

## 11.4. Phân tích Đóng góp 21 Đặc trưng (`Feature Importance Gain`)

```{code-cell} ipython3
:tags: [remove-input]

if HAS_M3_STATS:
    gains = m3_eval.get("feature_importance_gain") or m3_eval.get("ranker_metadata", {}).get("feature_importance_gain", {})
    m2_cols = {"cite_frequency", "first_cite_section_type", "first_cite_section_depth"}
    rel_cols = {"title_sim_rank_in_query", "title_sim_diff_from_max", "title_sim_margin_to_top2"}
    anchor_cols = {"arxiv_id_in_bib_text", "doi_exact_match"}

    def _feat_group(name: str) -> str:
        if name in m2_cols:
            return "AST Milestone 2 (E)"
        if name in rel_cols:
            return "Tương đối truy vấn (A)"
        if name in anchor_cols:
            return "Mỏ neo định danh (B)"
        if "author" in name:
            return "Tác giả (B)"
        if "year" in name:
            return "Thời gian (B)"
        return "Từ vựng tiêu đề (B)"

    gain_df = pd.DataFrame([
        {
            "Đặc trưng": k,
            "Nhóm đặc trưng": _feat_group(k),
            "Gain (LightGBM)": float(v),
        }
        for k, v in gains.items()
    ]).sort_values("Gain (LightGBM)", ascending=False).reset_index(drop=True)
    tot_gain = max(float(gain_df["Gain (LightGBM)"].sum()), 1e-9)
    gain_df["Tỷ trọng Gain (%)"] = gain_df["Gain (LightGBM)"] / tot_gain * 100.0

    nz_df = gain_df[gain_df["Gain (LightGBM)"] > 0].copy()
    disp_df = nz_df.copy()
    disp_df["Gain (LightGBM)"] = disp_df["Gain (LightGBM)"].map(lambda x: f"{x:,.2f}")
    disp_df["Tỷ trọng Gain (%)"] = disp_df["Tỷ trọng Gain (%)"].map(lambda x: f"{x:.2f}%")
    show_table(disp_df)

    plot_df = gain_df.head(10).iloc[::-1]
    fig, ax_g = plt.subplots(figsize=(9.5, 3.85))
    colors_g = []
    for f in plot_df["Đặc trưng"]:
        if f in m2_cols:
            colors_g.append("#d97706")
        elif f in rel_cols:
            colors_g.append("#0f766e")
        elif f in anchor_cols:
            colors_g.append("#2b8a3e")
        else:
            colors_g.append("#1971c2")

    bars_g = ax_g.barh(plot_df["Đặc trưng"], plot_df["Gain (LightGBM)"], color=colors_g, height=0.60)
    ax_g.set_xlabel("Mức độ đóng góp thông tin (Information Gain)")
    ax_g.set_title("Top-10 đặc trưng theo Information Gain trong LightGBM LambdaMART")
    max_g = max(plot_df["Gain (LightGBM)"].tolist() + [1.0])
    for b, val in zip(bars_g, plot_df["Gain (LightGBM)"]):
        pct_g = val / tot_gain * 100.0
        lbl = f"{val:,.1f} ({pct_g:.2f}%)" if val > 0 else "0.0"
        ax_g.text(
            b.get_width() + max_g * 0.015,
            b.get_y() + b.get_height() / 2,
            lbl,
            va="center",
            fontsize=8.2,
            fontweight="bold" if val > 0 else "normal",
        )
    ax_g.set_xlim(0, max_g * 1.28)
    plt.tight_layout()
    plt.show()
    plt.close(fig)
else:
    show_pending_m3_banner("Bảng và biểu đồ Feature Importance Gain tại Mục 11.4")
```

**Diễn giải hành vi học của `LightGBM LambdaMART` qua `Feature Importance Gain`:**

- **Đặc trưng tương đối nội bộ truy vấn `title_sim_diff_from_max` dẫn đầu áp đảo (`88,88%` tổng Gain = `29.863,90`):** Thay vì so khớp bằng một ngưỡng điểm tuyệt đối cứng, cây quyết định `LambdaMART` chọn độ lệch so với ứng viên tiêu đề cao nhất ngay trong truy vấn làm gốc phân tách chính, kèm theo `title_sim_rank_in_query` (`5,22` Gain) để định vị ứng viên ứng cử số 1.
- **Mỏ neo định danh & TF-IDF nội bộ đóng vai trò chốt hạ (`9,29%` và `1,09%` Gain):** Hai đặc trưng `doi_exact_match` (`1.699,75` Gain — `5,06%`) và `arxiv_id_in_bib_text` (`1.420,50` Gain — `4,23%`) giúp cứu các ca tiêu đề bị cắt ngắn hoặc biến đổi mạnh khi xuất bản lại, theo sau bởi `title_tfidf_cosine` (`365,19` Gain — `1,09%`), `year_diff` (`197,21` Gain — `0,59%`) và cụm tác giả `authors_jaccard_sim` (`41,93`) + `author_count_diff` (`2,24`).
- **Tín hiệu cấu trúc AST Milestone 2 (`cite_frequency = 6,00` Gain) tham gia trực tiếp vào nhánh phân tách:** Dù cơ chế dừng sớm trên `Valid-Manual` dừng ở `best_iteration = 1` (do quy mô `Valid-Manual` chỉ gồm `8` nhóm có cặp dương/âm trên một bài báo, mô hình nhanh chóng hội tụ để tránh overfit), đặc trưng **`cite_frequency`** từ đồ thị AST Milestone 2 vẫn đứng ở **Top-7** toàn cục (có Gain dương lớn hơn cả `title_sim_rank_in_query` và `author_count_diff`).
