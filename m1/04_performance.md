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

# Chương 4. Đánh giá Hiệu năng Bộ Thu thập

```{admonition} Phạm vi số đo hiệu năng: Toàn bộ 25.000 Định danh (38 Lượt chạy tích lũy)
:class: note
Toàn bộ số đo hiệu năng thời gian thực thi (Runtime), bộ nhớ RAM RSS và dung lượng đĩa dưới đây được đo đạc tự động bằng luồng `ResourceSampler` và `time.perf_counter()` trên **toàn bộ 25.000 ID (5 dải dữ liệu)** với **38 phiên chạy tích lũy** hợp nhất từ **32 session logs** (từ lượt chạy 7 đến lượt chạy 38, chủ yếu trên **Google Colab CPU 2 vCPU, Python 3.13.18** ở các lượt 13–33 và hoàn thiện cuối trên **Google Colab 12 CPU, Python 3.13.16** ở các lượt 34–38).
```

## 4.1. Môi trường Kiểm thử & Phương pháp Đo lường Kiểm chứng

Theo đúng quy chuẩn đánh giá hiệu năng của đề bài, phần lớn quá trình thu thập được vận hành và đo đạc trên máy chuẩn chạy ở chế độ chỉ CPU (Standard CPU-only Runtime, tương thích môi trường Google Colab CPU 2 vCPU, 12,7 GiB RAM):

- **Cấu hình hệ thống chuẩn:** Hệ điều hành Linux x86_64 / Windows, vi xử lý ảo hóa Intel Xeon CPU, bộ nhớ RAM khả dụng $\ge 12\text{ GiB}$, ổ đĩa SSD cục bộ, môi trường Python `3.11+` (đo đạc chính thức trên Colab với Python `3.13`).
- **Phương pháp đo lường kiểm chứng chuyên sâu (`metrics.py` $\rightarrow$ `stats/performance.json`):**
  1. *Thời gian thực thi (Wall-clock Runtime):* Được đo bằng đồng hồ đơn điệu độ phân giải cao `time.perf_counter()` bao quanh các chặng (`discovery`, `download`, `extract`, `s2`) và ghi nhận độc lập theo từng phiên chạy (`sessions`). Bộ tổng hợp đa phiên `summarize_sessions()` tự động loại bỏ khoảng thời gian chết giữa các phiên (`idle_gap_seconds`), bóc tách minh bạch **thời gian xử lý thực (`active_wall_seconds`)** và **thời gian chờ phạt / cooldown (`cooldown_retry_seconds`)**. Tổng thời gian thực đầu–cuối của toàn hệ thống được xác định bởi đường găng $\max(T_{\text{arXiv}}, T_{\text{S2}})$.
  2. *Bộ nhớ RAM & Lưu trữ đĩa $O(1)$:* Luồng daemon nền `ResourceSampler` sử dụng thư viện `psutil` lấy mẫu định kỳ mỗi **5 giây** tổng bộ nhớ vật lý thường trú (`RSS`) của tiến trình chính cùng toàn bộ tiến trình con, cho phép truy xuất cực trị $O(1)$ mà không tốn chi phí quét cây tiến trình trên luồng chính. Dung lượng thư mục làm việc được quét định kỳ mỗi **300 giây** và ngay thời điểm kết thúc bằng `os.scandir()` để xác định dung lượng đĩa tối đa (`disk_peak_bytes`) và đầu ra cuối cùng (`disk_final_bytes`).

---

## 4.2. Thời gian Chạy Hệ thống (Runtime Analysis)

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
REQUIRED_PERF_FILES = ("performance.json", "summary.json")
MISSING_PERF_FILES = [
    name for name in REQUIRED_PERF_FILES if not (STATS_DIR / name).is_file()
]
HAS_PERF = len(MISSING_PERF_FILES) == 0


def show_table(df: pd.DataFrame, *, kv: bool = False) -> None:
    classes = "dataframe jb-stats-table jb-kv-table" if kv else "dataframe jb-stats-table"
    display(HTML(df.to_html(index=False, border=0, classes=classes)))


def show_pending_perf_box(section_desc: str, preview_df: pd.DataFrame | None = None) -> None:
    missing_html = ", ".join(f"<code>stats/{name}</code>" for name in MISSING_PERF_FILES)
    html = (
        '<div class="jb-pending-card">'
        '<div class="jb-pending-title">⏳ Đang chờ tệp đo hiệu năng trong thư mục <code>arxiv-book/stats/</code></div>'
        f"<div>Hiện chưa tìm thấy: {missing_html}. "
        f"{section_desc} sẽ <strong>tự động sinh đầy đủ</strong> ngay khi chép tệp "
        "<code>performance.json</code> và <code>summary.json</code> từ Colab CPU vào "
        "<code>arxiv-book/stats/</code> và biên dịch lại sách.</div>"
        "</div>"
    )
    display(HTML(html))
    if preview_df is not None:
        show_table(preview_df, kv=True)


def fmt_duration(sec):
    sec = float(sec or 0.0)
    if sec >= 3600:
        return f"{sec:,.1f} s ({sec / 3600:.2f} giờ)"
    if sec >= 60:
        return f"{sec:,.1f} s ({sec / 60:.2f} phút)"
    return f"{sec:,.2f} s"


if HAS_PERF:
    perf = json.loads((STATS_DIR / "performance.json").read_text(encoding="utf-8"))
    summary = json.loads((STATS_DIR / "summary.json").read_text(encoding="utf-8"))

    st = perf.get("stage_seconds", {})
    s2_info = perf.get("s2", {})
    arxiv_wall_s = (
        float(st.get("discovery", 0.0))
        + float(st.get("download", 0.0))
        + float(st.get("extract", 0.0))
    )
    s2_total_s = float(st.get("s2", 0.0)) + float(s2_info.get("retry_wait_seconds", 0.0))
    wall_end_to_end_s = max(arxiv_wall_s, s2_total_s)

    n_req = max(int(summary.get("ids_requested") or 0), 1)
    n_pap = max(int(summary.get("papers_total") or 0), 1)
    n_pair = max(int(summary.get("pairs_total") or 0), 1)

    runtime_rows = [
        ("Tổng thời gian thực đầu–cuối hệ thống (End-to-End Wall Time)", fmt_duration(wall_end_to_end_s)),
        ("Tổng thời gian cho việc khám phá bài báo (discovery — Snapshot / Atom API)", fmt_duration(st.get("discovery", 0.0))),
        ("Tổng thời gian tải gói nguồn + chờ nhịp lịch sự arXiv (download)", fmt_duration(st.get("download", 0.0))),
        ("Tổng thời gian giải nén & lọc .tex/.bib + băm SHA-256 (extract)", fmt_duration(st.get("extract", 0.0))),
        ("Thời gian hoạt động luồng nền Semantic Scholar (s2 — chạy song song)", fmt_duration(st.get("s2", 0.0))),
        ("Thời gian chờ backoff HTTP 429 trên luồng S2 (retry_wait_seconds)", fmt_duration(s2_info.get("retry_wait_seconds", 0.0))),
        ("Số lô truy vấn S2 Batch đã thực hiện", f"{int(s2_info.get('batches', 0)):,} lô"),
        ("Thời gian TB xử lý mỗi bài báo được yêu cầu (wall / ids_requested)", f"{wall_end_to_end_s / n_req:.2f} giây / ID"),
        ("Thời gian TB xử lý một bài báo tồn tại (wall / papers_total)", f"{wall_end_to_end_s / n_pap:.2f} giây / bài"),
        ("Thời gian TB xử lý một phiên bản bài báo (wall / pairs_total)", f"{wall_end_to_end_s / n_pair:.2f} giây / phiên bản"),
        ("Tổng số phiên chạy cộng dồn (runs)", f"{int(perf.get('runs', 1))} phiên"),
    ]
    show_table(pd.DataFrame(runtime_rows, columns=["Chỉ số thời gian chạy (Runtime)", "Giá trị đo đạc"]), kv=True)

    stage_labels = [
        "Khám phá bài báo\n(discovery)",
        "Tải nguồn + chờ nhịp\n(download)",
        "Giải nén & lọc TeX\n(extract)",
        "Tham khảo S2\n(luồng nền song song)",
    ]
    stage_secs = [float(st.get(k, 0.0)) for k in ("discovery", "download", "extract", "s2")]
    use_hours = max(stage_secs, default=0.0) >= 3600
    scale = 3600.0 if use_hours else 1.0
    unit_lbl = "Thời gian tích lũy (giờ)" if use_hours else "Thời gian tích lũy (giây)"
    stage_vals = [s / scale for s in stage_secs]

    fig, ax = plt.subplots(figsize=(8.6, 3.2))
    bars = ax.barh(stage_labels, stage_vals, color=["#4dabf7", "#1971c2", "#2b8a3e", "#f59f00"])
    ax.invert_yaxis()
    ax.set_xlabel(unit_lbl)
    ax.set_title("Phân rã thời gian hoạt động chủ động theo từng chặng")
    max_v = max(stage_vals) if max(stage_vals) > 0 else 1.0
    for b, sec in zip(bars, stage_secs):
        ax.text(
            b.get_width() + max_v * 0.02,
            b.get_y() + b.get_height() / 2,
            fmt_duration(sec),
            va="center",
            fontsize=8.5,
        )
    ax.set_xlim(0, max_v * 1.40)
    plt.tight_layout()
    plt.show()
    plt.close(fig)
else:
    runtime_preview = pd.DataFrame(
        [
            ("Tổng thời gian thực đầu–cuối hệ thống (End-to-End Wall Time)", "⏳ Chờ stats/performance.json (Cận dưới lý thuyết ~47.1 giờ ở nhịp 3.5s)"),
            ("Tổng thời gian khám phá bài báo (discovery — Snapshot / Atom API)", "⏳ Chờ stats/performance.json"),
            ("Tổng thời gian tải nguồn + chờ nhịp lịch sự arXiv (download)", "⏳ Chờ stats/performance.json"),
            ("Tổng thời gian giải nén & lọc .tex/.bib + SHA-256 (extract)", "⏳ Chờ stats/performance.json"),
            ("Thời gian hoạt động luồng nền Semantic Scholar (s2)", "⏳ Chờ stats/performance.json"),
            ("Thời gian TB xử lý mỗi bài báo được yêu cầu (wall / ids_requested)", "⏳ Chờ stats/performance.json & summary.json"),
        ],
        columns=["Chỉ số thời gian chạy cần báo cáo (Mục 4.2)", "Trạng thái dữ liệu"],
    )
    show_pending_perf_box("Bảng 11 chỉ số Runtime và biểu đồ phân rã thời gian 4 chặng tại Mục 4.2", runtime_preview)
```

**Phân tích hiệu năng thời gian:**

- **Đối chiếu cận dưới lý thuyết điều nhịp (*Rate-limit bound*) với kiến trúc Start-to-Start:**
  Theo chính sách lịch sự của arXiv, giữa hai request liên tiếp tới `export.arxiv.org` phải cách nhau tối thiểu $\Delta t \ge 3{,}00\text{ s}$ trên 1 kết nối duy nhất. Trong kiến trúc **Producer–Consumer Start-to-Start** với nhịp cơ sở $3{,}15\text{ s} + \text{jitter}$, trên toàn bộ **25.000 ID** với tổng cộng **$R = 41.629$ phiên bản** (hệ số $\bar{V} = 1{,}67$), cận dưới lý thuyết chỉ riêng cho công đoạn tải gói nguồn arXiv là:

  $$
  T_{\text{floor, min}} \approx 41.629 \times 3{,}00\text{ s} \approx 124.887\text{ s} \approx 34{,}69\text{ giờ} \quad (\text{hoặc } \approx 131.131\text{ s} \approx 36{,}43\text{ giờ ở nhịp } 3{,}15\text{ s})
  $$

  Nhờ nhịp **Start-to-Start** và việc tách giải nén sang pool `extract-worker` (`2.393,82 s` giải nén cho toàn tập), thao tác giải nén diễn ra song song trong cửa sổ điều nhịp mà không chặn vòng lặp tải chính; đồng thời giai đoạn khám phá siêu dữ liệu (`discovery`) chỉ tiêu tốn **$598{,}48\text{ s}$ (~9,97 phút)**.
- **Hiệu quả thực thi song song & tách pha của Semantic Scholar:** Khối làm giàu trích dẫn Semantic Scholar thực hiện tổng cộng **2.077 lượt truy vấn lô** (`POST /graph/v1/paper/batch`, sử dụng kích thước lô 25 bài kết hợp cơ chế chia đôi lô Bisection khi gặp 413/5xx ở kiến trúc chuẩn hóa mới nhất). Thời gian hoạt động thuần túy của khối S2 là **$8.842{,}14\text{ s}$ (~2,46 giờ)** và tổng thời gian chờ backoff/retry qua **2.592 lượt HTTP 429** là **$83.745{,}00\text{ s}$ (~23,26 giờ)**, tạo thành tổng thời gian khối S2 **$92.587{,}14\text{ s}$ (~25,72 giờ)**. Mức thời gian này vẫn thấp hơn nhiều so với đường găng arXiv (**67,30 giờ**), xác nhận luồng S2 không làm tăng tổng thời gian đầu–cuối khi vận hành song song hoặc tách pha `--s2-only`.
- **Đánh giá tổng thời gian chạy thực tế trên toàn bộ 25.000 ID:**
  - Tổng thời gian đường găng đầu–cuối (**End-to-End Wall Time** theo khối arXiv `discovery + download + extract`) đạt **242.271,31 s (~67,30 giờ)**, trong đó `download` chiếm **239.279,01 s (~66,47 giờ)**. Độ dôi ra so với sàn điều nhịp $36{,}43\text{ giờ}$ chủ yếu đến từ lưu lượng tải các gói nguồn nén kích thước lớn (trung bình 7,10 MiB/bài), **311 lần HTTP 429** với **36.690,0 s (~10,19 giờ)** cooldown hồi phục, **96 lượt tản nhiệt định kỳ** ở các phiên chạy trước v3.10+, **344 lượt nối tải Range Resume** và cơ chế điều tiết **Proportional Bandwidth Breather**.
  - Tốc độ xử lý trung bình toàn cục đạt **9,69 giây / ID** (hay **9,69 giây / bài báo**) và **5,82 giây / phiên bản** trên tổng số **41.629 phiên bản**.
  - Quá trình thu thập đã vượt qua **38 phiên chạy tích lũy** (`runs = 38`) với **371 lần tự động khôi phục (`auto_resumes = 371`)** và **344 lần Range Resume tại chỗ (`range_resumes = 344`)** một cách liền mạch qua SQLite WAL manifest.

---

## 4.3. Mức Sử dụng Bộ nhớ RAM & Dung lượng Lưu trữ Đĩa

```{code-cell} ipython3
:tags: [remove-input]

def fmt_storage(b):
    if b >= 1024**3:
        return f"{b:,.0f} B ({b / 1024**3:.3f} GiB)"
    return f"{b:,.0f} B ({b / 1024**2:.2f} MiB)"


if HAS_PERF:
    res = perf.get("resources", {})
    ram_mean = float(res.get("ram_mean_bytes") or 0.0)
    ram_peak = float(res.get("ram_peak_bytes") or 0.0)
    disk_peak = float(res.get("disk_peak_bytes") or 0.0)
    disk_final = float(res.get("disk_final_bytes") or 0.0)

    mem_disk_rows = [
        ("Lượng RAM tối đa dùng trong quá trình thu thập (ram_peak_bytes)", f"{ram_peak:,.0f} B ({ram_peak / 1024**2:.2f} MiB)"),
        ("Mức tiêu thụ RAM trung bình (ram_mean_bytes — lấy mẫu 5s/lần)", f"{ram_mean:,.0f} B ({ram_mean / 1024**2:.2f} MiB)"),
        ("Tổng số mẫu đo RAM định kỳ đã thu thập (ram_samples)", f"{int(res.get('ram_samples') or 0):,} mẫu"),
        ("Dung lượng lưu trữ đĩa tối đa cần thiết (disk_peak_bytes)", fmt_storage(disk_peak)),
        ("Dung lượng lưu trữ của đầu ra cuối cùng (disk_final_bytes)", fmt_storage(disk_final)),
    ]
    show_table(
        pd.DataFrame(mem_disk_rows, columns=["Chỉ số bộ nhớ & lưu trữ (psutil + quét đĩa)", "Giá trị đo đạc"]),
        kv=True,
    )

    fig, (ax_ram, ax_disk) = plt.subplots(1, 2, figsize=(9.6, 3.3))

    ram_vals = [ram_mean / 1024**2, ram_peak / 1024**2]
    b1 = ax_ram.bar(
        ["RAM Trung bình", "RAM Tối đa (Peak)"],
        ram_vals,
        color=["#339af0", "#1864ab"],
        width=0.45,
    )
    ax_ram.set_ylabel("Bộ nhớ vật lý RSS (MiB)")
    ax_ram.set_title("Mức tiêu thụ RAM toàn hệ thống")
    for b, v in zip(b1, ram_vals):
        ax_ram.text(
            b.get_x() + b.get_width() / 2,
            b.get_height() * 1.03,
            f"{v:.2f} MiB",
            ha="center",
            fontweight="bold",
            fontsize=9,
        )
    ax_ram.set_ylim(0, max(ram_vals) * 1.25 if max(ram_vals) > 0 else 100)

    use_gib = max(disk_peak, disk_final) >= 1024**3
    d_scale = 1024**3 if use_gib else 1024**2
    d_unit = "GiB" if use_gib else "MiB"
    disk_vals = [disk_peak / d_scale, disk_final / d_scale]
    b2 = ax_disk.bar(
        ["Đĩa Tối đa (Peak)", "Đầu ra Cuối cùng (Final)"],
        disk_vals,
        color=["#fcc419", "#2b8a3e"],
        width=0.45,
    )
    ax_disk.set_ylabel(f"Dung lượng lưu trữ ({d_unit})")
    ax_disk.set_title("Mức sử dụng dung lượng ổ đĩa")
    for b, v in zip(b2, disk_vals):
        ax_disk.text(
            b.get_x() + b.get_width() / 2,
            b.get_height() * 1.03,
            f"{v:.2f} {d_unit}",
            ha="center",
            fontweight="bold",
            fontsize=9,
        )
    ax_disk.set_ylim(0, max(disk_vals) * 1.25 if max(disk_vals) > 0 else 100)

    plt.tight_layout()
    plt.show()
    plt.close(fig)
else:
    mem_preview = pd.DataFrame(
        [
            ("Lượng RAM tối đa (ram_peak_bytes)", "⏳ Chờ stats/performance.json (Pilot: 41,234,432 B — 39.32 MiB)"),
            ("Mức tiêu thụ RAM trung bình (ram_mean_bytes)", "⏳ Chờ stats/performance.json (Pilot: 40,595,351 B — 38.71 MiB)"),
            ("Dung lượng lưu trữ đĩa tối đa (disk_peak_bytes)", "⏳ Chờ stats/performance.json (Pilot 30 ID: 8.04 MiB)"),
            ("Dung lượng lưu trữ đầu ra cuối cùng (disk_final_bytes)", "⏳ Chờ stats/performance.json (Pilot 30 ID: 8.04 MiB)"),
        ],
        columns=["Chỉ số bộ nhớ & lưu trữ (Mục 4.3)", "Trạng thái / Đối chiếu Pilot 30 ID"],
    )
    show_pending_perf_box("Bảng 5 chỉ số RAM/Đĩa và cặp biểu đồ so sánh tại Mục 4.3", mem_preview)
```

**Phân tích hiệu quả sử dụng bộ nhớ và lưu trữ:**

- **Độ phức tạp không gian bộ nhớ $\mathcal{O}(1)$ được kiểm soát chặt chẽ:** Nhờ kỹ thuật đệm RAM Zero-Copy $\le 96\text{ MiB}$ (chỉ tràn sang đĩa tạm nếu gói khổng lồ $> 96\text{ MiB}$), kết hợp van điều tiết hàng đợi `extract_max_queue_bytes = 192 MiB`, tiến trình không bao giờ bị phình to RAM khi gặp chuỗi gói nặng liên tiếp. Bộ nhớ thường trú RSS được luồng daemon `ResourceSampler` theo dõi định kỳ mỗi 5 giây, bảo đảm an toàn tuyệt đối cho môi trường máy ảo.
- **Tối ưu hóa dung lượng đĩa và bảo vệ dữ liệu:** Bộ giải nén 1-pass `_FastGzipStream` 512 KiB loại bỏ toàn bộ hình ảnh nhị phân ngay trên luồng, chỉ ghi các tệp `.tex`, `.bib` và `.bbl`. Cùng với cơ chế sao lưu nền `arxiv-data.tar.gz` có kiểm tra chống tụt lùi dữ liệu (`shrink guard`) và bỏ qua nén khi dữ liệu không đổi (`skip_if_unchanged=True`), hệ thống bảo đảm an toàn dữ liệu 100% trong suốt quá trình vận hành liên tục.
- **Đánh giá số đo thực nghiệm trên toàn bộ 25.000 ID:**
  - **Bộ nhớ RAM thường trú (RSS):** Mức tiêu thụ RAM trung bình thực tế chỉ là **195,18 MiB** và đỉnh RAM tối đa đạt **362,88 MiB** trên tổng số **60.774 mẫu** lấy định kỳ. Con số này chiếm chưa tới **3%** dung lượng RAM khả dụng (`12,7 GiB`) của Google Colab CPU chuẩn, hoàn toàn loại bỏ nguy cơ bị máy ảo buộc dừng do lỗi tràn bộ nhớ (*Out-Of-Memory*).
  - **Dung lượng lưu trữ đĩa:** Cả đỉnh lưu trữ trong quá trình chạy lẫn dung lượng đầu ra cuối cùng sau khi hoàn tất đều đạt **23,686 GiB** (**24.254,81 MiB** / **25.433.014.346 B**), không phát sinh dư thừa tệp tạm trên đĩa. Toàn bộ kho ngữ liệu **25.000 bài báo đa phiên bản** (**41.629 phiên bản**) được gói gọn an toàn ở mức ~23,7 GiB đĩa.

---

(tai-lieu-tham-khao)=
## Tài liệu Tham khảo

1. arXiv.org. *arXiv API User's Manual & Basics*. <https://info.arxiv.org/help/api/user-manual.html>
2. arXiv.org. *Terms of Use for arXiv APIs*. <https://info.arxiv.org/help/api/tou.html>
3. arXiv.org. *Open Archives Initiative (OAI-PMH) & Bulk Data Access*. <https://info.arxiv.org/help/oa/index.html>
4. arXiv.org. *Why Submit the TeX/LaTeX Source? & Media Types*. <https://info.arxiv.org/help/faq/whytex.html>
5. Ginev, D., et al. (2024). *HTML papers on arXiv — why it is important, and how we made it happen*. arXiv:2402.08954.
6. Allen Institute for AI (AI2). *Semantic Scholar Academic Graph API Documentation*. <https://api.semanticscholar.org/api-docs/>
7. Kinney, R., Anastasiades, C., Authur, R., et al. (2023). *The Semantic Scholar Open Data Platform*. arXiv:2301.10140.
8. Executable Books Community. *Jupyter Book v1 Documentation*. <https://jupyterbook.org/>
