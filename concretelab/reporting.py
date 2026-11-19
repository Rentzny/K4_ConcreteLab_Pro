"""Ekspor PDF profesional dan paket ZIP yang mengikuti HasilAnalisis terkini."""
from __future__ import annotations

from datetime import datetime
from html import escape
from io import BytesIO
import json
from zipfile import ZipFile, ZIP_DEFLATED

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, KeepTogether

from .engine import HasilAnalisis
from .plots import semua_grafik
from .quality import audit_csv, audit_counts

NAVY = colors.HexColor("#15324C")
TEAL = colors.HexColor("#12786F")
SLATE = colors.HexColor("#4F6577")
BORDER = colors.HexColor("#D9E3EA")
PALE = colors.HexColor("#EDF4F6")
SOFT = colors.HexColor("#F5F8FA")
ORANGE = colors.HexColor("#A26A35")
W, H = A4


def clean_str(value, limit=120):
    return escape(str(value)[:limit])


def _number(value, n=2):
    try:
        import math
        if not math.isfinite(float(value)):
            return "-"
        return f"{float(value):,.{n}f}".replace(",", "_").replace(".", ",").replace("_", ".")
    except (ValueError, TypeError):
        return "-"


def _styles():
    s = getSampleStyleSheet()
    s.add(ParagraphStyle(name="K4Title", fontName="Helvetica-Bold", fontSize=22, leading=28, textColor=NAVY, spaceAfter=10))
    s.add(ParagraphStyle(name="K4Subtitle", fontName="Helvetica", fontSize=11, leading=16, textColor=SLATE, spaceAfter=10))
    s.add(ParagraphStyle(name="K4H1", fontName="Helvetica-Bold", fontSize=14, leading=18, textColor=NAVY, spaceBefore=6, spaceAfter=11))
    s.add(ParagraphStyle(name="K4H2", fontName="Helvetica-Bold", fontSize=10, leading=14, textColor=TEAL, spaceBefore=8, spaceAfter=6))
    s.add(ParagraphStyle(name="K4Body", fontName="Helvetica", fontSize=9, leading=14, textColor=NAVY, spaceAfter=6))
    s.add(ParagraphStyle(name="K4Small", fontName="Helvetica", fontSize=7.5, leading=11, textColor=SLATE, spaceAfter=5))
    s.add(ParagraphStyle(name="K4Cell", fontName="Helvetica", fontSize=7.5, leading=10, textColor=NAVY))
    s.add(ParagraphStyle(name="K4Head", fontName="Helvetica-Bold", fontSize=7.4, leading=10, textColor=colors.white))
    s.add(ParagraphStyle(name="K4Kpi", fontName="Helvetica-Bold", fontSize=17, leading=20, textColor=NAVY, alignment=TA_CENTER))
    s.add(ParagraphStyle(name="K4Label", fontName="Helvetica", fontSize=7, leading=10, textColor=SLATE, alignment=TA_CENTER))
    return s


def _p(text, style):
    return Paragraph(clean_str(text, 1200), style)


def _table(headers, rows, widths, s, row_bg=SOFT):
    data = [[_p(h,s["K4Head"]) for h in headers]]
    for row in rows:
        data.append([_p(x, s["K4Cell"]) for x in row])
    t = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0),(-1,0), NAVY),
        ("ROWBACKGROUNDS", (0,1),(-1,-1), [colors.white,row_bg]),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("LEFTPADDING",(0,0),(-1,-1),7), ("RIGHTPADDING",(0,0),(-1,-1),7),
        ("TOPPADDING",(0,0),(-1,-1),4.2), ("BOTTOMPADDING",(0,0),(-1,-1),4.2),
        ("LINEBELOW",(0,-1),(-1,-1),.5,BORDER),
    ]))
    return t


def _kpi(value, label, width, s):
    grid = Table([[_p(value,s["K4Kpi"])], [_p(label,s["K4Label"])]], colWidths=[width-12], hAlign="CENTER")
    grid.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),PALE),("TOPPADDING",(0,0),(-1,0),10),("BOTTOMPADDING",(0,-1),(-1,-1),10)]))
    return grid


def _draw_page(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(NAVY)
    canvas.rect(0,H-14*mm,W,14*mm,fill=1,stroke=0)
    canvas.setFont("Helvetica-Bold",8.2)
    canvas.setFillColor(colors.white)
    canvas.drawString(16*mm,H-9.1*mm,"K4 | CONCRETELAB PRO")
    canvas.setFont("Helvetica",7)
    canvas.setFillColor(SLATE)
    canvas.line(16*mm,15*mm,W-16*mm,15*mm)
    canvas.drawString(16*mm,11*mm,"EVALUASI SIMULASI / BUKAN SERTIFIKAT LABORATORIUM")
    canvas.drawRightString(W-16*mm,11*mm,f"Halaman {doc.page}")
    canvas.restoreState()


def buat_pdf(h: HasilAnalisis, nama_proyek="Proyek K4 - Evaluasi Kuat Tekan Beton", penanggung_jawab="Kelompok PjBL K4", grafik=None) -> bytes:
    """Menghasilkan laporan PDF A4. Isi angka berasal dari satu HasilAnalisis."""
    grafik = grafik or semua_grafik(h)
    out = BytesIO()
    doc = SimpleDocTemplate(out, pagesize=A4, rightMargin=16*mm, leftMargin=16*mm, topMargin=23*mm, bottomMargin=21*mm,
                            title="Laporan Otomatis K4 ConcreteLab Pro", author=penanggung_jawab)
    s = _styles()
    story=[]
    def add(txt,style="K4Body"): story.append(_p(txt,s[style]))
    def section(txt): add(txt,"K4H1")

    # HALAMAN 1 - ringkasan
    story.append(Spacer(1,8*mm))
    add("LAPORAN HASIL ANALISIS", "K4Subtitle")
    add("KUAT TEKAN BETON", "K4Title")
    add(nama_proyek, "K4Subtitle")
    add("Ringkasan eksekutif | terbit otomatis dari data CSV", "K4Small")
    story.append(Spacer(1,7*mm))
    k=h.ringkasan
    labels=[(str(k["silinder"]),"BENDA UJI"),(str(k["campuran"]),"CAMPURAN"),(str(k["jumlah_uji"]),"HASIL UJI"),(_number(h.mutu_rencana),"TARGET (MPa)")]
    area=W-32*mm
    kp = Table([[_kpi(val,lbl,area/4,s) for val,lbl in labels]],colWidths=[area/4]*4)
    kp.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),3),("RIGHTPADDING",(0,0),(-1,-1),3)]))
    story.append(kp)
    story.append(Spacer(1,8*mm))
    section("Ikhtisar hasil campuran")
    statrows=[[r["campuran"],str(int(r["jumlah"])),_number(r["rata_rata"]),_number(r["simpangan_baku"]),_number(r["cv_persen"])] for _,r in h.statistik.iterrows()]
    story.append(_table(["Campuran","n","Rata-rata (MPa)","SD (MPa)","CV (%)"],statrows,[90,54,134,122,123],s))
    story.append(Spacer(1,9*mm))
    add(f"Campuran dengan rata-rata tertinggi: {h.statistik.loc[h.statistik['rata_rata'].idxmax(),'campuran']} "
        f"({_number(h.statistik['rata_rata'].max())} MPa). {k['mencapai_target']} dari {k['silinder']} silinder "
        f"mencapai target secara individual; pencapaian target individual bukan dasar tunggal penerimaan beton.")
    add(f"Evaluasi simulasi: {k['campuran_memenuhi_simulasi']} campuran memenuhi, "
        f"{k['campuran_tidak_memenuhi']} belum memenuhi, dan {k['campuran_belum_dapat_dinilai']} tidak dapat dievaluasi.")
    add("PERINGATAN: Data contoh bersifat ilustratif; data unggahan tidak diverifikasi keaslian atau prosedur pengujiannya. Untuk penerimaan beton nyata diperlukan verifikasi standar, kalibrasi mesin, tata cara pengambilan sampel, umur uji, dan urutan pengujian.","K4Small")
    story.append(Spacer(1,8*mm))
    add("DATA & KETERLACAKAN", "K4H2")
    add(f"Sumber: {h.sumber_data} | Dibuat: {datetime.now():%d-%m-%Y %H:%M} | SHA-256 CSV: {h.hash_sumber[:18]}...", "K4Small")
    add(f"Penanggung jawab: {penanggung_jawab}", "K4Small")
    story.append(PageBreak())

    # HALAMAN 2 - charts
    section("Visualisasi pengujian")
    add("Seluruh grafik mengikuti data dan target mutu dari eksekusi saat ini.","K4Small")
    for filename, caption in [("histogram.png","Distribusi kuat tekan setiap silinder"),("perbandingan_rata_rata.png","Perbandingan rata-rata dan simpangan baku campuran")]:
        add(caption,"K4H2")
        story.append(Image(BytesIO(grafik[filename]),width=169*mm,height=71*mm))
        story.append(Spacer(1,5*mm))
    add("Garis target adalah parameter skenario, bukan batas yang otomatis membuktikan penerimaan beton.","K4Small")
    story.append(PageBreak())

    # HALAMAN 3 - evaluation
    section("Evaluasi numerik mutu (simulasi)")
    add(f"Asumsi: setiap hasil uji berasal dari 2 silinder diameter 150 mm berumur 28 hari. "
        f"Rata-rata setiap 3 hasil uji berturut-turut >= f'c {_number(h.mutu_rencana)} MPa, "
        f"dan setiap hasil uji >= {_number(h.evaluasi['batas_uji_MPa'].iloc[0])} MPa. "
        "Urutan memakai kolom urutan_uji jika tersedia; jika tidak, berdasarkan ID pengujian. ","K4Body")
    eval_rows=[]
    for _,r in h.evaluasi.iterrows():
        eval_rows.append([r["campuran"],str(int(r["jumlah_uji"])),_number(r["rata_3_terendah_MPa"]),_number(r["uji_terendah_MPa"]),r["status"]])
    story.append(_table(["Campuran","n Uji","Min rata 3 (MPa)","Min hasil (MPa)","Status simulasi"],eval_rows,[80,56,116,110,161],s))
    story.append(Spacer(1,8*mm))
    section("Jendela tiga hasil uji berurutan")
    if h.jendela_tiga_uji.empty:
        add("Belum ada rangkaian tiga hasil uji pada campuran mana pun.")
    else:
        windows=[]
        for _,r in h.jendela_tiga_uji.iterrows():
            windows.append([r["campuran"],r["rentang_uji"],_number(r["rata_3_uji_MPa"]),"Ya" if r["memenuhi_rata"] else "Tidak"])
        story.append(_table(["Campuran","ID pengujian berurutan","Rata-rata (MPa)","Mencapai target"],windows,[83,220,114,106],s))
    story.append(Spacer(1,8*mm))
    section("Catatan pengendalian mutu")
    add(f"Penapisan outlier: {k['indikasi_outlier']} indikasi dengan aturan ±2 simpangan baku per campuran (minimal 5 silinder). Indikasi bukan alasan otomatis menghapus data.")
    if h.peringatan:
        for i, warning in enumerate(h.peringatan[:6],1):
            add(f"{i}. {warning}","K4Small")
    else:
        add("Tidak ada peringatan format atau asumsi tambahan pada input.","K4Small")
    story.append(Spacer(1,5*mm))
    section("Rekap hasil uji (rata-rata pasangan)")
    testrows=[[r["campuran"],r["id_pengujian"],str(int(r["jumlah_silinder"])),_number(r["kuat_tekan_uji_MPa"])] for _,r in h.rekap_uji.iterrows()]
    story.append(_table(["Campuran","ID uji","Jumlah silinder","Kuat tekan uji (MPa)"],testrows,[100,110,146,167],s))
    story.append(Spacer(1,7*mm))
    story.append(PageBreak())

    # HALAMAN 4 dan selanjutnya - tables
    section("Data rinci seluruh benda uji")
    add("Luas dihitung dengan A = pi x d^2 / 4 (mm2), fc = P x 1000 / A (MPa).", "K4Small")
    rows=[]
    for _,r in h.benda_uji.iterrows():
        rows.append([r["id_benda_uji"],r["campuran"],r["id_pengujian"],_number(r["umur_hari"],0),_number(r["diameter_mm"],0),_number(r["beban_maksimum_kN"],1),_number(r["kuat_tekan_MPa"]),"Ya" if r["status_target"]=="Mencapai target" else "Tidak"])
    story.append(_table(["ID","Mix","ID Uji","Hari","Ø mm","Beban kN","fc MPa",">= Target"],rows,[59,35,70,44,52,91,88,84],s))
    story.append(Spacer(1,8*mm))
    add("VERIFIKASI KOMPUTASI", "K4H2")
    add("Hasil kuat tekan diuji ulang secara numerik terhadap rumus P/A untuk seluruh baris, dan jumlah silinder pada rekap diperiksa sama dengan data input. Pemeriksaan ini bukan validasi alat uji atau mutu beton lapangan.","K4Small")
    doc.build(story, onFirstPage=_draw_page, onLaterPages=_draw_page)
    return out.getvalue()


def buat_zip(h: HasilAnalisis, pdf_bytes: bytes, gambar: dict[str,bytes], nama_proyek: str = "K4 ConcreteLab Pro") -> bytes:
    """Bundel seluruh hasil terbaru tanpa menyimpan data pengguna di server."""
    output=BytesIO()
    files={
        "data/input_tervalidasi.csv":h.input_data,
        "hasil/hasil_kuat_tekan.csv":h.benda_uji,
        "hasil/statistik_campuran.csv":h.statistik,
        "hasil/rekap_pengujian.csv":h.rekap_uji,
        "hasil/evaluasi_simulasi.csv":h.evaluasi,
        "hasil/jendela_tiga_uji.csv":h.jendela_tiga_uji,
        "hasil/audit_input.csv":audit_csv(h.input_data),
    }
    manifest={
        "versi_aplikasi":"2.0",
        "audit_input":audit_counts(audit_csv(h.input_data)),
        "nama_proyek":nama_proyek,
        "dibuat_pada":datetime.now().isoformat(timespec="seconds"),
        "mutu_rencana_MPa":h.mutu_rencana,
        "sumber_data":h.sumber_data,
        "sha256_input":h.hash_sumber,
        "ringkasan":h.ringkasan,
        "peringatan":h.peringatan,
        "keterangan":"SIMULASI DATA K4, bukan sertifikat penerimaan beton laboratorium.",
    }
    with ZipFile(output,"w",ZIP_DEFLATED) as z:
        for name, df in files.items():
            z.writestr(name,df.to_csv(index=False).encode("utf-8-sig"))
        for name,b in gambar.items():
            z.writestr("grafik/"+name,b)
        z.writestr("hasil/Laporan_Otomatis_K4_Beton.pdf",pdf_bytes)
        z.writestr("ringkasan_metadata.json",json.dumps(manifest,ensure_ascii=False,indent=2))
        z.writestr("BACA_SAYA.txt","K4 ConcreteLab Pro - paket hasil analisis otomatis.\nInput dan angka mengikuti CSV terakhir saat analisis.\nHasil evaluasi mutu hanya simulasi pendidikan, bukan sertifikat laboratorium.\n")
    return output.getvalue()
