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

```{admonition} Phạm vi số đo hiệu năng: Báo cáo thực nghiệm trên 5.000 ID (Dải 1) — sẽ cập nhật khi đủ 25.000 ID
:class: important
Toàn bộ số đo hiệu năng thời gian thực thi (Runtime), bộ nhớ RAM RSS và dung lượng đĩa dưới đây được đo đạc tự động bằng luồng `ResourceSampler` và `time.perf_counter()` trên máy chuẩn **Google Colab CPU (2 vCPU, Python 3.13.18)** trong quá trình thu thập trọn vẹn **5.000 ID thuộc Dải 1** (với 18 phiên chạy và 12 session logs hợp nhất).

Khi quá trình crawl nối tiếp cán mốc đủ 25.000 ID, các số đo hiệu năng toàn cục sẽ được cập nhật tiếp.
```

## 4.1. Môi trường Kiểm thử & Phương pháp Đo lường Kiểm chứng

Theo đúng quy chuẩn đánh giá hiệu năng của đề bài, toàn bộ quá trình thu thập chính thức được vận hành và đo đạc trên một máy chuẩn chạy ở chế độ chỉ CPU (Standard CPU-only Runtime, tương thích môi trường Google Colab CPU 2 vCPU, 12,7 GiB RAM):

- **Cấu hình hệ thống chuẩn:** Hệ điều hành Linux x86_64 / Windows, vi xử lý ảo hóa Intel Xeon CPU, bộ nhớ RAM khả dụng $\ge 12\text{ GiB}$, ổ đĩa SSD cục bộ, môi trường Python `3.11`.
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
        ("Tổng thời gian cho việc khám phá bài báo (discovery — Atom API)", fmt_duration(st.get("discovery", 0.0))),
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
            ("Tổng thời gian khám phá bài báo (discovery — lô 50 ID)", "⏳ Chờ stats/performance.json"),
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
  Theo chính sách lịch sự của arXiv, giữa hai request liên tiếp tới `export.arxiv.org` phải cách nhau tối thiểu $\Delta t \ge 3{,}0\text{ s}$ trên 1 kết nối duy nhất. Trong kiến trúc **Producer–Consumer Start-to-Start** với nhịp cơ sở $3{,}15\text{ s} + \text{jitter}$ và khám phá siêu dữ liệu theo lô 250 ID kết hợp tận dụng thẻ `<updated>`:
  
  $$
  N_{\text{arxiv}} = N_{\text{discovery\_batches}} + N_{\text{confirm\_subbatches}} + N_{\text{revised\_batches}} + R
  $$

  Với **5.000 ID** của Dải 1 ($R = 8.200$ phiên bản ở hệ số $\bar{V} = 1{,}64$), tổng số request tới máy chủ arXiv $N_{\text{arxiv}} \approx 20 + 8.200 \approx 8.220$ request, xác định sàn lý thuyết thời gian của bộ điều nhịp:

  $$
  T_{\text{floor, 5k}} \approx 8.220 \times 3{,}15\text{ s} \approx 25.893\text{ s} \approx 7{,}19\text{ giờ}
  $$

  (Khi mở rộng lên toàn bộ **25.000 ID** với $R \approx 41.000$ phiên bản, sàn lý thuyết thời gian sẽ là $T_{\text{floor, 25k}} \approx 41.150 \times 3{,}0\text{ s} \approx 123.450\text{ s} \approx 34{,}3\text{ giờ}$).
  Nhờ nhịp **Start-to-Start** và việc tách giải nén sang pool `extract-worker` 2 luồng, thời gian tải của mọi gói nguồn $\le 2{,}50\text{ s}$ (~96% số bài) đều đạt chu kỳ đúng $3{,}15\text{ s/phiên bản}$ (`+0,00 s` overhead).
- **Hiệu quả thực thi song song của Semantic Scholar:** Luồng nền Semantic Scholar gom lô (`POST /graph/v1/paper/batch`, thực hiện qua 707 lượt truy vấn lô; trong thiết kế pipeline chuẩn hóa mới nhất, kích thước lô mặc định được tối ưu thành 25 bài kết hợp cơ chế chia đôi lô Bisection khi gặp 413/5xx). Thời gian tính toán luồng thuần túy chỉ mất $3.171{,}86\text{ s}$ (~52,86 phút), và tổng thời gian kèm chờ backoff là $26.136{,}86\text{ s}$ (~7,26 giờ). Nhờ vận hành hoàn toàn song song không khóa tiến trình chính, toàn bộ thời gian của Semantic Scholar nằm gọn bên dưới đường găng arXiv ($29.019{,}85\text{ s}$ ~ 8,06 giờ), không làm phát sinh thêm bất kỳ giây chờ nào cho tổng thời gian thực thi đầu–cuối của toàn hệ thống.
- **Đánh giá tổng thời gian chạy thực tế trên 5.000 ID:**
  - Tổng thời gian End-to-End Wall Time ghi nhận đạt **29.019,85 s (~8,06 giờ)**, bám rất sát cận dưới lý thuyết của bộ điều nhịp (độ dôi ra chủ yếu do tải các gói TeX dung lượng lớn và thời gian hồi phục thích ứng 40 lần HTTP 429 từ máy chủ arXiv).
  - Tốc độ xử lý trung bình đạt **5,80 giây / bài báo** (29.019,85 s / 5.000 ID) và **3,54 giây / phiên bản** (29.019,85 s / 8.200 phiên bản).
  - Quá trình thu thập đã vượt qua 18 phiên chạy gián đoạn (`runs = 18`) một cách liền mạch, minh chứng tính kiên cường và khả năng phục hồi nguyên vẹn (resumability) của pipeline qua SQLite WAL manifest.

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
- **Đánh giá số đo thực nghiệm trên 5.000 ID:**
  - **Bộ nhớ RAM thường trú (RSS):** Mức tiêu thụ RAM trung bình thực tế chỉ là **111,10 MiB** và đỉnh RAM tối đa đạt **217,23 MiB** trên tổng số 6.381 mẫu lấy định kỳ. Con số này chiếm chưa tới **1,8%** dung lượng RAM khả dụng (12,7 GiB) của Google Colab, hoàn toàn loại bỏ nguy cơ bị máy ảo buộc dừng do lỗi tràn bộ nhớ (Out-Of-Memory).
  - **Dung lượng lưu trữ đĩa:** Dung lượng đĩa tối đa trong quá trình chạy đạt **2,983 GiB (3.054,90 MiB)** và dung lượng đầu ra cuối cùng sau khi hoàn tất đạt **2,928 GiB (2.998,11 MiB)**. Mức chênh lệch giữa dung lượng đỉnh và dung lượng cuối cùng chỉ vỏn vẹn **~56,8 MiB**, chứng minh các tệp đệm và bộ nhớ tạm được thu hồi tức thì sau mỗi gói giải nén. Toàn bộ kho ngữ liệu 5.000 bài báo đa phiên bản được gói gọn an toàn dưới 3 GiB đĩa.

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
