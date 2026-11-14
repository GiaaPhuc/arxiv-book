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

# Chương 8. Đánh giá Hiệu năng Bộ Phân tích Cú pháp

```{admonition} Trạng thái số liệu Chương 8: Đã hoàn tất đo đạc thực nghiệm trên 25.000 bài báo (12 worker)
:class: note
Toàn bộ chỉ số thời gian thực thi đầu–cuối, phân rã CPU theo 4 chặng, phân phối độ trễ cấp bài báo, mức tiêu thụ bộ nhớ RSS và dung lượng 3 bảng Sharded Parquet trong chương này được nạp tự động từ `stats/m2/m2_performance.json` và `stats/m2/m2_papers_stats.csv` (phiên chạy đầy đủ `25.000` bài báo / `41.629` phiên bản hoàn tất lúc `2026-11-14T12:04:47+00:00`, `wall_seconds = 1.688,11 s ≈ 28,14 phút`, `papers_failed = 0`).
```

## 8.1. Môi trường Kiểm thử & Phương pháp Đo lường Kiểm chứng

Tuân thủ tiêu chí đánh giá hiệu năng của đề bài, toàn bộ quá trình phân tích cú pháp, chuẩn hóa và khử trùng lặp của Milestone 2 chạy hoàn toàn trên **CPU thuần túy (CPU-only, không sử dụng GPU/TPU)** và **không phát sinh I/O mạng**: toàn bộ cây thư mục `.tex`/`.bib` sau khi giải nén cục bộ (`25.286.215.425 B ≈ 23,550 GiB`) được đọc trực tiếp từ đĩa cục bộ và ghi ra 3 bảng Sharded Parquet theo lô song song.

- **Cấu hình thực thi song song ghi nhận trong nhật ký (`stats/m2/m2_performance.json`):** Hệ thống điều phối `ProcessPoolExecutor` với **`workers = 12` tiến trình xử lý song song**, kích thước lô xả phân mảnh **`batch_size = 500` bài báo / shard** (tổng cộng `50` shard cho mỗi bảng trên toàn tập `25.000` bài báo), và tách hoàn toàn khỏi Google Drive FUSE ở khâu đọc/ghi trung gian.
- **Phương pháp đo đạc tự động trong `src/parsing/pipeline.py` (`stats/m2/m2_performance.json` & `stats/m2/m2_papers_stats.csv`):**
  1. *Thời gian chạy đầu–cuối và phân rã 4 chặng:* Đồng hồ đơn điệu `time.perf_counter()` đo thời gian thực tổng thể (`wall_seconds`) của toàn bộ tiến trình điều phối kèm thời gian xử lý tích lũy trên từng bài báo qua 4 chặng cốt lõi: `gather` (khử comment, bầu chọn gốc, nối phẳng đa tệp), `hierarchy` (mở rộng macro, chuẩn hóa toán, dựng cây ngăn xếp đơn điệu và tách câu ngữ cảnh), `bib` (phân tích `.bib`/`.bbl` và cascade 4 mẫu `\bibitem`), và `dedup` (gom cụm Union-Find, viết lại `\cite{}` và băm toàn văn xuyên phiên bản).
  2. *Bộ nhớ RAM toàn hệ thống (kể cả worker con) & Lưu trữ đĩa:* Luồng nền `ResourceSampler` lấy mẫu định kỳ (`1.648` mẫu trong `1.688,11 s`, trung bình ~`1,0 s`/mẫu) tổng bộ nhớ vật lý thường trú (`RSS`) của tiến trình điều phối cộng toàn bộ tiến trình con trong `ProcessPoolExecutor` (`total_rss_bytes()` qua `psutil`), đồng thời đo đối chứng kích thước kho nguồn đầu vào (`input_corpus_bytes`) với tổng dung lượng các phân mảnh Parquet đầu ra (`output_parsed_bytes`).

```{code-cell} ipython3
:tags: [remove-input]

from pathlib import Path
import json
import math
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


def _find_stats_dir() -> Path:
    for rel in ("stats/m2", "stats"):
        for candidate in (
            Path("..") / rel,
            Path(rel),
            *[parent / rel for parent in Path.cwd().parents],
        ):
            if (candidate / "m2_performance.json").is_file() or (candidate / "m2_papers_stats.csv").is_file():
                return candidate
    for rel in ("stats/m2", "stats"):
        for candidate in (
            Path("..") / rel,
            Path(rel),
            *[parent / rel for parent in Path.cwd().parents],
        ):
            if candidate.is_dir():
                return candidate
    return Path("../stats/m2")


STATS_DIR = _find_stats_dir()
HAS_M2_PERF = (STATS_DIR / "m2_performance.json").is_file()
HAS_M2_PAPERS_CSV = (STATS_DIR / "m2_papers_stats.csv").is_file()


def fmt_duration(sec: float) -> str:
    sec = float(sec or 0.0)
    if sec >= 3600:
        return f"{sec:,.1f} s ({sec / 3600:.2f} giờ)"
    if sec >= 60:
        return f"{sec:,.1f} s ({sec / 60:.2f} phút)"
    return f"{sec:,.2f} s"


def fmt_ms_or_s(ms: float) -> str:
    ms = float(ms or 0.0)
    if ms >= 1000.0:
        return f"{ms / 1000.0:,.2f} s"
    return f"{ms:,.1f} ms"


def fmt_storage(b: float) -> str:
    b = float(b or 0.0)
    if b >= 1024**3:
        return f"{b:,.0f} B ({b / 1024**3:.3f} GiB)"
    return f"{b:,.0f} B ({b / 1024**2:.2f} MiB)"


def show_table(df: pd.DataFrame, *, kv: bool = False) -> None:
    classes = "dataframe jb-stats-table jb-kv-table" if kv else "dataframe jb-stats-table"
    display(HTML(df.to_html(index=False, border=0, classes=classes)))


def show_pending_perf_m2_banner(section_desc: str) -> None:
    html = (
        '<div class="jb-pending-card">'
        '<div class="jb-pending-title">⚠️ Không tìm thấy <code>stats/m2/m2_performance.json</code> — Chưa thể nạp số đo thực nghiệm</div>'
        f"<div>{section_desc} cần tệp <code>m2_performance.json</code> trong thư mục <code>stats/m2/</code> để hiển thị bảng và biểu đồ thực tế.</div>"
        "</div>"
    )
    display(HTML(html))


if not HAS_M2_PERF:
    display(HTML(
        '<div class="admonition pending-stats">'
        '<p class="admonition-title">Thiếu tệp stats/m2/m2_performance.json</p>'
        '<p>Vui lòng kiểm tra lại vị trí tệp <code>m2_performance.json</code> và <code>m2_papers_stats.csv</code> trong <code>stats/m2/</code> trước khi biên dịch sách.</p>'
        '</div>'
    ))
```

---

## 8.2. Thời gian Thực thi Đầu–Cuối & Phân rã theo Chặng (Runtime Analysis)

```{code-cell} ipython3
:tags: [remove-input]

STAGE_KEYS = ("gather", "hierarchy", "bib", "dedup")
STAGE_LABELS = [
    "Thu thập & nối phẳng đa tệp\n(gather)",
    "Làm sạch, toán & cây phân cấp\n(hierarchy + clean/split)",
    "Trích xuất .bib / \\bibitem\n(bib)",
    "Khử trùng lặp 2 tầng\n(dedup)",
]

if HAS_M2_PERF:
    perf = json.loads((STATS_DIR / "m2_performance.json").read_text(encoding="utf-8"))
    st = perf.get("stage_seconds", {})
    wall_s = float(perf.get("wall_seconds") or 0.0)
    n_total = int(perf.get("papers_total") or 0)
    n_parsed = int(perf.get("papers_parsed") or 0)
    n_failed = int(perf.get("papers_failed") or 0)
    n_proc = max(n_parsed + n_failed, 1)
    ms_per_paper = float(perf.get("ms_per_paper") or (wall_s * 1000.0 / n_proc))
    sec_per_paper = float(perf.get("seconds_per_paper") or (wall_s / n_proc))
    workers = int(perf.get("workers") or 1)
    batch_sz = int(perf.get("batch_size") or 500)
    n_shards = math.ceil(n_total / max(batch_sz, 1)) if n_total > 0 else 0
    runs = int(perf.get("runs") or 1)
    last_run_at = str(perf.get("last_run_at") or "")
    stage_secs = [float(st.get(k, 0.0)) for k in STAGE_KEYS]
    total_cpu_s = sum(stage_secs)
    throughput = n_parsed / max(wall_s, 1e-6)
    speedup = total_cpu_s / max(wall_s, 1e-6)
    parallel_eff = speedup / max(workers, 1) * 100.0

    runtime_rows = [
        ("Dấu thời gian hoàn tất phiên chạy (last_run_at / runs)", f"{last_run_at} ({runs} phiên)"),
        ("Tổng thời gian thực đầu–cuối (wall_seconds)", fmt_duration(wall_s)),
        ("Số bài báo xử lý thành công / thất bại", f"{n_parsed:,} thành công / {n_failed:,} lỗi (tỷ lệ thành công {n_parsed / max(n_total, 1) * 100:.2f}%)"),
        ("Cấu hình song song & phân mảnh Parquet", f"{workers} worker · {batch_sz:,} bài / shard ({n_shards:,} shard / bảng)"),
        ("Độ trễ tường trung bình & thông lượng toàn cục", f"{ms_per_paper:,.2f} ms / bài ({sec_per_paper:.4f} s / bài · {throughput:.2f} bài/s)"),
        ("Tổng thời gian CPU tích lũy cả 4 chặng (4 stages)", fmt_duration(total_cpu_s)),
        ("Hệ số tăng tốc song song (Tổng CPU / Wall-time)", f"{speedup:.2f}× trên {workers} worker (hiệu suất {parallel_eff:.1f}%)"),
        ("CPU chặng 1 — Thu thập & nối phẳng đa tệp (gather)", f"{fmt_duration(stage_secs[0])} ({stage_secs[0] / max(total_cpu_s, 1e-6) * 100:.1f}%)"),
        ("CPU chặng 2 — Chuẩn hóa, dựng cây & tách câu (hierarchy)", f"{fmt_duration(stage_secs[1])} ({stage_secs[1] / max(total_cpu_s, 1e-6) * 100:.1f}%)"),
        ("CPU chặng 3 — Trích xuất BibTeX & \\bibitem (bib)", f"{fmt_duration(stage_secs[2])} ({stage_secs[2] / max(total_cpu_s, 1e-6) * 100:.1f}%)"),
        ("CPU chặng 4 — Khử trùng lặp 2 tầng (dedup)", f"{fmt_duration(stage_secs[3])} ({stage_secs[3] / max(total_cpu_s, 1e-6) * 100:.1f}%)"),
    ]
    show_table(pd.DataFrame(runtime_rows, columns=["Chỉ số hiệu năng thời gian (Mục 8.2)", "Giá trị đo đạc"]), kv=True)
    title_suffix = ""
else:
    show_pending_perf_m2_banner("Bảng chỉ số Runtime và biểu đồ phân rã thời gian 4 chặng tại Mục 8.2")
    wall_s = 0.0
    n_parsed = 0
    workers = 1
    batch_sz = 500
    ms_per_paper = 0.0
    stage_secs = [0.0, 0.0, 0.0, 0.0]
    title_suffix = " [THIẾU DỮ LIỆU]"

fig, ax = plt.subplots(figsize=(9.2, 3.45))
use_min = max(stage_secs + [0.0]) >= 120.0
scale = 60.0 if use_min else 1.0
unit_lbl = "Thời gian CPU tích lũy qua các worker (phút)" if use_min else "Thời gian CPU tích lũy (giây)"
vals = [s / scale for s in stage_secs]

bars = ax.barh(STAGE_LABELS, vals, color=["#4dabf7", "#1971c2", "#0b7285", "#2b8a3e"], height=0.56)
ax.invert_yaxis()
ax.set_xlabel(unit_lbl)
ax.set_title(f"Phân rã thời gian CPU tích lũy theo 4 chặng của bộ phân tích cú pháp{title_suffix}")
max_v = max(vals + [0.1])
tot_cpu = max(sum(stage_secs), 1e-6)
for b, sec in zip(bars, stage_secs):
    share = sec / tot_cpu * 100.0
    ax.text(
        b.get_width() + max_v * 0.018,
        b.get_y() + b.get_height() / 2,
        f"{fmt_duration(sec)} · {share:.1f}%",
        va="center",
        fontsize=8.4,
    )
ax.set_xlim(0, max_v * 1.48)
plt.tight_layout()
plt.show()
plt.close(fig)
```

```{code-cell} ipython3
:tags: [remove-input]

if HAS_M2_PAPERS_CSV:
    p_df = pd.read_csv(STATS_DIR / "m2_papers_stats.csv", dtype={"arxivid": str})
    for col in ("t_gather", "t_hierarchy", "t_bib", "t_dedup"):
        p_df[f"{col}_ms"] = pd.to_numeric(p_df[col], errors="coerce").fillna(0.0) * 1000.0
    p_df["t_total_ms"] = (
        p_df["t_gather_ms"] + p_df["t_hierarchy_ms"] + p_df["t_bib_ms"] + p_df["t_dedup_ms"]
    )

    stage_defs = [
        ("t_gather_ms", "Chặng 1: Thu thập & nối phẳng (gather)"),
        ("t_hierarchy_ms", "Chặng 2: Chuẩn hóa, cây & tách câu (hierarchy)"),
        ("t_bib_ms", "Chặng 3: Trích xuất .bib / \\bibitem (bib)"),
        ("t_dedup_ms", "Chặng 4: Khử trùng lặp 2 tầng (dedup)"),
        ("t_total_ms", "Tổng CPU cả 4 chặng trên mỗi bài báo"),
    ]
    q_rows = []
    for col, label in stage_defs:
        s = p_df[col]
        q_rows.append({
            "Chặng xử lý (từng bài báo)": label,
            "Trung bình": fmt_ms_or_s(s.mean()),
            "Trung vị (P50)": fmt_ms_or_s(s.median()),
            "P75": fmt_ms_or_s(s.quantile(0.75)),
            "P95": fmt_ms_or_s(s.quantile(0.95)),
            "P99": fmt_ms_or_s(s.quantile(0.99)),
            "Cực đại (Max)": fmt_ms_or_s(s.max()),
        })
    show_table(pd.DataFrame(q_rows))

    # Distribution plots: P99 clipped histogram + latency bucket breakdown
    fig, (ax_hist, ax_bkt) = plt.subplots(1, 2, figsize=(10.2, 3.7))
    t_ms = p_df["t_total_ms"]
    p99_ms = float(t_ms.quantile(0.99))
    med_ms = float(t_ms.median())
    mean_ms = float(t_ms.mean())
    clipped = t_ms[t_ms <= p99_ms]

    ax_hist.hist(clipped, bins=42, color="#1971c2", edgecolor="white", linewidth=0.45, alpha=0.90)
    ax_hist.axvline(med_ms, color="#2b8a3e", linestyle="--", linewidth=1.6)
    ax_hist.axvline(mean_ms, color="#d97706", linestyle=":", linewidth=1.7)
    _, y_top = ax_hist.get_ylim()
    ax_hist.text(
        med_ms + p99_ms * 0.02,
        y_top * 0.88,
        f"Trung vị: {med_ms:.1f} ms",
        color="#1e6b2d",
        fontsize=8.2,
        fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.22", facecolor="#f0fdf4", edgecolor="#86efac", alpha=0.95),
    )
    ax_hist.text(
        mean_ms + p99_ms * 0.02,
        y_top * 0.72,
        f"Trung bình: {mean_ms:.1f} ms",
        color="#b45309",
        fontsize=8.2,
        fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.22", facecolor="#fffbeb", edgecolor="#fcd34d", alpha=0.95),
    )
    ax_hist.set_xlabel("Thời gian CPU tích lũy mỗi bài báo (ms)")
    ax_hist.set_ylabel("Số bài báo")
    ax_hist.set_title(f"Phân phối độ trễ (cắt tại P99 = {p99_ms:,.0f} ms)", fontsize=10.3)

    buckets = [
        ("< 250 ms", (t_ms < 250.0).sum()),
        ("250–500 ms", ((t_ms >= 250.0) & (t_ms < 500.0)).sum()),
        ("0,5–1 s", ((t_ms >= 500.0) & (t_ms < 1000.0)).sum()),
        ("1–5 s", ((t_ms >= 1000.0) & (t_ms <= 5000.0)).sum()),
        ("> 5 s", (t_ms > 5000.0).sum()),
    ]
    b_labels = [b[0] for b in buckets]
    b_counts = [int(b[1]) for b in buckets]
    b_colors = ["#2b8a3e", "#37b24d", "#1971c2", "#f59f00", "#e03131"]
    bars_b = ax_bkt.bar(b_labels, b_counts, color=b_colors, width=0.56)
    max_bc = max(b_counts + [1])
    for bar, cnt in zip(bars_b, b_counts):
        pct = cnt / max(len(t_ms), 1) * 100.0
        ax_bkt.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max_bc * 0.022,
            f"{cnt:,}\n({pct:.1f}%)",
            ha="center",
            va="bottom",
            fontsize=8.1,
            fontweight="bold",
        )
    ax_bkt.set_ylim(0, max_bc * 1.24)
    ax_bkt.set_ylabel("Số bài báo")
    ax_bkt.set_xlabel("Nhóm thời gian CPU tích lũy mỗi bài")
    ax_bkt.set_title("Phân tầng tốc độ xử lý (25.000 bài báo)", fontsize=10.3)
    plt.tight_layout(w_pad=2.2)
    plt.show()
    plt.close(fig)

    # Top-5 slowest papers highlighting empirical heavy tail
    top5 = p_df.sort_values("t_total_ms", ascending=False).head(5)
    top_rows = []
    bib_raw_col = next((c for c in ("n_bib_raw", "n_bibs_raw", "bib_raw") if c in p_df.columns), None)
    ver_col = next((c for c in ("n_versions", "versions") if c in p_df.columns), None)
    elem_col = next((c for c in ("n_elements", "elements") if c in p_df.columns), None)
    for _, r in top5.iterrows():
        row_d = {"arXiv ID": str(r["arxivid"])}
        if ver_col:
            row_d["Phiên bản"] = f"{int(r[ver_col]):,}"
        if elem_col:
            row_d["Elements"] = f"{int(r[elem_col]):,}"
        if bib_raw_col:
            row_d["BibTeX thô"] = f"{int(r[bib_raw_col]):,}"
        row_d["gather"] = fmt_ms_or_s(r["t_gather_ms"])
        row_d["hierarchy"] = fmt_ms_or_s(r["t_hierarchy_ms"])
        row_d["bib"] = fmt_ms_or_s(r["t_bib_ms"])
        row_d["dedup"] = fmt_ms_or_s(r["t_dedup_ms"])
        row_d["Tổng CPU"] = fmt_ms_or_s(r["t_total_ms"])
        top_rows.append(row_d)
    show_table(pd.DataFrame(top_rows))
```

**Phân tích đặc tính thời gian chạy của bộ phân tích cú pháp:**

- **Khác biệt bản chất giữa Milestone 1 (I/O-bound mạng) và Milestone 2 (CPU-bound thuần nội bộ):** Trong khi Milestone 1 mất **`242.271,31 s` (`67,30 giờ`)** do bị chặn bởi độ trễ tải mạng và khoảng nghỉ lịch sự giữa các truy vấn, toàn bộ Milestone 2 đọc trực tiếp cây tệp giải nén từ đĩa cục bộ mà không phát sinh kết nối mạng. Nhờ biên dịch trước biểu thức chính quy ở mức module (`re.compile`), quét trạng thái tuyến tính và song song hóa **`12` worker** qua `ProcessPoolExecutor`, thời gian thực đầu–cuối chỉ còn **`1.688,11 s` (`28,14 phút`)** — nhanh gấp **`~143,5×`** về wall-clock so với giai đoạn thu thập M1 (`67,52 ms/bài`, thông lượng **`14,81 bài/s`** hay ~`24,66 phiên bản/s`). Tổng thời gian CPU cộng dồn của 4 chặng đạt **`19.579,12 s` (`5,44 giờ CPU`)**, tương ứng hệ số tăng tốc song song **`11,60×`** trên `12` worker (**hiệu suất song song `96,7%`**).
- **Đường găng CPU tập trung ở `hierarchy` (`49,3%`) và `gather` (`32,0%`):** Chặng `hierarchy` (`9.653,9 s` CPU — làm sạch chuỗi, chuẩn hóa công thức toán, dựng cây ngăn xếp và tách câu ngữ cảnh) cùng `gather` (`6.268,3 s` CPU — duyệt tệp, khử chú thích và nối phẳng `\input`/`\include`) chiếm **`81,3%`** tổng thời gian CPU vì phải quét toàn bộ độ dài mã nguồn `.tex` của cả `38.735` phiên bản có TeX. Ngược lại, `bib` (`1.936,5 s`, `9,9%`) và `dedup` (`1.720,4 s`, `8,8%`) chỉ chiếm dưới một phần năm tổng chi phí CPU.
- **Phân phối độ trễ lệch phải mạnh ở cấp bài báo:** Trên `25.000` bài, trung vị thời gian CPU mỗi bài chỉ là **`461,4 ms`** (Q25 = `248,0 ms`, Q75 = `898,6 ms`), và **`99,0%` bài báo hoàn tất CPU trong `≤ 4,95 s`** (P95 = `2,34 s`; chỉ `244` bài `> 5 s` và `58` bài `> 10 s`). Nhóm đuôi nặng cực đoan trong bảng Top-5 minh chứng trực tiếp hai cơ chế gây tải mà Chương 6 đã cảnh báo: cặp ngoại lệ `2408.01285` (`189,96 s`, trong đó `dedup = 163,68 s`) và `2408.09430` (`140,47 s`, trong đó `dedup = 120,34 s`) phát sinh chi phí gom cụm bậc hai $\mathcal{O}(R^2)$ trên hơn `90.000` mục `.bib` thô mỗi bài, còn `2406.11779` (`93,65 s`, với `gather = 51,40 s` và `hierarchy = 38,53 s`) chịu chi phí I/O/cú pháp của `14` phiên bản và `2.245` tệp `.tex`.

---

## 8.3. Mức Sử dụng Bộ nhớ RAM & Hiệu quả Lưu trữ Sharded Parquet

```{code-cell} ipython3
:tags: [remove-input]

if HAS_M2_PERF:
    res = perf.get("resources", {})
    ram_peak_b = float(res.get("ram_peak_bytes") or (float(perf.get("ram_peak_mb") or 0.0) * 1e6))
    ram_mean_b = float(res.get("ram_mean_bytes") or (float(perf.get("ram_mean_mb") or 0.0) * 1e6))
    ram_samples = int(res.get("ram_samples") or 0)
    in_bytes = float(perf.get("input_corpus_bytes") or 0.0)
    out_bytes = float(perf.get("output_parsed_bytes") or res.get("disk_final_bytes") or 0.0)
    disk_peak_b = float(res.get("disk_peak_bytes") or out_bytes)
    ram_per_worker_mib = (ram_peak_b / 1024**2) / max(workers, 1)
    out_pct = out_bytes / max(in_bytes, 1.0) * 100.0
    comp_ratio = in_bytes / max(out_bytes, 1.0)

    mem_rows = [
        ("Đỉnh bộ nhớ vật lý toàn hệ thống kể cả worker con (ram_peak_bytes)", fmt_storage(ram_peak_b).replace("GiB)", f"GiB · {ram_peak_b / 1024**2:,.2f} MiB)")),
        ("Mức tiêu thụ RAM trung bình toàn phiên (ram_mean_bytes)", fmt_storage(ram_mean_b).replace("GiB)", f"GiB · {ram_mean_b / 1024**2:,.2f} MiB)")),
        (f"Peak RSS bình quân quy về mỗi worker ({workers} worker)", f"~{ram_per_worker_mib:,.1f} MiB / worker"),
        ("Tổng số mẫu đo RAM định kỳ đã thu thập (ram_samples)", f"{ram_samples:,} mẫu"),
        ("Dung lượng kho nguồn .tex/.bib đầu vào từ Milestone 1 (input_corpus_bytes)", fmt_storage(in_bytes)),
        ("Dung lượng 3 bảng Sharded Parquet đầu ra (output_parsed_bytes)", fmt_storage(out_bytes)),
        ("Đỉnh dung lượng đĩa đầu ra ghi nhận trong phiên (disk_peak_bytes)", fmt_storage(disk_peak_b)),
        ("Tỷ lệ dung lượng Parquet đầu ra so với kho nguồn & hệ số thu gọn", f"{out_pct:.2f}% (thu gọn {comp_ratio:.2f}×)"),
    ]
    show_table(pd.DataFrame(mem_rows, columns=["Chỉ số bộ nhớ RAM & lưu trữ đĩa (Mục 8.3)", "Giá trị đo đạc"]), kv=True)
else:
    show_pending_perf_m2_banner("Bảng chỉ số RAM/Đĩa và cặp biểu đồ đối chiếu tại Mục 8.3")
    ram_mean_b = 0.0
    ram_peak_b = 0.0
    in_bytes = 0.0
    out_bytes = 0.0

fig, (ax_ram, ax_disk) = plt.subplots(1, 2, figsize=(9.8, 3.55))

ram_mib = [ram_mean_b / 1024**2, ram_peak_b / 1024**2]
b_r = ax_ram.bar(["RAM Trung bình\n(Mean RSS)", "RAM Tối đa\n(Peak RSS)"], ram_mib, color=["#339af0", "#1864ab"], width=0.45)
ax_ram.set_ylabel("Bộ nhớ vật lý RSS (MiB)")
ax_ram.set_title(f"Tiêu thụ RAM (tiến trình chính + {workers} worker){title_suffix}")
top_r = max(ram_mib + [50.0])
for bar, v in zip(b_r, ram_mib):
    ax_ram.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height() + top_r * 0.025,
        f"{v:,.1f} MiB\n({v / 1024:.2f} GiB)",
        ha="center",
        fontsize=8.4,
        fontweight="bold",
    )
ax_ram.set_ylim(0, top_r * 1.26)

use_gib = max(in_bytes, out_bytes) >= 1024**3
d_scale = 1024**3 if use_gib else 1024**2
d_unit = "GiB" if use_gib else "MiB"
d_vals = [in_bytes / d_scale, out_bytes / d_scale]
b_d = ax_disk.bar(
    ["Kho nguồn đầu vào\n(.tex / .bib giải nén)", "3 bảng Sharded Parquet\n(đầu ra M2)"],
    d_vals,
    color=["#94a3b8", "#2b8a3e"],
    width=0.45,
)
ax_disk.set_ylabel(f"Dung lượng lưu trữ ({d_unit})")
ax_disk.set_title(f"Đối chiếu lưu trữ Đầu vào vs. Parquet{title_suffix}")
top_d = max(d_vals + [0.1])
for idx, (bar, v) in enumerate(zip(b_d, d_vals)):
    lbl = f"{v:.2f} {d_unit}"
    if idx == 1 and in_bytes > 0:
        lbl = f"{out_bytes / 1024**2:.1f} MiB\n({out_bytes / in_bytes * 100:.2f}% đầu vào)"
    ax_disk.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height() + top_d * 0.025,
        lbl,
        ha="center",
        fontsize=8.4,
        fontweight="bold",
    )
ax_disk.set_ylim(0, top_d * 1.24)

plt.tight_layout()
plt.show()
plt.close(fig)
```

**Ba kỹ thuật kiểm soát bộ nhớ và tối ưu hóa dung lượng đầu ra Parquet:**

1. **Xả phân mảnh định kỳ theo lô `500` bài (`Streaming Sharded Parquet`):** Tổng lượng dữ liệu đầu ra trên `25.000` bài báo lên tới **`38.787.282` dòng** (`14.880.359` nút `elements`, `22.516.391` cạnh `hierarchy` và `1.390.532` bản ghi `bibtex`). Cơ chế `flush()` sau mỗi `500` bài báo (`50` shard/bảng) kết hợp `chunksize = 1` trên `ProcessPoolExecutor` và thu gom rác chủ động (`gc.collect()`) giữ biên bộ nhớ ổn định ở quy mô lô thay vì tích lũy toàn tập: tổng RSS trên cả tiến trình điều phối lẫn **`12` worker** đạt trung bình **`2.377,68 MiB` (`2,322 GiB`)** và đỉnh **`4.028,20 MiB` (`3,934 GiB`, bình quân ~`335,7 MiB/worker`)** xuyên suốt `1.648` mẫu đo.
2. **Mã hóa từ điển (`Dictionary Encoding`) cho các cột phân loại lặp lại:** Hai cột `elements.kind` (8 nhãn lặp lại hàng triệu lần) và `bibtex.entrytype` được lưu bằng kiểu `pa.dictionary(pa.int8(), pa.string())`, thay thế hàng triệu chuỗi ký tự lặp bằng chỉ số nguyên 1 byte ngay ở tầng cột nhị phân.
3. **Cộng hưởng giữa khử trùng lặp xuyên phiên bản và lưu trữ cột Apache Parquet:** Việc chỉ lưu một bản sao duy nhất cho mỗi phần tử nội dung không đổi qua $v_1 \dots v_N$ (`-34,90%` phần tử văn bản và `-57,76%` bản ghi BibTeX) kết hợp định dạng cột nhị phân của Apache Parquet (PyArrow) giúp nén **`23,550 GiB`** mã nguồn `.tex`/`.bib` đầu vào xuống còn **`898,48 MiB` (`0,877 GiB`, chỉ `3,73%` dung lượng gốc — hệ số thu gọn `26,84×`)**, sẵn sàng cho việc đọc chiếu cột (*column projection*) với thông lượng cao ở Milestone 3.

---

(m2-tai-lieu-tham-khao)=
## Tài liệu Tham khảo (Milestone 2)

1. Mittelbach, F., & Goossens, M. (2004). *The LaTeX Companion* (2nd ed.). Addison-Wesley Professional.
2. Patashnik, O. (1988). *BibTeXing — Documentation for General BibTeX Users*. CTAN Bibliography Documentation. <https://ctan.org/pkg/bibtex>
3. Apache Arrow Community. *PyArrow Parquet Columnar Format & Dictionary Encoding Documentation*. <https://arrow.apache.org/docs/python/parquet.html>
4. Clement, C. B., Bierbaum, M., O'Keeffe, K. P., & Alemi, A. A. (2019). *On the Use of ArXiv as a Dataset*. arXiv:1905.00075.
5. Lo, K., Wang, L. L., Neumann, M., Kinney, R., & Weld, D. (2020). *S2ORC: The Semantic Scholar Open Research Corpus*. In *Proceedings of ACL 2020* (pp. 4969–4983).
