"""Plotly charts v4.0: palet konsisten, hover/satuan, judul ringkas, tanpa animasi.
Semua figur murni berbasis hasil perhitungan HasilAnalisis.
"""
from __future__ import annotations
import math
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from .engine import HasilAnalisis
from .professional import tabel_kinerja

BLUE="#316A89"
TEAL="#157F75"
AMBER="#D0904A"
RED="#C25F53"
INK="#273E4B"
GRID="#E7EDF1"
PALETTE=[BLUE,TEAL,AMBER,"#8D7CA9","#B7828F","#6A9198","#758D62"]

def _colors(names):
    return {str(x):PALETTE[i%len(PALETTE)] for i,x in enumerate(sorted(map(str,names)))}

def _style(fig:go.Figure,height=370):
    fig.update_layout(
        template="plotly_white",height=height,
        font=dict(family="Arial, sans-serif",color=INK,size=12),
        paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="#FFFFFF",
        margin=dict(l=28,r=18,t=40,b=38),
        legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="left",x=0,font=dict(size=11)),
        hoverlabel=dict(bgcolor="#FFFFFF",font_size=12),
        uirevision="k4v4",
    )
    fig.update_xaxes(showgrid=False,zeroline=False,linecolor=GRID)
    fig.update_yaxes(showgrid=True,gridcolor=GRID,zeroline=False)
    return fig

def grafik_rerata(h:HasilAnalisis):
    t=tabel_kinerja(h)
    colors=_colors(t.campuran)
    fig=go.Figure()
    for row in t.itertuples(index=False):
        sd=float(row.simpangan_baku_MPa)
        valid_sd=math.isfinite(sd)
        fig.add_trace(go.Bar(
            x=[str(row.campuran)],y=[float(row.rata_rata_MPa)],
            name=f"Campuran {row.campuran}",marker_color=colors[str(row.campuran)],
            error_y=dict(type="data",array=[sd if valid_sd else 0],visible=valid_sd,thickness=1.4,width=5),
            text=[f"{row.rata_rata_MPa:.2f}"],textposition="outside",
            customdata=[[row.jumlah_silinder,row.cv_persen]],
            hovertemplate="Campuran %{x}<br>Rerata %{y:.2f} MPa<br>Jumlah %{customdata[0]} silinder<br>CV %{customdata[1]:.2f}%<extra></extra>",
        ))
    fig.add_hline(y=h.mutu_rencana,line_dash="dash",line_color=RED,
                  annotation_text=f"Target {h.mutu_rencana:g} MPa",annotation_position="top right")
    fig.update_layout(bargap=.40,showlegend=False)
    fig.update_yaxes(title="Kuat tekan rata-rata (MPa)",rangemode="tozero")
    fig.update_xaxes(title="Campuran")
    return _style(fig,380)

def grafik_histogram(h:HasilAnalisis):
    d=h.benda_uji.copy()
    colors=_colors(d.campuran.unique())
    count=len(d)
    bins=max(4,min(28,int(np.sqrt(count)*1.6)))
    lo=float(d.kuat_tekan_MPa.min()); hi=float(d.kuat_tekan_MPa.max())
    step=max((hi-lo)/bins,.05)
    fig=px.histogram(d,x="kuat_tekan_MPa",color="campuran",barmode="overlay",
        color_discrete_map=colors,nbins=bins,opacity=.68,
        labels={"kuat_tekan_MPa":"Kuat tekan (MPa)","campuran":"Campuran"})
    fig.update_traces(marker_line_width=1,marker_line_color="white",
        hovertemplate="Kuat tekan: %{x:.2f} MPa<br>Frekuensi: %{y}<extra>%{fullData.name}</extra>")
    fig.add_vline(x=h.mutu_rencana,line_dash="dash",line_color=RED,
        annotation_text=f"Target {h.mutu_rencana:g} MPa",annotation_position="top right")
    fig.update_xaxes(title="Kuat tekan silinder (MPa)")
    fig.update_yaxes(title="Jumlah silinder")
    return _style(fig,370)

def grafik_box(h:HasilAnalisis):
    d=h.benda_uji
    fig=px.box(d,x="campuran",y="kuat_tekan_MPa",color="campuran",points="all",
        color_discrete_map=_colors(d.campuran.unique()),
        labels={"campuran":"Campuran","kuat_tekan_MPa":"Kuat tekan (MPa)"},
        hover_data=["id_benda_uji","id_pengujian"])
    fig.add_hline(y=h.mutu_rencana,line_color=RED,line_dash="dash",annotation_text=f"Target {h.mutu_rencana:g} MPa")
    fig.update_traces(boxmean=True,jitter=.23,pointpos=.0,marker_size=5)
    fig.update_layout(showlegend=False)
    return _style(fig,370)

def grafik_tren(h:HasilAnalisis):
    d=h.rekap_uji.copy()
    d['nomor_uji']=d.groupby('campuran',sort=True).cumcount()+1
    fig=px.line(d,x="nomor_uji",y="kuat_tekan_uji_MPa",color="campuran",markers=True,
        color_discrete_map=_colors(d.campuran.unique()),
        hover_data=['id_pengujian','jumlah_silinder'],
        labels={"nomor_uji":"Urutan hasil uji","kuat_tekan_uji_MPa":"Rerata hasil uji (MPa)","campuran":"Campuran"})
    fig.update_traces(line_width=2.3,marker_size=8)
    fig.add_hline(y=h.mutu_rencana,line_color=RED,line_dash="dash",annotation_text=f"Target {h.mutu_rencana:g} MPa")
    fig.update_xaxes(dtick=1)
    return _style(fig,360)

def grafik_pencapaian(h:HasilAnalisis):
    k=tabel_kinerja(h)
    fig=go.Figure()
    fig.add_trace(go.Bar(
        y=k['campuran'].astype(str),x=k['pencapaian_target_persen'],orientation="h",
        marker_color=[_colors(k.campuran)[x] for x in k.campuran.astype(str)],
        text=[f"{n:.0f}%" for n in k.pencapaian_target_persen],textposition="inside",
        hovertemplate="Campuran %{y}<br>Silinder mencapai target %{x:.1f}%<extra></extra>",
    ))
    fig.update_xaxes(range=[0,105],title="Silinder yang mencapai target (%)",ticksuffix="%")
    fig.update_yaxes(title="Campuran",autorange="reversed")
    fig.update_layout(showlegend=False,bargap=.42)
    return _style(fig,310)

def grafik_ecdf(h:HasilAnalisis):
    d=h.benda_uji
    fig=px.ecdf(d,x="kuat_tekan_MPa",color="campuran",ecdfnorm="percent",
        color_discrete_map=_colors(d.campuran.unique()),
        labels={"kuat_tekan_MPa":"Kuat tekan silinder (MPa)","campuran":"Campuran"})
    fig.add_vline(x=h.mutu_rencana,line_dash="dash",line_color=RED,
        annotation_text=f"Target {h.mutu_rencana:g} MPa")
    fig.update_yaxes(title="Proporsi kumulatif (%)",range=[0,105])
    return _style(fig,370)
