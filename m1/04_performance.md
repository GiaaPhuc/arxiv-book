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

```{admonition} Phạm vi số đo hiệu năng hiện tại: 15.000 / 25.000 ID (Sẽ cập nhật khi hoàn tất đủ 25.000 ID)
:class: note
Các chỉ số thời gian chạy, bộ nhớ RAM và dung lượng đĩa dưới đây được kết xuất trực tiếp từ tệp `stats/performance.json`, ghi nhận cộng dồn trung thực qua **`54` phiên chạy/khôi phục thực tế** trên Google Colab CPU (cập nhật đến `2026-11-05T14:43:00Z`) cho **15.000 định danh đầu tiên** (`24.734` phiên bản). **Ngay khi hoàn tất thu thập 10.000 ID còn lại để đạt đủ 25.000 ID, tệp `performance.json` và các phân tích đối chiếu dưới đây sẽ được cập nhật lên số đo toàn cục.**
```

## 4.1. Môi trường Kiểm thử & Phương pháp Đo lường Kiểm chứng

Theo đúng quy chuẩn đánh giá hiệu năng của đề bài, toàn bộ quá trình thu thập chính thức được vận hành và đo đạc trên một **instance Google Colab chạy ở chế độ chỉ CPU (Standard CPU-only Runtime, không bật GPU/TPU)**:

- **Cấu hình hệ thống chuẩn:** Hệ điều hành Ubuntu 22.04 LTS (`x86_64`), vi xử lý ảo hóa Intel(R) Xeon(R) CPU @ 2.20 GHz (`2 vCPU`), bộ nhớ vật lý `12,7 GiB` RAM, ổ đĩa SSD cục bộ `/content` dung lượng khả dụng `~107,7 GiB`, môi trường Python `3.11`.
- **Phương pháp đo lường có thể kiểm chứng (`metrics.py` $\rightarrow$ `stats/performance.json`):**
  1. *Thời gian thực thi (Wall-clock Runtime):* Được đo bằng đồng hồ đơn điệu độ phân giải cao `time.perf_counter()` bao quanh bốn chặng (`discovery`, `download`, `extract`, `s2`) và cộng dồn trung thực xuyên suốt mọi phiên chạy/resume (`runs`). Vì luồng chính arXiv (`discovery + download + extract`) và luồng nền Semantic Scholar (`s2` + thời gian chờ HTTP 429 `retry_wait_seconds`) thực thi song song rồi hội tụ tại `Thread.join()` cuối mỗi phiên, tổng thời gian thực đầu–cuối (*end-to-end wall time*) của toàn hệ thống được xác định bởi đường găng $\max(T_{\text{arXiv}}, T_{\text{S2}})$.
  2. *Bộ nhớ RAM & Lưu trữ đĩa:* Luồng giám sát nền `ResourceSampler` sử dụng thư viện `psutil` lấy mẫu định kỳ mỗi **5 giây** tổng bộ nhớ vật lý thường trú (`RSS`) của tiến trình chính cộng toàn bộ các tiến trình con (`process.children(recursive=True)`), từ đó tính trung bình có trọng số theo tổng số mẫu (`ram_mean_bytes`) và ghi nhận đỉnh cực đại (`ram_peak_bytes`). Dung lượng thư mục làm việc được quét định kỳ mỗi **60 giây** và ngay thời điểm kết thúc bằng `os.scandir()` để xác định dung lượng lưu trữ đĩa tối đa (`disk_peak_bytes`) và dung lượng đầu ra cuối cùng (`disk_final_bytes`).

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
        ("Số lô truy vấn S2 Batch đã thực hiện (tối đa 100 bài/lô)", f"{int(s2_info.get('batches', 0)):,} lô"),
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

**Phân tích hiệu năng thời gian (trên 15.000 ID thực tế — sẽ cập nhật khi đủ 25.000 ID):**

- **Tổng thời gian chạy đầu–cuối và phân rã theo chặng:** Qua `54` phiên vận hành liên tục trên Google Colab CPU, tổng thời gian thực đầu–cuối (*End-to-End Wall Time*) cho **15.000 ID** (`24.734` phiên bản) đạt **`165.812,8 giây` (`46,06 giờ`)**, tương đương trung bình **`11,05 giây / bài báo`** (`6,70 giây / phiên bản`). Trong đó:
  - Chặng **khám phá bài báo (`discovery` — lô 50 ID)** chỉ mất **`3.511,1 giây` (`58,52 phút`**, tức `~0,23 giây/bài`), nhờ gom lô 50 ID giúp giảm số lượt gọi Atom API đi 50 lần so với truy vấn đơn lẻ;
  - Chặng **giải nén luồng, lọc `.tex`/`.bib` & băm `SHA-256` (`extract`)** trên ổ SSD cục bộ chỉ tiêu tốn **`1.476,5 giây` (`24,61 phút`**, tức `~60 ms/phiên bản`);
  - Chặng **tải nguồn và chờ nhịp lịch sự (`download`)** chiếm áp đảo **`160.825,3 giây` (`44,67 giờ` — `96,99%` tổng đường găng)**.
- **Đối chiếu cận dưới lý thuyết (*Rate-limit bound*) và thời gian truyền tải thực tế:** Trên tập 15.000 ID (`24.734` gói nguồn cộng khoảng `~500` lượt gọi lô Atom API cho cả khám phá gốc và ngày sửa đổi trung gian), riêng thời gian ngủ bắt buộc $\Delta t = 3{,}5\text{ s}$ *sau khi đóng stream* trên một kết nối đơn tới `export.arxiv.org` đã tạo ra cận dưới tĩnh:

  $$
  T_{\text{sleep, 15k}} \approx (24.734 + 500) \times 3{,}5\text{ s} \approx 88.319\text{ s} \approx 24{,}53\text{ giờ}
  $$

  *(và với toàn bộ **25.000 ID** ở hệ số $\bar{V} \approx 1{,}65$, cận dưới ngủ tĩnh riêng lẻ đạt $\approx 40{,}9\text{ giờ}$).* Phần thời gian chênh lệch từ `24,53 giờ` lên `44,67 giờ` ở chặng `download` (`~20,14 giờ`, trung bình `~2,93 giây/phiên bản`) chính là thời gian truyền tải vật lý qua mạng cho hơn **`~105 GiB` dữ liệu gói nén** (`4,34 MiB`/phiên bản giải nén) cùng các nhịp chờ `Retry-After` khi IP máy ảo đám mây gặp giới hạn băng thông thoáng qua. Ngoại suy theo nhịp độ thực tế `11,05 giây/ID`, toàn bộ **25.000 ID** sẽ hoàn tất trong khoảng **`~76,7 giờ` wall-clock** *(số đo thực nghiệm 25.000 ID sẽ được cập nhật ngay khi 10.000 ID cuối hoàn tất)*.
- **Hiệu quả thực thi song song hai luồng (arXiv & Semantic Scholar):** Luồng nền Semantic Scholar thực hiện `2.816` lô truy vấn với thời gian xử lý chủ động rất nhỏ (**`9.622,7 giây` = `2,67 giờ`**). Dù gặp `2.592` phản hồi giới hạn tần suất HTTP `429` khiến bộ điều nhịp thích ứng tự động lùi và chờ cộng dồn `155.520,0 giây` (`43,20 giờ`), tổng thời gian luồng S2 (`165.142,7 giây` = `45,87 giờ`) vẫn **hoàn tất gọn bên trong đường găng `46,06 giờ` của luồng tải nguồn arXiv**, không làm tăng thêm tổng thời gian thực của toàn hệ thống.

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

**Phân tích hiệu quả sử dụng bộ nhớ và lưu trữ (trên 15.000 ID thực tế — sẽ cập nhật khi đủ 25.000 ID):**

- **Độ phức tạp không gian bộ nhớ $\mathcal{O}(1)$ được kiểm chứng thực nghiệm:** Qua **`50.891` mẫu đo định kỳ** (`5 giây/lần`) xuyên suốt hơn 46 giờ vận hành thực tế, mức tiêu thụ bộ nhớ vật lý thường trú trung bình (`ram_mean_bytes`) chỉ ở mức **`80.489.596 B` (`76,76 MiB`)** và đỉnh cực đại (`ram_peak_bytes`) đạt **`234.766.336 B` (`223,89 MiB`)** — chỉ chiếm **`~1,72%`** trên tổng `12,7 GiB` RAM của instance Google Colab CPU. Nhờ truyền tải gói nguồn trực tiếp ra tệp tạm theo khối `64 KiB`, giải nén luồng tuần tự và lưu trạng thái vào SQLite trên đĩa, bộ nhớ tiêu thụ hoàn toàn không phình to theo số lượng bài báo.
- **Tối ưu hóa sát sao giữa dung lượng đĩa tối đa và đầu ra cuối cùng:** Toàn bộ kho dữ liệu đầu ra của **15.000 bài báo** (`disk_final_bytes`, bao gồm cây thư mục `.tex`/`.bib` của `22.921` phiên bản, siêu dữ liệu JSON, phản hồi nén `s2_references.raw.json.gz` và `manifest.sqlite`) chiếm **`10.804.249.326 B` (`10,062 GiB`)**, trong khi mức sử dụng ổ đĩa cực đại suốt quá trình chạy (`disk_peak_bytes`) là **`10.825.222.397 B` (`10,082 GiB`)** — chỉ nhỉnh hơn đầu ra cuối cùng vỏn vẹn **`~19,5 MiB`** nhờ giải phóng tệp nén tạm ngay trong khối `finally` của từng phiên bản. Ngoại suy lên quy mô **25.000 ID đầy đủ**, dung lượng đĩa ước tính đạt khoảng **`~16,8 GiB`**, nằm gọn an toàn trong hạn mức `~107,7 GiB` SSD cục bộ của Google Colab CPU *(số đo chính thức sẽ được cập nhật khi hoàn tất đủ 25.000 ID)*.

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
