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

# Chương 12. Đánh giá Mô hình `MRR@5`, Ablation M2 & Kiểm chứng Hugging Face

Toàn bộ bảng số liệu đánh giá, đối sánh 4 mô hình, thí nghiệm Ablation cấu trúc M2 và kiểm toán đóng gói 6 bảng Hugging Face trong chương này được nạp tự động lúc biên dịch sách từ `arxiv-book/stats/m3/` (`m3_evaluation.json`, `m3_summary.json`, `m3_hf_tables.csv`).

```{admonition} Trạng thái Đánh giá Thực nghiệm trên Dải range_0 (5.000 ID)
:class: note
Kết quả dưới đây phản ánh phiên chạy hoàn chỉnh end-to-end của thành viên **A — Võ Gia Phúc** trên dải **`range_0`** (`2408.11045`–`2408.16044`) với `515` bài báo (`26.959` truy vấn). Toàn bộ quy trình chạy trên CPU trong **`347,09 s` (`5,78 phút`)** với thời gian huấn luyện `LightGBM LambdaMART` chỉ **`0,974 s`**, đạt **`MRR@5 (matchable) = 1,0000`** (`Hit@1 = 100%`) trên tập `test`, **`MRR@5 (matchable) = 0,7722`** (`Hit@5 = 100%`) trên tập `valid`, và đóng gói hợp lệ **`7.693.326` dòng** qua 6 bảng Parquet (`185,28 MiB`) tương thích Hugging Face `datasets`.
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


def _find_stats_dir(subdir: str = "m3", marker: str = "m3_evaluation.json") -> Path:
    for base in (
        Path("../stats"),
        Path("stats"),
        *[parent / "stats" for parent in Path.cwd().parents],
    ):
        for candidate in (base / subdir, base):
            if candidate.is_dir() and (candidate / marker).is_file():
                return candidate
    return Path(f"../stats/{subdir}")


STATS_DIR = _find_stats_dir("m3", "m3_evaluation.json")
REQUIRED_M3_EVAL = ("m3_evaluation.json", "m3_summary.json", "m3_hf_tables.csv")
MISSING_M3_EVAL = [name for name in REQUIRED_M3_EVAL if not (STATS_DIR / name).is_file()]
HAS_M3_EVAL = len(MISSING_M3_EVAL) == 0


def show_table(df: pd.DataFrame, *, kv: bool = False) -> None:
    classes = "dataframe jb-stats-table jb-kv-table" if kv else "dataframe jb-stats-table"
    display(HTML(df.to_html(index=False, border=0, classes=classes)))


def show_pending_m3_banner(section_desc: str) -> None:
    missing_html = ", ".join(f"<code>stats/m3/{name}</code>" for name in MISSING_M3_EVAL)
    html = (
        '<div class="jb-pending-card">'
        '<div class="jb-pending-title">Đang chờ bộ tệp đánh giá Milestone 3 trong <code>arxiv-book/stats/m3/</code></div>'
        f"<div>Hiện chưa tìm thấy: {missing_html}. "
        f"{section_desc} sẽ <strong>tự động sinh đầy đủ</strong> khi bổ sung các tệp thống kê M3 và biên dịch lại sách.</div>"
        "</div>"
    )
    display(HTML(html))
```

## 12.1. Kết quả Đánh giá `MRR@5` trên Tập Kiểm tra (`test`) & Tập Kiểm định (`valid`)

```{code-cell} ipython3
:tags: [remove-input]

if HAS_M3_EVAL:
    m3_eval = json.loads((STATS_DIR / "m3_evaluation.json").read_text(encoding="utf-8"))
    m3_sum = json.loads((STATS_DIR / "m3_summary.json").read_text(encoding="utf-8"))
    hf_df = pd.read_csv(STATS_DIR / "m3_hf_tables.csv")

    eval_rows = []
    for part in ("test", "valid"):
        for item in m3_eval.get(part, []):
            ex = item.get("extra", {})
            nq = int(item["num_queries"])
            nm = int(item["num_matchable_queries"])
            nn = int(item["num_negative_only_queries"])
            eval_rows.append({
                "Phân vùng": part,
                "Lát cắt (subset)": item["subset"],
                "|Q| (Tổng / Dương / Âm)": f"{nq} / {nm} / {nn}",
                "MRR@5 (matchable)": f"{item['mrr_at_5_matchable']:.4f}",
                "MRR@5 (all — Eq. 1)": f"{item['mrr_at_5_all']:.4f}",
                "Hit@1 (match.)": f"{item['hit_at_1'] * 100:.2f}%",
                "Hit@3 (match.)": f"{item['hit_at_3'] * 100:.2f}%",
                "Hit@5 (match.)": f"{item['hit_at_5'] * 100:.2f}%",
                "Rank1 / Rank2–5 / Miss": f"{int(ex.get('rank1_count', 0))} / {int(ex.get('rank2_5_count', 0))} / {int(ex.get('miss_count', 0))}",
            })
    show_table(pd.DataFrame(eval_rows))

    fig, (ax_mrr, ax_rk) = plt.subplots(1, 2, figsize=(10.4, 3.75))

    subsets = ["overall", "manual", "auto"]
    test_map = {x["subset"]: x for x in m3_eval["test"]}
    valid_map = {x["subset"]: x for x in m3_eval["valid"]}
    sub_labels = [
        f"Overall\n({test_map['overall']['num_queries']} q / {valid_map['overall']['num_queries']} q)",
        f"Manual Gold\n({test_map['manual']['num_queries']} q / {valid_map['manual']['num_queries']} q)",
        f"Auto Silver\n({test_map['auto']['num_queries']} q / {valid_map['auto']['num_queries']} q)",
    ]

    x = np.arange(len(subsets))
    w = 0.20
    t_match = [test_map[s]["mrr_at_5_matchable"] for s in subsets]
    t_all = [test_map[s]["mrr_at_5_all"] for s in subsets]
    v_match = [valid_map[s]["mrr_at_5_matchable"] for s in subsets]
    v_all = [valid_map[s]["mrr_at_5_all"] for s in subsets]

    b1 = ax_mrr.bar(x - 1.5 * w, t_match, w, label="Test MRR@5 (matchable)", color="#2b8a3e")
    b2 = ax_mrr.bar(x - 0.5 * w, t_all, w, label="Test MRR@5 (all, Eq. 1)", color="#69db7c")
    b3 = ax_mrr.bar(x + 0.5 * w, v_match, w, label="Valid MRR@5 (matchable)", color="#1971c2")
    b4 = ax_mrr.bar(x + 1.5 * w, v_all, w, label="Valid MRR@5 (all, Eq. 1)", color="#74c0fc")
    ax_mrr.set_xticks(x)
    ax_mrr.set_xticklabels(sub_labels, fontsize=8.3)
    ax_mrr.set_ylim(0, 1.24)
    ax_mrr.set_ylabel("Giá trị MRR@5")
    ax_mrr.set_title("MRR@5 theo lát cắt Manual / Auto trên Test & Valid")
    for bars in (b1, b2, b3, b4):
        for b in bars:
            val = b.get_height()
            ax_mrr.text(b.get_x() + b.get_width() / 2, val + 0.015, f"{val:.2f}", ha="center", fontsize=7.2, fontweight="bold")
    ax_mrr.legend(loc="upper center", bbox_to_anchor=(0.5, -0.17), ncol=2, fontsize=7.6)

    rk_groups = ["Test\nOverall (98)", "Test\nManual (24)", "Valid\nOverall (72)", "Valid\nManual (22)"]
    rk_src = [test_map["overall"], test_map["manual"], valid_map["overall"], valid_map["manual"]]
    r1 = np.array([d["extra"]["rank1_count"] for d in rk_src])
    r25 = np.array([d["extra"]["rank2_5_count"] for d in rk_src])
    miss = np.array([d["extra"]["miss_count"] for d in rk_src])
    neg = np.array([d["num_negative_only_queries"] for d in rk_src])

    xr = np.arange(len(rk_groups))
    ax_rk.bar(xr, r1, width=0.5, label="Đúng tại Rank 1", color="#2b8a3e")
    ax_rk.bar(xr, r25, bottom=r1, width=0.5, label="Đúng tại Rank 2–5", color="#f59f00")
    ax_rk.bar(xr, miss, bottom=r1 + r25, width=0.5, label="Trượt Top-5 (Miss)", color="#e03131")
    ax_rk.bar(xr, neg, bottom=r1 + r25 + miss, width=0.5, label="Toàn âm (Negative-only)", color="#cbd5e1")
    ax_rk.set_xticks(xr)
    ax_rk.set_xticklabels(rk_groups, fontsize=8.3)
    ax_rk.set_ylabel("Số lượng truy vấn")
    ax_rk.set_title("Phân rã thứ hạng dự đoán trên tập Test & Valid")
    for xi, a, b, c, d in zip(xr, r1, r25, miss, neg):
        if a > 0:
            ax_rk.text(xi, a / 2, f"{int(a)}", ha="center", va="center", color="white", fontweight="bold", fontsize=8.0)
        if b > 0:
            ax_rk.text(xi, a + b / 2, f"{int(b)}", ha="center", va="center", color="white", fontweight="bold", fontsize=8.0)
        if d > 0:
            ax_rk.text(xi, a + b + c + d / 2, f"{int(d)}", ha="center", va="center", color="#334155", fontweight="bold", fontsize=8.0)
    ax_rk.legend(loc="upper center", bbox_to_anchor=(0.5, -0.17), ncol=2, fontsize=7.6)

    plt.tight_layout()
    plt.show()
    plt.close(fig)
else:
    show_pending_m3_banner("Bảng chỉ số MRR@5 và biểu đồ phân rã thứ hạng tại Mục 12.1")
```

**Phân tích sâu hiệu quả xếp hạng trên tập `test` và tập `valid`:**

- **Đạt điểm tuyệt đối trên tập `test` (`98` truy vấn thuộc `2408.11203` + `2408.15325`):** Trên toàn bộ `76` truy vấn có bản arXiv thật (`9` truy vấn Manual + `67` truy vấn Auto), `LightGBM LambdaMART` xếp đúng đáp án ngay tại vị trí **`cand1` trên 76/76 truy vấn (`Hit@1 = 100,00%`, `MRR@5_matchable = 1,0000`, `Miss = 0`)**. Khi tính cả `22` truy vấn ngoài arXiv theo phương trình (1) của đề bài, chỉ số **`MRR@5_all` đạt `0,7755`** (`76 / 98`), chạm đúng **100% trần lý thuyết** của tập kiểm tra (`0,3750` trên lát cắt `manual` ứng với `9/24` và `0,9054` trên lát cắt `auto` ứng với `67/74`).
- **Sức mạnh phục hồi Top-5 trên tập kiểm định khó `valid` (`2408.11078` + `2408.13851`):** Bài kiểm định thủ công `2408.11078` là ca thử thách thực sự vì sử dụng kiểu trích dẫn Vật lý chỉ ghi tên tạp chí không có tiêu đề (nơi `auto_matcher` ở Mục 11.2 chỉ đạt Recall `25,0%`, bỏ sót `6/8` liên kết). Dù vậy, `LightGBM LambdaMART` vẫn đưa được **`100,00%` (15/15) truy vấn có đáp án vào Top-5** (`Hit@1 = 66,67%`, `Hit@3 = 80,00%`, **`Hit@5 = 100,00%`**, `MRR@5_matchable = 0,7722` toàn phần và `0,5729` trên riêng `valid/manual` với `0` truy vấn trượt ngoài Top-5). Điều này chứng minh bộ đặc trưng đa chiều (`authors`, `year`, `tfidf`, `cite_frequency`) vẫn định vị được ứng viên đúng vào Top-5 ngay cả khi trường tiêu đề BibTeX bị khuyết hoàn toàn.

---

## 12.2. Đối sánh 4 Mô hình & Nghiên cứu Ablation Cấu trúc Milestone 2

```{code-cell} ipython3
:tags: [remove-input]

if HAS_M3_EVAL:
    models_dict = m3_eval.get("models", {})
    ablation_dict = m3_eval.get("ablation", {})

    comp_rows = []
    for label, entry in list(models_dict.items()) + list(ablation_dict.items()):
        ov = next((x for x in entry if x["subset"] == "overall"), entry[0])
        mn = next((x for x in entry if x["subset"] == "manual"), {})
        au = next((x for x in entry if x["subset"] == "auto"), {})
        comp_rows.append({
            "Mô hình / Cấu hình Ablation": label,
            "Nhóm": "Ablation M2" if label in ablation_dict else "Đối sánh mô hình",
            "MRR@5 matchable (Overall)": f"{ov['mrr_at_5_matchable']:.4f}",
            "MRR@5 all (Overall)": f"{ov['mrr_at_5_all']:.4f}",
            "MRR@5 all (Manual)": f"{mn.get('mrr_at_5_all', 0.0):.4f}",
            "MRR@5 all (Auto)": f"{au.get('mrr_at_5_all', 0.0):.4f}",
            "Hit@1 (match.)": f"{ov['hit_at_1'] * 100:.2f}%",
            "Hit@5 (match.)": f"{ov['hit_at_5'] * 100:.2f}%",
        })
    show_table(pd.DataFrame(comp_rows))

    fig, (ax_cmp, ax_abl) = plt.subplots(1, 2, figsize=(10.3, 3.65))

    m_names = list(models_dict.keys())
    m_vals = [
        next((x["mrr_at_5_matchable"] for x in models_dict[m] if x["subset"] == "overall"), 0.0)
        for m in m_names
    ]
    m_all_vals = [
        next((x["mrr_at_5_all"] for x in models_dict[m] if x["subset"] == "overall"), 0.0)
        for m in m_names
    ]
    xm = np.arange(len(m_names))
    ax_cmp.bar(xm - 0.18, m_vals, 0.35, label="MRR@5 (matchable)", color="#1971c2")
    ax_cmp.bar(xm + 0.18, m_all_vals, 0.35, label="MRR@5 (all, Eq. 1)", color="#2b8a3e")
    ax_cmp.set_xticks(xm)
    ax_cmp.set_xticklabels([n.replace(" ", "\n", 1) for n in m_names], fontsize=8.1)
    ax_cmp.set_ylim(0, 1.22)
    ax_cmp.set_ylabel("MRR@5 trên tập Test")
    ax_cmp.set_title(f"Đối sánh 4 mô hình trên Test Set ({test_map['overall']['num_queries']} truy vấn)")
    for xi, v1, v2 in zip(xm, m_vals, m_all_vals):
        ax_cmp.text(xi - 0.18, v1 + 0.02, f"{v1:.3f}", ha="center", fontsize=7.6, fontweight="bold")
        ax_cmp.text(xi + 0.18, v2 + 0.02, f"{v2:.3f}", ha="center", fontsize=7.6, fontweight="bold")
    ax_cmp.legend(loc="upper center", bbox_to_anchor=(0.5, -0.20), ncol=2, fontsize=7.8)

    ab_names = list(ablation_dict.keys())
    ab_match = [
        next((x["mrr_at_5_matchable"] for x in ablation_dict[a] if x["subset"] == "overall"), 0.0)
        for a in ab_names
    ]
    ab_all = [
        next((x["mrr_at_5_all"] for x in ablation_dict[a] if x["subset"] == "overall"), 0.0)
        for a in ab_names
    ]
    xa = np.arange(len(ab_names))
    ax_abl.bar(xa - 0.18, ab_match, 0.34, label="MRR@5 (matchable)", color="#64748b")
    ax_abl.bar(xa + 0.18, ab_all, 0.34, label="MRR@5 (all, Eq. 1)", color="#d97706")
    ax_abl.set_xticks(xa)
    ax_abl.set_xticklabels(ab_names, fontsize=8.5)
    ax_abl.set_ylim(0, 1.22)
    ax_abl.set_ylabel("MRR@5 trên tập Test")
    ax_abl.set_title("Ablation Study: Không M2 (18) vs. Có M2 AST (21)")
    for xi, v1, v2 in zip(xa, ab_match, ab_all):
        ax_abl.text(xi - 0.18, v1 + 0.02, f"{v1:.3f}", ha="center", fontsize=8.0, fontweight="bold")
        ax_abl.text(xi + 0.18, v2 + 0.02, f"{v2:.3f}", ha="center", fontsize=8.0, fontweight="bold")
    ax_abl.legend(loc="upper center", bbox_to_anchor=(0.5, -0.20), ncol=2, fontsize=7.8)

    plt.tight_layout()
    plt.show()
    plt.close(fig)
else:
    show_pending_m3_banner("Bảng và biểu đồ đối sánh 4 mô hình và Ablation M2 tại Mục 12.2")
```

**Đánh giá khách quan hiện tượng đồng hạng trên tập `test` và vai trò của M2 AST:**

- **Lý do 4 mô hình và cặp Ablation cùng đạt `MRR@5_matchable = 1,0000` trên tập `test` của `range_0`:** Tuân thủ đúng quy ước chia tập của đề bài, phân vùng `test` trong một dải 5.000 ID chỉ gồm **2 công bố** (`2408.11203` manual + `2408.15325` auto). Khác với bài Vật lý khuyết tiêu đề ở `valid`, cả hai công bố trong `test` đều chứa danh mục BibTeX đầy đủ tiêu đề hoặc mỏ neo định danh rõ ràng, khiến mọi phương pháp từ `Title Fuzzy`, `TF-IDF Cosine`, `Logistic Regression` cho tới `LightGBM LambdaMART` (cả 18 và 21 đặc trưng) đều xếp đúng cả `76/76` mục ở hạng 1.
- **Bằng chứng đóng góp thực tế của AST Milestone 2:** Dù điểm cuối trên 2 bài `test` đã bão hòa ở `1,0000`, phân tích Gain nội bộ của mô hình (Mục 11.4) chứng minh đặc trưng `cite_frequency` từ cây phân cấp AST Milestone 2 đóng góp **`6,004` Information Gain** (đứng thứ 7/21 đặc trưng, vượt qua cả `title_sim_rank_in_query` và `author_count_diff`). Để quan sát sự tách biệt rõ rệt về `MRR@5` giữa các mô hình và giữa 18 vs 21 đặc trưng trên các bài trích dẫn rút gọn/nhiễu, bước tổng hợp **cả 5 dải (`10` bài Test trên `25.000` ID)** ở vòng tổng kết Poster A2 đóng vai trò quyết định.

---

## 12.3. Hiệu năng Pipeline & Đóng gói 6 Bảng Hugging Face (`data/hf_range_0/`)

```{code-cell} ipython3
:tags: [remove-input]

if HAS_M3_EVAL:
    rmeta = m3_eval.get("ranker_metadata", {})
    n_bib_papers = int(m3_sum["n_papers_in_range"])
    elapsed_s = float(m3_sum["elapsed_seconds"])
    train_s = float(rmeta.get("training_seconds", m3_sum.get("training_seconds", 0.0)))

    perf_rows = [
        ("Tổng thời gian thực thi đầu–cuối pipeline M3 (elapsed_seconds)", f"{elapsed_s:,.2f} s ({elapsed_s / 60:.2f} phút)"),
        ("Thông lượng tiền xử lý & trích 21 đặc trưng trên toàn dải", f"{n_bib_papers:,} bài ({elapsed_s * 1000 / max(n_bib_papers, 1):.1f} ms / bài có BibTeX)"),
        ("Số cặp ứng viên 21 đặc trưng đã sinh (n_features)", f"{int(m3_sum['n_features']):,} cặp (Stage-1 Blocking khi n > 50)"),
        ("Thời gian huấn luyện LightGBM LambdaMART (training_seconds)", f"{train_s:.3f} s trên {int(rmeta.get('train_rows', 0)):,} dòng ({int(rmeta.get('train_groups', 0)):,} nhóm)"),
        ("Tổng quy mô 6 bảng Sharded Parquet Hugging Face (hf_range_0)", f"{int(m3_sum['hf_total_rows']):,} dòng · {int(m3_sum['hf_total_shards'])} shards · {float(hf_df['bytes'].sum()) / 1024**2:.2f} MiB"),
    ]
    show_table(pd.DataFrame(perf_rows, columns=["Chỉ số hiệu năng & đóng gói Milestone 3 (Mục 12.3)", "Giá trị đo đạc"]), kv=True)

    hf_disp = pd.DataFrame({
        "Bảng (config_name)": hf_df["table_name"],
        "Nguồn": hf_df["milestone"],
        "Số dòng": hf_df["rows"].map(lambda x: f"{int(x):,}"),
        "Số shard": hf_df["shards"].map(lambda x: f"{int(x)}"),
        "Dung lượng (MiB)": hf_df["bytes"].map(lambda b: f"{float(b) / 1024**2:.2f} MiB"),
        "Khóa liên kết": hf_df["key_columns"],
        "Nội dung chính": hf_df["description"],
    })
    show_table(hf_disp)

    fig, (ax_sz, ax_rw) = plt.subplots(1, 2, figsize=(10.3, 3.6))

    tbls = hf_df["table_name"].tolist()
    mibs = (hf_df["bytes"] / 1024**2).tolist()
    rows_m = (hf_df["rows"] / 1e6).tolist()
    t_colors = ["#1971c2" if m == "M1" else ("#0b7285" if m == "M2" else "#2b8a3e") for m in hf_df["milestone"]]

    b_sz = ax_sz.barh(tbls, mibs, color=t_colors, height=0.56)
    ax_sz.invert_yaxis()
    ax_sz.set_xlabel("Dung lượng Parquet ZSTD (MiB)")
    ax_sz.set_title("Dung lượng lưu trữ 6 bảng Hugging Face (range_0)")
    max_sz = max(mibs + [1.0])
    tot_sz = max(sum(mibs), 1e-6)
    for b, v in zip(b_sz, mibs):
        ax_sz.text(
            b.get_width() + max_sz * 0.02,
            b.get_y() + b.get_height() / 2,
            f"{v:.2f} MiB ({v / tot_sz * 100:.1f}%)",
            va="center",
            fontsize=8.0,
            fontweight="bold",
        )
    ax_sz.set_xlim(0, max_sz * 1.44)

    b_rw = ax_rw.barh(tbls, rows_m, color=t_colors, height=0.56)
    ax_rw.invert_yaxis()
    ax_rw.set_xlabel("Số bản ghi (triệu dòng)")
    ax_rw.set_title(f"Số lượng bản ghi trên 6 bảng (tổng {int(hf_df['rows'].sum()) / 1e6:.2f} triệu dòng)")
    max_rw = max(rows_m + [0.1])
    for b, raw_r in zip(b_rw, hf_df["rows"].tolist()):
        ax_rw.text(
            b.get_width() + max_rw * 0.02,
            b.get_y() + b.get_height() / 2,
            f"{int(raw_r):,}",
            va="center",
            fontsize=8.0,
            fontweight="bold",
        )
    ax_rw.set_xlim(0, max_rw * 1.38)

    plt.tight_layout()
    plt.show()
    plt.close(fig)
else:
    show_pending_m3_banner("Bảng hiệu năng và thống kê 6 bảng Hugging Face tại Mục 12.3")
```

**Đánh giá hiệu năng vận hành & tính sẵn sàng công bố Hugging Face:**

1. **Hiệu năng CPU vượt trội nhờ tiền xử lý 1 lần và `rapidfuzz` C++:** Trên máy cục bộ không sử dụng GPU, toàn bộ luồng đọc streaming Parquet M1/M2, tiền xử lý `4.247` bài có BibTeX, chạy Auto-Matcher & Audit, trích `519.700` vector 21 đặc trưng, huấn luyện đồng thời 4 mô hình + cặp Ablation M2 và đánh giá `MRR@5` hoàn tất chỉ trong **`347,09 s` (`5,78 phút`)** — trong đó bước huấn luyện `LightGBM LambdaMART` trên `210.774` dòng chỉ mất **`0,974 giây`**.
2. **Đóng gói chuẩn Streaming & Tương thích 100% `datasets.load_dataset`:** Bộ dữ liệu đầu ra tại `data/hf_range_0/` gói gọn toàn bộ kết quả của cả 3 Milestone (`7.693.326` dòng trải trên `17` phân mảnh nén `ZSTD`) trong **`185,28 MiB` (`194.277.601 B`)** — với `elements` (`2.945.275` dòng, `10` shards, `137,04 MiB`) và `bibtex` (`229.161` dòng, `1` shard, `20,68 MiB`) chiếm phần lớn dung lượng, còn bảng `predictions` (`26.959` dòng của `515` bài thuộc `train`/`valid`/`test`) chỉ chiếm **`0,59 MiB`**. Toàn bộ 6 `config_name` đều đã qua kiểm chứng đọc lại bằng `datasets.load_dataset` ở cổng `--verify-hf`.

---

(m3-tai-lieu-tham-khao)=
## Tài liệu Tham khảo (Milestone 3)

1. Burges, C. J. C. (2010). *From RankNet to LambdaRank to LambdaMART: An Overview*. Microsoft Research Technical Report MSR-TR-2010-82.
2. Ke, G., Meng, Q., Finley, T., Wang, T., Chen, W., Ma, W., Ye, Q., & Liu, T.-Y. (2017). *LightGBM: A Highly Efficient Gradient Boosting Decision Tree*. In *Advances in Neural Information Processing Systems (NeurIPS)*, pp. 3146–3154.
3. Bachmann, M., et al. *RapidFuzz: Rapid fuzzy string matching in Python and C++*. <https://github.com/rapidfuzz/RapidFuzz>
4. Lhoest, Q., Villanova del Moral, A., Jernite, Y., Thakur, A., von Platen, P., Patil, S., Chaumond, J., Drame, M., Plu, J., Tunstall, L., Davison, J., Šaško, M., Chhablani, G., Malik, B., Brandeis, S., Le Scao, T., Sanh, V., Xu, C., Patry, N., McMillan-Major, A., Schmid, P., Gugger, S., Delangue, C., Matussière, T., Debut, L., Bekman, S., Cistac, P., Trapp, T., Goff, R., & Wolf, T. (2021). *Datasets: A Community Library for Natural Language Processing*. In *Proceedings of EMNLP 2021: System Demonstrations*, pp. 175–184.
5. Kinney, R., Anastasiades, C., Authur, R., et al. (2023). *The Semantic Scholar Open Data Platform*. arXiv:2301.10140.
