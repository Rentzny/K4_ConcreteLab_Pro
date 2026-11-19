"""Grafik cetak, berasal dari HasilAnalisis yang sama dengan dashboard."""
from __future__ import annotations
from io import BytesIO
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from .engine import HasilAnalisis

NAVY = "#15324C"
TEAL = "#12786F"
BLUE = "#427DA1"
AMBER = "#CF8C3A"
COLORS = [BLUE, TEAL, AMBER, "#7C78AA", "#8593A0", "#4E8A93"]


def _style(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", alpha=.15)
    ax.set_axisbelow(True)
    ax.tick_params(colors="#33485B")


def _png(fig) -> bytes:
    output = BytesIO()
    fig.savefig(output, format="png", dpi=170, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return output.getvalue()


def histogram(h: HasilAnalisis) -> bytes:
    fig, ax = plt.subplots(figsize=(10, 4.2))
    x = h.benda_uji["kuat_tekan_MPa"]
    bins = max(3, min(20, int(np.sqrt(len(x)) * 1.5)))
    ax.hist(x, bins=bins, color=BLUE, edgecolor="white", linewidth=1.3)
    ax.axvline(h.mutu_rencana, color="#BF543D", lw=2, ls="--", label=f"Target {h.mutu_rencana:g} MPa")
    ax.set(xlabel="Kuat tekan silinder (MPa)", ylabel="Jumlah silinder", title="Distribusi kuat tekan beton")
    ax.legend(frameon=False, loc="upper right")
    _style(ax)
    fig.tight_layout()
    return _png(fig)


def perbandingan(h: HasilAnalisis) -> bytes:
    fig, ax = plt.subplots(figsize=(10, 4.2))
    stats = h.statistik
    n = len(stats)
    inds = np.arange(n)
    ax.bar(inds, stats["rata_rata"], yerr=stats["simpangan_baku"].fillna(0), capsize=5,
           color=[COLORS[i%len(COLORS)] for i in inds], width=.65, ecolor="#526576")
    ax.axhline(h.mutu_rencana, ls="--", color="#BF543D", lw=2, label=f"Target {h.mutu_rencana:g} MPa")
    ax.set_xticks(inds, stats["campuran"].astype(str).tolist())
    ax.set(xlabel="Campuran", ylabel="Rata-rata ± SD (MPa)", title="Perbandingan rata-rata per campuran")
    ax.set_ylim(bottom=0, top=max(1, (stats["rata_rata"]+stats["simpangan_baku"].fillna(0)).max()*1.23))
    ax.legend(frameon=False)
    _style(ax)
    fig.tight_layout()
    return _png(fig)


def boxplot(h: HasilAnalisis) -> bytes:
    fig, ax = plt.subplots(figsize=(10, 4.2))
    grouped = list(h.benda_uji.groupby("campuran", sort=True))
    vals = [d["kuat_tekan_MPa"].tolist() for _,d in grouped]
    bp = ax.boxplot(vals, patch_artist=True, tick_labels=[str(g) for g,_ in grouped], showmeans=True)
    for box, color in zip(bp["boxes"], COLORS*max(1,(len(vals)//len(COLORS))+1)):
        box.set(facecolor=color, edgecolor=NAVY, alpha=.75)
    ax.axhline(h.mutu_rencana, ls="--", color="#BF543D", lw=2)
    ax.set(xlabel="Campuran", ylabel="Kuat tekan (MPa)", title="Sebaran dan variasi hasil per campuran")
    _style(ax)
    fig.tight_layout()
    return _png(fig)


def tren(h: HasilAnalisis) -> bytes:
    fig, ax = plt.subplots(figsize=(10, 4.2))
    for i, (campuran, d) in enumerate(h.rekap_uji.groupby("campuran", sort=True)):
        d = d.sort_values("urutan_uji" if "urutan_uji" in d.columns else "id_pengujian")
        ax.plot(np.arange(1,len(d)+1), d["kuat_tekan_uji_MPa"], marker="o", ms=6,
                color=COLORS[i%len(COLORS)], label=f"Campuran {campuran}", lw=1.8)
    ax.axhline(h.mutu_rencana, ls="--", color="#BF543D", lw=1.5, label=f"Target {h.mutu_rencana:g} MPa")
    ax.set(xlabel="Urutan pengujian dalam setiap campuran", ylabel="Rata-rata hasil uji (MPa)", title="Tren hasil uji per campuran")
    ax.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True))
    ax.legend(frameon=False, fontsize=8, ncol=2)
    _style(ax)
    fig.tight_layout()
    return _png(fig)


def semua_grafik(h: HasilAnalisis) -> dict[str,bytes]:
    return {"histogram.png":histogram(h),"perbandingan_rata_rata.png":perbandingan(h),
            "boxplot_campuran.png":boxplot(h),"tren_pengujian.png":tren(h)}
