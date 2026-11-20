"""Pengujian keamanan/portabilitas arsip proyek v3.0."""
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import json

import pandas as pd
import pytest
from pypdf import PdfReader

from concretelab.engine import analisis
from concretelab.projects import (
    buat_arsip_proyek, baca_arsip_proyek, report_id_for, sha256,
    ProjectArchiveError, LocalHistoryStore,
)
from concretelab.reporting import buat_pdf, buat_zip

DATA = Path(__file__).resolve().parents[1] / "data" / "contoh_18_silinder.csv"


@pytest.fixture
def result():
    return analisis(pd.read_csv(DATA), 30.0, sumber="Data ilustratif")


@pytest.fixture
def archive(result):
    pdf = buat_pdf(result, nama_proyek="Lab K4", penanggung_jawab="Kelompok K4")
    return buat_arsip_proyek(result, nama_proyek="Lab K4", penanggung_jawab="Kelompok K4",
                            catatan="Uji versi", pdf_bytes=pdf)


def _rewrite_zip(original: bytes, changes: dict[str, bytes | None]) -> bytes:
    target = BytesIO()
    with ZipFile(BytesIO(original)) as old, ZipFile(target, "w", ZIP_DEFLATED) as z:
        for name in old.namelist():
            if name in changes and changes[name] is None:
                continue
            z.writestr(name, changes.get(name, old.read(name)))
        for name, data in changes.items():
            if name not in old.namelist() and data is not None:
                z.writestr(name, data)
    return target.getvalue()


def test_roundtrip_archive(result, archive):
    item = baca_arsip_proyek(archive)
    assert item.metadata["nama_proyek"] == "Lab K4"
    assert item.metadata["target_MPa"] == 30
    assert item.metadata["jumlah_silinder"] == 18
    assert item.metadata["jumlah_campuran"] == 3
    assert item.metadata["id_laporan"] == report_id_for(result, "Lab K4")
    assert item.metadata["files_sha256"]["data/input.csv"] == sha256(item.csv_bytes)
    assert len(pd.read_csv(BytesIO(item.csv_bytes))) == 18
    assert item.pdf_bytes and item.pdf_bytes.startswith(b"%PDF-")
    assert len(PdfReader(BytesIO(item.pdf_bytes)).pages) == 5


def test_recompute_after_data_edit(result):
    changed = result.input_data.copy()
    changed.loc[changed.id_benda_uji.eq("U01"), "beban_maksimum_kN"] = 550
    another = analisis(changed, 30)
    archive = buat_arsip_proyek(another, nama_proyek="Lab K4", penanggung_jawab="Kelompok")
    item = baca_arsip_proyek(archive)
    assert item.metadata["jumlah_silinder"] == 18
    assert item.metadata["id_laporan"] != report_id_for(result, "Lab K4")
    assert item.pdf_bytes is None


def test_pdf_qr_and_id_are_present(result):
    blob = buat_pdf(result, nama_proyek="Lab K4")
    doc = PdfReader(BytesIO(blob))
    assert len(doc.pages) == 5
    last = doc.pages[-1].extract_text()
    assert "Identitas & verifikasi arsip" in last
    assert report_id_for(result, "Lab K4") in last
    assert "BUKAN tanda tangan digital" in last


def test_zip_export_v3(result):
    pdf = buat_pdf(result)
    bundle = buat_zip(result, pdf, {})
    with ZipFile(BytesIO(bundle)) as z:
        metadata = json.loads(z.read("ringkasan_metadata.json"))
        assert metadata["versi_aplikasi"] == "3.0"
        assert "id_laporan" in metadata


def test_tampered_csv_is_detected(archive):
    with ZipFile(BytesIO(archive)) as z:
        raw = z.read("data/input.csv")
    changed = _rewrite_zip(archive, {"data/input.csv": raw.replace(b"500", b"550", 1)})
    with pytest.raises(ProjectArchiveError, match="Integritas"):
        baca_arsip_proyek(changed)


def test_manifest_summary_tampering_is_detected(archive):
    with ZipFile(BytesIO(archive)) as z:
        manifest = json.loads(z.read("manifest.json"))
    manifest["jumlah_silinder"] = 999
    changed = _rewrite_zip(archive, {"manifest.json": json.dumps(manifest).encode()})
    with pytest.raises(ProjectArchiveError, match="Ringkasan"):
        baca_arsip_proyek(changed)


def test_manifest_report_id_tampering_is_detected(archive):
    with ZipFile(BytesIO(archive)) as z:
        manifest = json.loads(z.read("manifest.json"))
    manifest["id_laporan"] = "K4-UNTRUSTED"
    changed = _rewrite_zip(archive, {"manifest.json": json.dumps(manifest).encode()})
    with pytest.raises(ProjectArchiveError):
        baca_arsip_proyek(changed)


def test_extra_or_traversal_file_rejected(archive):
    with pytest.raises(ProjectArchiveError):
        baca_arsip_proyek(_rewrite_zip(archive, {"../../danger.py": b"x"}))


def test_invalid_archive_and_size_rejected():
    for data in (b"", b"not zip", b"x" * (25 * 1024 * 1024 + 1)):
        with pytest.raises(ProjectArchiveError):
            baca_arsip_proyek(data)


def test_missing_input_rejected(archive):
    with pytest.raises(ProjectArchiveError):
        baca_arsip_proyek(_rewrite_zip(archive, {"data/input.csv": None}))


def test_invalid_project_name_and_bad_pdf(result):
    with pytest.raises(ProjectArchiveError):
        buat_arsip_proyek(result, nama_proyek=" ", penanggung_jawab="X")
    with pytest.raises(ProjectArchiveError):
        buat_arsip_proyek(result, nama_proyek="X", penanggung_jawab="X", pdf_bytes=b"invalid")


def test_local_history_persists_and_checks_hash(archive, tmp_path):
    store = LocalHistoryStore(tmp_path / "local" / "history.sqlite3")
    key = store.save(archive)
    assert store.load(key) == archive
    assert store.list()[0]["nama_proyek"] == "Lab K4"
    # A corrupted BLOB must never be sent back to users.
    with store._db() as db:
        db.execute("UPDATE k4_history SET arsip=? WHERE id_arsip=?", (b"tampered", key))
    with pytest.raises(ProjectArchiveError, match="berubah"):
        store.load(key)


def test_unavailable_local_id(tmp_path):
    store = LocalHistoryStore(tmp_path / "history.sqlite3")
    with pytest.raises(ProjectArchiveError, match="tidak ditemukan"):
        store.load("none")
