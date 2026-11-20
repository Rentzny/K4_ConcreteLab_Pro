"""Ekspor PDF profesional dan paket ZIP yang mengikuti HasilAnalisis terkini."""
from __future__ import annotations

from datetime import datetime
from hashlib import sha256
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
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.barcode.qr import QrCodeWidget

from .engine import HasilAnalisis
from .plots import semua_grafik
from .quality import audit_csv, audit_counts
from .advanced import statistik_lanjutan, sensitivitas_target, rekap_sensitivitas_target
from .professional import ringkasan_eksekutif, tabel_kinerja, interpretasi_per_campuran

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


def _report_id(h: HasilAnalisis, nama_proyek: str) -> str:
    canonical = sha256(h.input_data.to_csv(index=False).encode("utf-8")).hexdigest()
    payload = f"{canonical}|{h.mutu_rencana:.6f}|{nama_proyek.strip()}".encode("utf-8")
    return "K4-" + sha256(payload).hexdigest()[:12].upper()


def _qr_drawing(payload: str, mm_size: float = 46) -> Drawing:
    """Kode QR offline untuk fingerprint; tidak merupakan sertifikat digital."""
    widget = QrCodeWidget(payload)
    x1, y1, x2, y2 = widget.getBounds()
    size = mm_size * mm
    draw = Drawing(size, size, transform=[size/(x2-x1), 0, 0, size/(y2-y1), -x1*size/(x2-x1), -y1*size/(y2-y1)])
    draw.add(widget)
    return draw


def _draw_page(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(NAVY)
    canvas.rect(0,H-14*mm,W,14*mm,fill=1,stroke=0)
    canvas.setFont("Helvetica-Bold",8.2)
    canvas.setFillColor(colors.white)
    canvas.drawString(16*mm,H-9.1*mm,"K4 | CONCRETELAB PRO 4.0")
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

    # HALAMAN 1 — Ikhtisar profesional; seluruh angka dari CSV aktif.
    ex = ringkasan_eksekutif(h)
    k=h.ringkasan
    story.append(Spacer(1,5*mm))
    add("LAPORAN TEKNIS | ANALISIS KUAT TEKAN", "K4Subtitle")
    add("CONCRETE STRENGTH ANALYSIS", "K4Title")
    add(nama_proyek, "K4Subtitle")
    add("Versi 4.0 • data dinamis • laporan simulasi, bukan sertifikat laboratorium", "K4Small")
    story.append(Spacer(1,6*mm))
    labels=[(str(ex.jumlah_silinder),"BENDA UJI"),(str(ex.jumlah_uji),"HASIL UJI"),
            (_number(ex.rata_rata_mpa),"RERATA (MPa)"),(_number(ex.target_mpa),"TARGET (MPa)")]
    area=W-32*mm
    kp=Table([[_kpi(val,lbl,area/4,s) for val,lbl in labels]],colWidths=[area/4]*4)
    kp.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),3),
                            ("RIGHTPADDING",(0,0),(-1,-1),3)]))
    story.append(kp)
    story.append(Spacer(1,7*mm))
    section("01  Ringkasan eksekutif")
    add(ex.deskripsi)
    add(f"Pencapaian target individual: {_number(ex.persen_silinder_target,1)}% silinder. "
        f"Hasil simulasi campuran: {ex.campuran_memenuhi} memenuhi, "
        f"{ex.campuran_belum_memenuhi} belum memenuhi, "
        f"{ex.campuran_tidak_dapat_dinilai} tidak dapat dievaluasi.")
    section("02  Kinerja setiap campuran")
    perform=tabel_kinerja(h)
    rows=[[r['campuran'],str(int(r['jumlah_silinder'])),_number(r['rata_rata_MPa']),
           _number(r['cv_persen']),_number(r['pencapaian_target_persen'],1)+"%",
           str(r['status_simulasi'])] for _,r in perform.head(7).iterrows()]
    story.append(_table(["Mix","n","Rerata (MPa)","CV (%)","Target silinder","Simulasi numerik"],
                        rows,[43,31,92,61,100,196],s))
    if len(perform)>7:
        add(f"Tabel menampilkan 7 dari {len(perform)} campuran. Seluruh data terdapat pada CSV kinerja di paket ZIP.","K4Small")
    story.append(Spacer(1,5*mm))
    section("03  Catatan teknis")
    add("Campuran dengan rata-rata silinder tertinggi adalah "
        f"{ex.campuran_rata_tertinggi} ({_number(ex.rerata_tertinggi_mpa)} MPa). "
        "Peringkat berdasarkan rerata saja tidak membuktikan kepatuhan mutu maupun kelayakan rancangan campuran.")
    add("Perbedaan antara 'silinder mencapai target' dan 'hasil uji memenuhi simulasi' "
        "harus dipertahankan; tidak boleh dipakai bergantian.", "K4Small")
    if h.peringatan:
        add("Catatan validasi: " + "; ".join(h.peringatan[:2]),"K4Small")
    add(f"Sumber: {h.sumber_data} | Dibuat: {datetime.now():%d-%m-%Y %H:%M}","K4Small")
    add(f"ID laporan: {_report_id(h,nama_proyek)} | Penanggung jawab: {penanggung_jawab}","K4Small")
    story.append(PageBreak())

    # HALAMAN 2 — Grafik ringkas untuk pembaca nonteknis.
    section("04  Analisis visual: distribusi dan rerata")
    add("Garis acuan menunjukkan target pilihan pengguna, bukan batas otomatis penerimaan beton.","K4Small")
    for filename, caption in [("histogram.png","Distribusi kuat tekan setiap silinder"),
                              ("perbandingan_rata_rata.png","Rerata campuran dan variasi sampel (±SD)")]:
        add(caption,"K4H2")
        story.append(Image(BytesIO(grafik[filename]),width=165*mm,height=69*mm))
        story.append(Spacer(1,4*mm))
    story.append(PageBreak())

    # HALAMAN 3 — Grafik lanjutan.
    section("05  Analisis visual: variasi &amp; tren")
    add("Plot data per campuran dan tren hasil uji membantu eksplorasi, bukan pengesahan mutu.","K4Small")
    for filename, caption in [("boxplot_campuran.png","Sebaran dan variasi hasil silinder"),
                              ("tren_pengujian.png","Tren per urutan pengujian")]:
        add(caption,"K4H2")
        story.append(Image(BytesIO(grafik[filename]),width=165*mm,height=69*mm))
        story.append(Spacer(1,4*mm))
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
    story.append(PageBreak())
    section("Identitas & verifikasi arsip")
    report_id = _report_id(h, nama_proyek)
    add("Kode identifikasi berikut dibuat dari isi CSV, target mutu, dan nama proyek. "
        "Scan QR untuk membaca ID dan SHA-256; pemilik data dapat mencocokkan arsip proyek di aplikasi.")
    story.append(Spacer(1, 8*mm))
    canonical_hash = sha256(h.input_data.to_csv(index=False).encode("utf-8")).hexdigest()
    qr_payload = f"K4-CONCRETELAB|REPORT={report_id}|CSV-SHA256={canonical_hash}|TARGET={h.mutu_rencana:g}MPa"
    story.append(_qr_drawing(qr_payload))
    story.append(Spacer(1, 7*mm))
    add(f"ID laporan: {report_id}", "K4H2")
    add(f"SHA-256 CSV ternormalisasi (hex): {canonical_hash}", "K4Small")
    add(f"Target simulasi: {_number(h.mutu_rencana)} MPa", "K4Small")
    add("PENTING: QR dan checksum hanya membantu mendeteksi perubahan data setelah arsip dibuat. "
        "Kode ini BUKAN tanda tangan digital, bukan verifikasi identitas laboratorium, "
        "dan bukan keputusan penerimaan beton.", "K4Small")
    doc.build(story, onFirstPage=_draw_page, onLaterPages=_draw_page)
    return out.getvalue()


def buat_zip(h: HasilAnalisis, pdf_bytes: bytes, gambar: dict[str,bytes], nama_proyek: str = "K4 ConcreteLab Pro") -> bytes:
    """Bundel seluruh hasil terbaru tanpa menyimpan data pengguna di server."""
    output=BytesIO()
    # Hasil tambahan v2.2 diturunkan dari data utama yang sama.
    tgt_start = max(1.0, float(h.mutu_rencana) - 10.0)
    tgt_end = min(150.0, float(h.mutu_rencana) + 10.0)
    target_grid = sorted({round(tgt_start + (tgt_end-tgt_start)*i/40, 3) for i in range(41)} | {float(h.mutu_rencana)})
    target_detail = sensitivitas_target(h, target_grid)
    files={
        "data/input_tervalidasi.csv":h.input_data,
        "hasil/hasil_kuat_tekan.csv":h.benda_uji,
        "hasil/statistik_campuran.csv":h.statistik,
        "hasil/rekap_pengujian.csv":h.rekap_uji,
        "hasil/evaluasi_simulasi.csv":h.evaluasi,
        "hasil/jendela_tiga_uji.csv":h.jendela_tiga_uji,
        "hasil/audit_input.csv":audit_csv(h.input_data),
        "hasil/statistik_lanjutan_silinder.csv":statistik_lanjutan(h, "silinder"),
        "hasil/statistik_lanjutan_per_pengujian.csv":statistik_lanjutan(h, "hasil_uji"),
        "hasil/sensitivitas_target_mutu.csv":target_detail,
        "hasil/rekap_sensitivitas_target.csv":rekap_sensitivitas_target(target_detail),
        "hasil/ringkasan_kinerja_profesional.csv":tabel_kinerja(h),
    }
    manifest={
        "versi_aplikasi":"4.0",
        "audit_input":audit_counts(audit_csv(h.input_data)),
        "nama_proyek":nama_proyek,
        "dibuat_pada":datetime.now().isoformat(timespec="seconds"),
        "mutu_rencana_MPa":h.mutu_rencana,
        "sumber_data":h.sumber_data,
        "sha256_input":h.hash_sumber,
        "id_laporan":_report_id(h,nama_proyek),
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
        summary=ringkasan_eksekutif(h)
        notes="\n".join([summary.judul,summary.deskripsi,"",*interpretasi_per_campuran(h),"",*summary.catatan])
        z.writestr("hasil/Ringkasan_Eksekutif.txt",notes.encode("utf-8"))
        z.writestr("ringkasan_metadata.json",json.dumps(manifest,ensure_ascii=False,indent=2))
        z.writestr("BACA_SAYA.txt","K4 ConcreteLab Pro - paket hasil analisis otomatis.\nInput dan angka mengikuti CSV terakhir saat analisis.\nHasil evaluasi mutu hanya simulasi pendidikan, bukan sertifikat laboratorium.\n")
    return output.getvalue()
