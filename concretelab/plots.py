"""Grafik cetak v4.0. Warna, target, dan nilai dihitung dari HasilAnalisis.

Komponen ini sengaja tidak memerlukan Streamlit supaya PDF/CLI dapat
berjalan tanpa browser. Angka tidak disalin dari contoh CSV.
"""
from __future__ import annotations
from io import BytesIO
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import numpy as np
from .engine import HasilAnalisis

NAVY="#273E4B"
MUTED="#5E7482"
BLUE="#316A89"
TEAL="#157F75"
AMBER="#D0904A"
RED="#C25F53"
COLORS=[BLUE,TEAL,AMBER,"#8D7CA9","#B7828F","#6A9198","#758D62"]

def _makefig():
    fig,ax=plt.subplots(figsize=(10,4.25))
    fig.set_facecolor("white")
    return fig,ax

def _style(ax):
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#DEE7EC')
    ax.spines['bottom'].set_color('#DEE7EC')
    ax.grid(axis='y',alpha=.18,color=MUTED)
    ax.set_axisbelow(True)
    ax.tick_params(colors=MUTED,labelsize=9,length=0,pad=7)
    ax.xaxis.label.set_color(MUTED)
    ax.yaxis.label.set_color(MUTED)
    ax.title.set_color(NAVY)
    ax.title.set_weight('semibold')
    ax.title.set_size(13)
    ax.title.set_position((.5,1.04))

def _target_line(ax,y=None,x=None,label=None):
    if y is not None: ax.axhline(y,color=RED,ls='--',lw=1.8,label=label,zorder=2)
    else: ax.axvline(x,color=RED,ls='--',lw=1.8,label=label,zorder=2)

def _save(fig):
    fig.tight_layout(pad=2.0)
    buf=BytesIO()
    fig.savefig(buf,format='png',dpi=185,bbox_inches='tight',facecolor='white')
    plt.close(fig)
    return buf.getvalue()

def histogram(h:HasilAnalisis)->bytes:
    fig,ax=_makefig()
    groups=list(h.benda_uji.groupby('campuran',sort=True))
    values=h.benda_uji.kuat_tekan_MPa.to_numpy(dtype=float)
    bins=max(4,min(28,int(np.sqrt(len(values))*1.6)))
    lo,hi=float(values.min()),float(values.max())
    if abs(hi-lo)<.001:
        edges=np.linspace(lo-.5,hi+.5,bins+1)
    else:
        edges=np.linspace(lo-.04*(hi-lo),hi+.04*(hi-lo),bins+1)
    for i,(name,data) in enumerate(groups):
        ax.hist(data.kuat_tekan_MPa,bins=edges,alpha=.65,label=f'Campuran {name}',
                color=COLORS[i%len(COLORS)],edgecolor='white',linewidth=.65)
    _target_line(ax,x=h.mutu_rencana,label=f'Target {h.mutu_rencana:g} MPa')
    ax.set(title='Distribusi kuat tekan silinder',xlabel='Kuat tekan (MPa)',ylabel='Jumlah silinder')
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.legend(frameon=False,fontsize=8,ncol=min(4,len(groups)+1),loc='upper right')
    _style(ax)
    return _save(fig)

def perbandingan(h:HasilAnalisis)->bytes:
    fig,ax=_makefig()
    stats=h.statistik
    idx=np.arange(len(stats)); avg=stats.rata_rata.to_numpy(dtype=float)
    sd=stats.simpangan_baku.fillna(0).to_numpy(dtype=float)
    bars=ax.bar(idx,avg,color=[COLORS[i%len(COLORS)] for i in idx],width=.58,
             yerr=sd,capsize=5,ecolor=MUTED,error_kw=dict(lw=1.25))
    _target_line(ax,y=h.mutu_rencana,label=f'Target {h.mutu_rencana:g} MPa')
    ax.set_xticks(idx,stats.campuran.astype(str))
    ylim=max(1,float(max(np.max(avg+sd),h.mutu_rencana))*1.29)
    ax.set_ylim(0,ylim)
    for item,value in zip(bars,avg):
        ax.annotate(f'{value:.2f}',xy=(item.get_x()+item.get_width()/2,value),
                    xytext=(0,4),textcoords='offset points',ha='center',fontsize=8,fontweight='bold',color=NAVY)
    ax.set(title='Rata-rata dan variasi tiap campuran',xlabel='Campuran',ylabel='Rata-rata ± SD (MPa)')
    ax.legend(frameon=False,fontsize=8,loc='upper right')
    _style(ax)
    return _save(fig)

def boxplot(h:HasilAnalisis)->bytes:
    fig,ax=_makefig()
    grouped=list(h.benda_uji.groupby('campuran',sort=True))
    values=[g.kuat_tekan_MPa.to_numpy(dtype=float) for _,g in grouped]
    labels=[str(name) for name,_ in grouped]
    bp=ax.boxplot(values,patch_artist=True,tick_labels=labels,showmeans=True,widths=.5,
                  meanprops=dict(marker='D',markerfacecolor='white',markeredgecolor=NAVY,markersize=4),
                  medianprops=dict(color=NAVY,linewidth=1.9),
                  whiskerprops=dict(color=MUTED),capprops=dict(color=MUTED))
    for i,rect in enumerate(bp['boxes']):
        rect.set(facecolor=COLORS[i%len(COLORS)],edgecolor=NAVY,alpha=.45)
    for i,v in enumerate(values,1):
        offsets=np.linspace(-.11,.11,len(v)) if len(v)>1 else np.array([0.0])
        ax.scatter(np.full(len(v),i)+offsets,v,color=COLORS[(i-1)%len(COLORS)],
                   alpha=.85,edgecolor='white',linewidth=.45,s=18,zorder=4)
    _target_line(ax,y=h.mutu_rencana,label=f'Target {h.mutu_rencana:g} MPa')
    ax.set(title='Sebaran hasil kuat tekan per campuran',xlabel='Campuran',ylabel='Kuat tekan silinder (MPa)')
    ax.legend(frameon=False,fontsize=8,loc='upper right')
    _style(ax)
    return _save(fig)

def tren(h:HasilAnalisis)->bytes:
    fig,ax=_makefig()
    for i,(name,rows) in enumerate(h.rekap_uji.groupby('campuran',sort=True)):
        x=np.arange(1,len(rows)+1)
        ax.plot(x,rows.kuat_tekan_uji_MPa,marker='o',ms=5.5,lw=2,
                color=COLORS[i%len(COLORS)],label=f'Campuran {name}')
    _target_line(ax,y=h.mutu_rencana,label=f'Target {h.mutu_rencana:g} MPa')
    ax.set(title='Tren hasil uji per campuran',xlabel='Urutan hasil uji dalam campuran',ylabel='Rata-rata hasil uji (MPa)')
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.legend(frameon=False,fontsize=8,ncol=2,loc='upper right')
    _style(ax)
    return _save(fig)

def semua_grafik(h:HasilAnalisis)->dict[str,bytes]:
    return {
        'histogram.png':histogram(h),
        'perbandingan_rata_rata.png':perbandingan(h),
        'boxplot_campuran.png':boxplot(h),
        'tren_pengujian.png':tren(h),
    }
