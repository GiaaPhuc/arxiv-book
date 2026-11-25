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

```{admonition} Phạm vi số đo hiệu năng: Toàn bộ 25.000 Định danh trên Google Colab (38 Lượt chạy tích lũy)
:class: note
Toàn bộ số đo hiệu năng thời gian thực thi (Runtime), bộ nhớ RAM RSS và dung lượng đĩa dưới đây được đo đạc tự động bằng luồng `ResourceSampler` và `time.perf_counter()` trên **toàn bộ 25.000 ID (5 dải dữ liệu)** qua **38 lượt chạy tích lũy** (`2026-11-07T05:17:47+00:00` → `2026-11-13T16:13:34+00:00` UTC, hợp nhất `32` bản ghi phiên có dấu thời gian `Runs 7–38` trong `stats/m1/summary.json` và đối chiếu tổng tích lũy trong `stats/m1/performance.json`).
```

## 4.1. Môi trường Kiểm thử, Phương pháp Đo lường & Quy tắc Tính Tổng Runtime

Tuân thủ tiêu chuẩn đánh giá hiệu năng của đề bài, toàn bộ chiến dịch thu thập **25.000 ID** được thực thi trên môi trường **Google Colab chạy chỉ CPU (CPU-only, không sử dụng GPU/TPU)**:

- **Cấu hình phần cứng thực thi ghi nhận từ `stats/m1/performance.json`:**
  - *Các phiên chính (Runs 13–33):* Máy ảo **Google Colab CPU-only** tiêu chuẩn (**`2` vCPU Intel Xeon**, **`~12,7 GiB` RAM**, hệ điều hành Linux x86_64, ổ đĩa cục bộ `/content/data`, **Python `3.13.18`**).
  - *Các phiên khởi đầu và chốt S2 (Runs 7–12 & Runs 34–38):* Instance **Google Colab CPU-only** cấu hình **`12` vCPU**, **Python `3.13.16`** (hoàn toàn không gắn GPU/TPU).
- **Quy tắc tính Tổng Thời gian Thực thi Đầu–Cuối (*End-to-End Wall-Clock Time*):**
  1. **Bao gồm mọi thời gian chờ retry, backoff và cooldown:** Tổng Runtime báo cáo tính **đầy đủ** toàn bộ thời gian tải mạng, giải nén, chờ giới hạn tốc độ (`RateLimiter`), và **mọi khoảng chờ retry / backoff / cooldown khi gặp lỗi mạng hoặc HTTP `429`/`5xx`** (`cooldown_retry_seconds`). Khoảng thời gian duy nhất được loại trừ là `idle_gap_seconds` (khoảng thời gian tắt máy/ngắt kết nối giữa hai phiên Colab không liên tiếp).
  2. **Sửa công thức ghép chặng khi chạy 2 giai đoạn tách rời:** Công thức đường găng $\max(T_{\text{arXiv}}, T_{\text{S2}})$ chỉ đúng khi `s2-worker` chạy song song trong **cùng một phiên** với luồng tải arXiv. Khi vận hành quy trình 2 giai đoạn tách rời (**Giai đoạn 1 `--skip-s2`** ở các phiên đầu rồi **Giai đoạn 2 `--s2-only`** ở các phiên tiếp theo), tổng thời gian thực thi đầu–cuối của toàn hệ thống là **tổng tuần tự (`sum`) thời gian thực (`finished_at_utc - started_at_utc`) của toàn bộ các phiên Giai đoạn 1 và Giai đoạn 2** (bao gồm cả thời gian quét `--snapshot` đầu vào).
- **Phương pháp đo lường viễn trắc $\mathcal{O}(1)$ (`metrics.py`):** Luồng nền `ResourceSampler` (`psutil`) lấy mẫu định kỳ mỗi **5 giây** tổng RAM `RSS` của tiến trình chính và mọi tiến trình con, kết hợp quét đĩa bằng `os.scandir()` mỗi **300 giây** và lúc kết thúc phiên.

---

## 4.2. Thời gian Chạy Hệ thống (Runtime Analysis) & Nhật ký Từng Phiên Colab

```{code-cell} ipython3
:tags: [remove-input]

from pathlib import Path
from datetime import datetime
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
            if candidate.is_dir() and (candidate / "performance.json").is_file():
                return candidate
    return Path("../stats/m1")


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


def _parse_iso(ts: object) -> datetime | None:
    if not isinstance(ts, str) or not ts.strip():
        return None
    try:
        return datetime.fromisoformat(ts.strip().replace("Z", "+00:00"))
    except ValueError:
        return None


def _session_wall_seconds(sess: dict) -> float:
    t0 = _parse_iso(sess.get("started_at_utc") or sess.get("started_at"))
    t1 = _parse_iso(sess.get("finished_at_utc") or sess.get("ended_at"))
    if t0 is not None and t1 is not None and t1 >= t0:
        return (t1 - t0).total_seconds()
    return float(sess.get("active_seconds", 0.0) or 0.0) + float(
        sess.get("cooldown_retry_seconds", 0.0) or 0.0
    )


def _infer_session_mode(sess: dict) -> str:
    ss = sess.get("stage_seconds", {}) or {}
    has_arx = float(ss.get("discovery", 0.0) or 0.0) + float(ss.get("download", 0.0) or 0.0) > 0.0
    has_s2 = float(ss.get("s2", 0.0) or 0.0) > 0.0
    vcpu = sess.get("cpu_count_logical")
    vcpu_tag = f" · {int(vcpu)} vCPU" if vcpu else ""
    if has_arx and has_s2:
        return f"arXiv + S2 song song{vcpu_tag}"
    if has_arx:
        return f"GĐ 1 (--skip-s2){vcpu_tag}"
    if has_s2:
        return f"GĐ 2 (--s2-only){vcpu_tag}"
    return f"Kiểm tra / Resume{vcpu_tag}"


if HAS_PERF:
    perf = json.loads((STATS_DIR / "performance.json").read_text(encoding="utf-8"))
    summary = json.loads((STATS_DIR / "summary.json").read_text(encoding="utf-8"))
    bench = summary.get("benchmark_summary", {}) if isinstance(summary.get("benchmark_summary"), dict) else {}
    sessions = bench.get("sessions") or perf.get("sessions") or []

    st = perf.get("stage_seconds", {})
    s2_info = perf.get("s2", {})
    ax_info = perf.get("arxiv", {})

    sess_wall_sum = sum(_session_wall_seconds(s) for s in sessions)
    sum_sess_disc = sum(float((s.get("stage_seconds") or {}).get("discovery", 0.0) or 0.0) for s in sessions)
    sum_sess_dl = sum(float((s.get("stage_seconds") or {}).get("download", 0.0) or 0.0) for s in sessions)
    sum_sess_ext = sum(float((s.get("stage_seconds") or {}).get("extract", 0.0) or 0.0) for s in sessions)
    sum_sess_s2 = sum(float((s.get("stage_seconds") or {}).get("s2", 0.0) or 0.0) for s in sessions)
    sum_sess_cd = sum(float(s.get("cooldown_retry_seconds", 0.0) or 0.0) for s in sessions)

    total_runs = int(perf.get("runs", len(sessions)) or len(sessions))
    legacy_disc_dl = max(
        0.0,
        (float(st.get("discovery", 0.0)) - sum_sess_disc)
        + (float(st.get("download", 0.0)) - sum_sess_dl),
    )
    legacy_ext = max(0.0, float(st.get("extract", 0.0)) - sum_sess_ext)
    legacy_s2 = max(0.0, float(st.get("s2", 0.0)) - sum_sess_s2)
    legacy_cd = max(0.0, float(perf.get("cooldown_retry_seconds", 0.0)) - sum_sess_cd)
    legacy_wall_s = (legacy_disc_dl + legacy_cd) if total_runs > len(sessions) else 0.0

    wall_end_to_end_s = sess_wall_sum + legacy_wall_s
    if wall_end_to_end_s <= 0.0:
        wall_end_to_end_s = float(perf.get("active_seconds", 0.0)) + float(
            perf.get("cooldown_retry_seconds", 0.0)
        )

    ax_wait_s = float(ax_info.get("cooldown_seconds", 0.0) or 0.0) + float(
        ax_info.get("retry_wait_seconds", 0.0) or 0.0
    )
    s2_wait_s = float(s2_info.get("retry_wait_seconds", 0.0) or 0.0)
    idle_gap_s = float(bench.get("idle_gap_seconds", 0.0) or 0.0)

    n_req = max(int(summary.get("ids_requested") or 0), 1)
    n_pap = max(int(summary.get("papers_total") or 0), 1)
    n_pair = max(int(summary.get("pairs_total") or 0), 1)

    runtime_rows = [
        ("Tổng thời gian thực đầu–cuối toàn trình (End-to-End Wall Time, gồm mọi retry/cooldown)", fmt_duration(wall_end_to_end_s)),
    ]
    if legacy_wall_s > 0.0:
        runtime_rows.append(
            (f"Tổng Wall Time trực tiếp của {len(sessions)} phiên có timestamp UTC (Runs 7–{total_runs})", fmt_duration(sess_wall_sum))
        )
        runtime_rows.append(
            (f"Phần tích lũy các lượt khởi đầu tiền-v3.3 chưa ghi mảng sessions (Runs 1–{total_runs - len(sessions)})", fmt_duration(legacy_wall_s))
        )
    runtime_rows.extend([
        ("Khoảng nghỉ ngoại tuyến giữa các phiên Colab đã loại trừ (idle_gap_seconds)", fmt_duration(idle_gap_s)),
        ("Thời gian khám phá siêu dữ liệu (discovery — Snapshot / Atom API)", fmt_duration(st.get("discovery", 0.0))),
        ("Thời gian tải gói nguồn + chờ nhịp lịch sự arXiv (download)", fmt_duration(st.get("download", 0.0))),
        ("Thời gian giải nén & lọc .tex/.bib/.bbl + băm SHA-256 (extract)", fmt_duration(st.get("extract", 0.0))),
        ("Thời gian chờ retry/cooldown kênh arXiv (HTTP 429 & thermal)", f"{fmt_duration(ax_wait_s)} ({int(ax_info.get('http_429', 0)):,} lượt 429)"),
        ("Thời gian hoạt động chủ động luồng Semantic Scholar (s2)", fmt_duration(st.get("s2", 0.0))),
        ("Thời gian chờ backoff HTTP 429 trên kênh Semantic Scholar", f"{fmt_duration(s2_wait_s)} ({int(s2_info.get('http_429', 0)):,} lượt 429 · {int(s2_info.get('batches', 0)):,} lô)"),
        ("Thời gian TB đầu–cuối mỗi bài báo được yêu cầu (wall / ids_requested)", f"{wall_end_to_end_s / n_req:.2f} giây / ID"),
        ("Thời gian TB đầu–cuối một phiên bản bài báo (wall / pairs_total)", f"{wall_end_to_end_s / n_pair:.2f} giây / phiên bản"),
        ("Tổng số phiên chạy cộng dồn (runs / timestamped sessions)", f"{total_runs} lượt ({len(sessions)} phiên có log UTC)"),
    ])
    show_table(pd.DataFrame(runtime_rows, columns=["Chỉ số thời gian chạy (Runtime — tính đủ retry/cooldown)", "Giá trị đo đạc"]), kv=True)

    # Hiển thị bảng viễn trắc CDN/Transport v3.16–v3.18 nếu có trong metrics mới
    if int(ax_info.get("requests_ok", 0) or 0) > 0 or int(ax_info.get("cdn_edge_hits", 0) or 0) > 0:
        wire_b = int(ax_info.get("wire_bytes", 0) or 0)
        wire_s = float(ax_info.get("wire_download_seconds", 0.0) or 0.0)
        tel_rows = [
            ("Tổng yêu cầu arXiv 2xx (requests_ok) / Tổng byte wire", f"{int(ax_info.get('requests_ok', 0)):,} req · {wire_b / 1024**3:.3f} GiB"),
            ("Phân bố Fastly CDN (HIT / SHIELD_HIT / MISS)", f"{int(ax_info.get('cdn_edge_hits', 0)):,} / {int(ax_info.get('cdn_shield_hits', 0)):,} / {int(ax_info.get('cdn_origin_misses', 0)):,}"),
            ("Ngắt sớm PDF/ZIP từ HTTP Header (early_header_rejects)", f"{int(ax_info.get('early_header_rejects', 0)):,} lượt (0 B body)"),
            ("Giải nén cắt dòng Cut-Through (in_flight_extractions)", f"{int(ax_info.get('in_flight_extractions', 0)):,} phiên bản"),
            ("Xen kẽ bài nặng & Byte-Budget Breather (v3.17)", f"{int(ax_info.get('heavy_versions_interleaved', 0)):,} bản xen kẽ · {int(ax_info.get('byte_budget_breathers', 0)):,} breather"),
        ]
        if wire_s > 0:
            tel_rows.append(("Tốc độ truyền tải wire trung bình (wire_bytes / wire_seconds)", f"{(wire_b / 1024**2) / wire_s:.2f} MiB/s"))
        show_table(pd.DataFrame(tel_rows, columns=["Viễn trắc Transport & Fastly CDN (v3.16–v3.18)", "Giá trị đo đạc"]), kv=True)

    stage_labels = [
        "Khám phá bài báo\n(discovery)",
        "Tải nguồn + chờ nhịp\n(download)",
        "Giải nén & lọc TeX\n(extract)",
        "Chờ phạt arXiv\n(cooldown & retry)",
        "Tham khảo S2\n(hoạt động chủ động)",
        "Chờ phạt S2 429\n(retry_wait_seconds)",
    ]
    stage_secs = [
        float(st.get("discovery", 0.0)),
        float(st.get("download", 0.0)),
        float(st.get("extract", 0.0)),
        ax_wait_s,
        float(st.get("s2", 0.0)),
        s2_wait_s,
    ]
    use_hours = max(stage_secs, default=0.0) >= 3600
    scale = 3600.0 if use_hours else 1.0
    unit_lbl = "Thời gian tích lũy (giờ)" if use_hours else "Thời gian tích lũy (giây)"
    stage_vals = [s / scale for s in stage_secs]

    fig, ax = plt.subplots(figsize=(9.0, 3.65))
    bars = ax.barh(
        stage_labels,
        stage_vals,
        color=["#4dabf7", "#1971c2", "#2b8a3e", "#e67700", "#f59f00", "#e03131"],
    )
    ax.invert_yaxis()
    ax.set_xlabel(unit_lbl)
    ax.set_title("Phân rã thời gian hoạt động chủ động & thời gian chờ retry/cooldown")
    max_v = max(stage_vals) if max(stage_vals) > 0 else 1.0
    for b, sec in zip(bars, stage_secs):
        ax.text(
            b.get_width() + max_v * 0.02,
            b.get_y() + b.get_height() / 2,
            fmt_duration(sec),
            va="center",
            fontsize=8.3,
        )
    ax.set_xlim(0, max_v * 1.44)
    plt.tight_layout()
    plt.show()
    plt.close(fig)
else:
    runtime_preview = pd.DataFrame(
        [
            ("Tổng thời gian thực đầu–cuối hệ thống (End-to-End Wall Time)", "⏳ Chờ stats/performance.json"),
            ("Tổng thời gian khám phá bài báo (discovery — Snapshot / Atom API)", "⏳ Chờ stats/performance.json"),
            ("Tổng thời gian tải nguồn + chờ nhịp lịch sự arXiv (download)", "⏳ Chờ stats/performance.json"),
            ("Tổng thời gian giải nén & lọc .tex/.bib/.bbl + SHA-256 (extract)", "⏳ Chờ stats/performance.json"),
            ("Thời gian hoạt động & backoff Semantic Scholar (s2)", "⏳ Chờ stats/performance.json"),
        ],
        columns=["Chỉ số thời gian chạy cần báo cáo (Mục 4.2)", "Trạng thái dữ liệu"],
    )
    show_pending_perf_box("Bảng chỉ số Runtime và biểu đồ phân rã thời gian tại Mục 4.2", runtime_preview)
```

### 4.2.1. Nhật ký Đối chiếu Từng Phiên Chạy trên Google Colab

Bảng dưới đây trích xuất trực tiếp từ mảng `sessions` trong `stats/m1/summary.json` / `stats/m1/performance.json` để đối chiếu minh bạch từng phiên checkpoint Colab với con số tổng hợp toàn trình:

```{code-cell} ipython3
:tags: [remove-input]

if HAS_PERF and sessions:
    sess_rows = []
    if legacy_wall_s > 0.0:
        legacy_act = legacy_disc_dl + legacy_ext + legacy_s2
        sess_rows.append({
            "Phiên (#)": f"Runs 1–{total_runs - len(sessions)}*",
            "Bắt đầu (UTC)": "Trước 2026-11-07T05:17",
            "Kết thúc (UTC)": "2026-11-07T05:17:47Z",
            "Chế độ chạy": "Tiền v3.3 (tổng hợp delta)",
            "Lượt bài xử lý": "3.069 (tích lũy)",
            "Active Stage (s)": f"{legacy_act:,.1f}",
            "Retry & Cooldown (s)": f"{legacy_cd:,.1f}",
            "Wall Time Phiên (s)": f"{legacy_wall_s:,.1f}",
            "Đỉnh RAM (MiB)": "—",
        })

    for s in sessions:
        w_sec = _session_wall_seconds(s)
        act_sec = float(s.get("active_seconds", 0.0) or 0.0)
        cd_sec = float(s.get("cooldown_retry_seconds", 0.0) or 0.0)
        peak_mib = float(s.get("peak_rss_mib") or ((s.get("resources") or {}).get("peak_rss_mib") or 0.0))
        t_start = str(s.get("started_at_utc") or s.get("started_at") or "").replace("+00:00", "Z")
        t_end = str(s.get("finished_at_utc") or s.get("ended_at") or "").replace("+00:00", "Z")
        sess_rows.append({
            "Phiên (#)": f"Run {int(s.get('run', 0))}",
            "Bắt đầu (UTC)": t_start,
            "Kết thúc (UTC)": t_end,
            "Chế độ chạy": _infer_session_mode(s),
            "Lượt bài xử lý": f"{int(s.get('papers_done', 0) or 0):,}",
            "Active Stage (s)": f"{act_sec:,.1f}",
            "Retry & Cooldown (s)": f"{cd_sec:,.1f}",
            "Wall Time Phiên (s)": f"{w_sec:,.1f}",
            "Đỉnh RAM (MiB)": f"{peak_mib:,.1f}" if peak_mib > 0 else "—",
        })

    sess_rows.append({
        "Phiên (#)": "Tổng hợp toàn trình",
        "Bắt đầu (UTC)": "2026-11-07 (Run 1)",
        "Kết thúc (UTC)": str(sessions[-1].get("finished_at_utc") or "").replace("+00:00", "Z"),
        "Chế độ chạy": f"{total_runs} lượt (loại trừ {idle_gap_s / 3600:.2f} h tắt máy)",
        "Lượt bài xử lý": f"{int(summary.get('papers_total', 0)):,} bài duy nhất",
        "Active Stage (s)": f"{float(perf.get('active_seconds', 0.0)):,.1f}",
        "Retry & Cooldown (s)": f"{float(perf.get('cooldown_retry_seconds', 0.0)):,.1f}",
        "Wall Time Phiên (s)": f"{wall_end_to_end_s:,.1f} ({wall_end_to_end_s / 3600:.2f} h)",
        "Đỉnh RAM (MiB)": f"{float(perf.get('resources', {}).get('ram_peak_bytes', 0.0)) / 1024**2:,.2f}",
    })
    show_table(pd.DataFrame(sess_rows))
elif HAS_PERF:
    show_pending_perf_box("Bảng Nhật ký Từng Phiên Colab tại Mục 4.2.1 (chưa có mảng sessions)")
```

**Phân tích hiệu năng thời gian và đối chiếu nâng cấp `v3.14` → `v3.18`:**

- **Tổng thời gian thực thi đầu–cuối tính đầy đủ retry/cooldown và Giai đoạn 2 (`318.666,4 s ≈ 88,52 giờ`):**
  - Trên **32 phiên chạy có dấu thời gian UTC (`Runs 7–38`)**, tổng thời gian thực tế (`sum(finished_at_utc - started_at_utc)`, bao gồm toàn bộ thời gian chờ nhịp, backoff và cooldown nhưng không tính `72,35 giờ` nghỉ tắt máy giữa các phiên) là **`297.279,0 s` (`82,58 giờ`)**. Cộng thêm phần tích lũy của `Runs 1–6` trước khi bật log mảng `sessions` (`21.387,4 s` gồm `10.887,4 s` tải/khám phá và `10.500,0 s` cooldown), **tổng thời gian thực đầu–cuối toàn trình đạt `318.666,4 s` (`88,52 giờ`)** — tương ứng trung bình **`12,75 giây / ID`** và **`7,65 giây / phiên bản`** trên toàn bộ `41.629` phiên bản.
  - Nếu tách riêng thời gian hoạt động chủ động chưa cộng cooldown phạt và Giai đoạn 2, tổng thời gian khối arXiv (`discovery + download + extract`) là **`242.271,31 s` (`67,30 giờ`)**, trong đó `discovery` chiếm `598,48 s` (~`9,97 phút`), `extract` chiếm `2.393,82 s` (~`39,90 phút` giải nén song song trên `extract-worker`), và `download` chiếm `239.279,01 s` (`66,47 giờ`), cộng thêm **`37.065,0 s` (`10,30 giờ`)** chờ phạt arXiv (`311` lần `429` + `96` thermal cooldown). Riêng các phiên chạy tách pha **Giai đoạn 2 (`--s2-only`, `Runs 15, 18, 35–38`)** tiêu tốn **`30.452,0 s` (`8,46 giờ`)** (chủ yếu nằm trong **`83.745,0 s ≈ 23,26 giờ`** chờ backoff qua **`2.592` lượt HTTP 429** của Semantic Scholar trên `2.077` lô `25` bài).
- **Đối chiếu cận dưới lý thuyết & mốc tham khảo trung vị năm trước (`7–8 giờ / 5.000 ID`, tức `~35–40 giờ / 25.000 ID`):**
  - Với `41.629` phiên bản và nhịp lịch sự tối thiểu `3,00 s` trên 1 kết nối tới `export.arxiv.org`, cận dưới lý thuyết thuần túy cho công đoạn `/src/` là:
    $$T_{\text{floor, min}} \approx 41.629 \times 3{,}00\text{ s} \approx 124.887\text{ s} \approx 34{,}69\text{ giờ}$$
  - Kết quả `88,52 giờ` của đợt chạy lịch sử phản ánh rõ ba nút thắt cổ chai đã được nhóm đo đạc và khắc phục triệt để trong kiến trúc **`v3.15` → `v3.18`**:
    1. **Loại bỏ phạt kép End-to-Start & Van ngủ cứng `50 MiB → 12 s` (`v3.15`):** Ở các phiên cũ, sàn End-to-Start `>= 3,05–3,25 s` cộng dồn với thời gian tải mạng và các lần ngủ cứng `12 s` mỗi `50 MiB` đã làm mất thêm `~4,5 giờ / 5.000 ID` (`~22,5 giờ / 25.000 ID`). Cơ chế **Start-to-Start `3,05 s + jitter`** + đệm hậu tải `0,25 s` + **Deficit Breather** (trần `6,0 s`) đưa tốc độ lý tưởng về sát mốc tham khảo **`~7,5–8,0 giờ / 5.000 ID`** (`~37,5–40 giờ / 25.000 ID`).
    2. **Zero-Body Header Early-Reject, Traffic-Shaping & CDN Self-Healing (`v3.16–v3.17.1`):** Ngắt sớm `2.751` gói PDF/ZIP ngay từ `Content-Type` header (`wire_bytes = 0`), kết hợp hoán vị tỷ lệ vàng + xen kẽ bài nặng `>= 25 MiB` + **Leaky Byte-Budget `360 MiB / 180 s`** giúp tránh cạn Token Bucket của Fastly CDN (nguyên nhân từng gây `311` lần `429` và `10,30 giờ` cooldown ở đợt chạy đầu).
    3. **Semantic Scholar High-Density Batch `150` + Save-First + Diệt False-Positive `/references` (`v3.18`):** Nâng kích thước lô từ `25` lên **`150` bài/lô** giảm **`6×`** số HTTP request, kết hợp siết `_references_truncated()` để không bắn hàng nghìn request `/references` giả do mục `citedPaper = null` và **Save-First Isolation** lưu ngay bài đã xong, triệt tiêu nguyên nhân chính gây ra **`2.592` lần HTTP `429`** (`23,26 giờ` chờ phạt S2) ở kiến trúc cũ.

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
    weighted_avg_mib = bench.get("session_time_weighted_avg_rss_mib")

    mem_disk_rows = [
        ("Lượng RAM tối đa dùng trong quá trình thu thập (ram_peak_bytes)", f"{ram_peak:,.0f} B ({ram_peak / 1024**2:.2f} MiB)"),
        ("Mức tiêu thụ RAM trung bình theo mẫu (ram_mean_bytes — 5s/lần)", f"{ram_mean:,.0f} B ({ram_mean / 1024**2:.2f} MiB)"),
    ]
    if weighted_avg_mib is not None:
        mem_disk_rows.append(
            ("Mức RAM trung bình theo trọng số thời gian phiên (time-weighted RSS)", f"{float(weighted_avg_mib):.2f} MiB")
        )
    mem_disk_rows.extend([
        ("Tổng số mẫu đo RAM định kỳ đã thu thập (ram_samples)", f"{int(res.get('ram_samples') or 0):,} mẫu"),
        ("Dung lượng lưu trữ đĩa tối đa cần thiết (disk_peak_bytes)", fmt_storage(disk_peak)),
        ("Dung lượng lưu trữ của đầu ra cuối cùng (disk_final_bytes)", fmt_storage(disk_final)),
    ])
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
            ("Lượng RAM tối đa (ram_peak_bytes)", "⏳ Chờ stats/performance.json"),
            ("Mức tiêu thụ RAM trung bình (ram_mean_bytes)", "⏳ Chờ stats/performance.json"),
            ("Dung lượng lưu trữ đĩa tối đa (disk_peak_bytes)", "⏳ Chờ stats/performance.json"),
            ("Dung lượng lưu trữ đầu ra cuối cùng (disk_final_bytes)", "⏳ Chờ stats/performance.json"),
        ],
        columns=["Chỉ số bộ nhớ & lưu trữ (Mục 4.3)", "Trạng thái dữ liệu"],
    )
    show_pending_perf_box("Bảng chỉ số RAM/Đĩa và cặp biểu đồ so sánh tại Mục 4.3", mem_preview)
```

**Phân tích hiệu quả sử dụng bộ nhớ và lưu trữ:**

- **Độ phức tạp không gian bộ nhớ $\mathcal{O}(1)$ theo quy mô kho ngữ liệu:** Nhờ giới hạn hàng đợi `extract_max_queue_bytes = 192 MiB`, đệm RAM Zero-Copy $\le 96\text{ MiB}$, bộ đọc `_FastGzipStream` (`512 KiB`) và chế độ giải nén cắt dòng trực tiếp trên luồng socket `--in-flight-extract` (`128 KiB`, `0 B` ghi tạm vào `.tmp/`), mức tiêu thụ RAM hoàn toàn phẳng bất kể kho dữ liệu tăng từ vài trăm lên `25.000` bài báo.
- **Tối ưu hóa dung lượng đĩa và bảo vệ dữ liệu:** Việc loại bỏ toàn bộ ảnh nhị phân ngay trên luồng giải nén và chỉ lưu `.tex`, `.bib`, `.bbl` giúp toàn bộ kho ngữ liệu **25.000 bài báo (`41.629` phiên bản)** chỉ chiếm **23,686 GiB** (`24.254,81 MiB` / `25.433.014.346 B`) ở cả đỉnh quá trình chạy lẫn đầu ra cuối cùng (không phát sinh rác tệp tạm trên đĩa).
- **Đánh giá số đo thực nghiệm trên Google Colab:**
  - **Bộ nhớ RAM thường trú (RSS):** Mức tiêu thụ RAM trung bình theo mẫu là **195,18 MiB** (trung bình theo trọng số thời gian giữa các phiên là **218,73 MiB**) và đỉnh RAM tối đa đạt **362,88 MiB** trên tổng số **60.774 mẫu** đo định kỳ. Con số đỉnh này chỉ chiếm khoảng **2,8%** dung lượng RAM khả dụng (`12,7 GiB`) của Google Colab CPU chuẩn `2 vCPU`, loại bỏ hoàn toàn nguy cơ tràn bộ nhớ (*Out-Of-Memory*).

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
