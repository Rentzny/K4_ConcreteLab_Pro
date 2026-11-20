"""Arsip proyek K4 portabel, verifikasi SHA-256, dan riwayat SQLite khusus lokal.

Tidak menandatangani dokumen digital. ZIP proyek bukan bukti keaslian data laboratorium.
Tidak ada upload server permanen; SQLite hanya jika admin lokal mengaktifkannya.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
import hashlib
import json
import math
import re
import sqlite3
from uuid import uuid4
from zipfile import BadZipFile, ZipFile, ZIP_DEFLATED

from .engine import HasilAnalisis, read_csv, analisis

APP_VERSION = "3.0"
SCHEMA_VERSION = 1
MAX_ARCHIVE_BYTES = 25 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 38 * 1024 * 1024
MAX_CSV_BYTES = 10 * 1024 * 1024
_ALLOWED_MEMBERS = {"manifest.json", "data/input.csv", "report/Laporan_K4_Beton.pdf"}


class ProjectArchiveError(ValueError):
    """Arsip proyek rusak, tidak valid, atau gagal verifikasi."""


@dataclass(frozen=True)
class ProjectArchive:
    metadata: dict
    csv_bytes: bytes
    pdf_bytes: bytes | None


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def report_id_for(h: HasilAnalisis, nama_proyek: str) -> str:
    """ID deterministik per dataset, mutu, dan nama proyek; bukan tanda tangan."""
    canonical = sha256(h.input_data.to_csv(index=False).encode("utf-8"))
    payload = f"{canonical}|{h.mutu_rencana:.6f}|{nama_proyek.strip()}".encode("utf-8")
    return "K4-" + sha256(payload)[:12].upper()


def _text(value: str, label: str, max_len: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > max_len:
        raise ProjectArchiveError(f"{label} harus berupa teks 1–{max_len} karakter.")
    return value.strip()


def buat_arsip_proyek(
    h: HasilAnalisis,
    *,
    nama_proyek: str,
    penanggung_jawab: str,
    catatan: str = "",
    pdf_bytes: bytes | None = None,
) -> bytes:
    """Buat arsip versi proyek (.k4proj.zip), lengkap dengan fingerprint setiap berkas."""
    nama = _text(nama_proyek, "Nama proyek", 110)
    owner = _text(penanggung_jawab, "Penanggung jawab", 85)
    if not isinstance(catatan, str) or len(catatan) > 1000:
        raise ProjectArchiveError("Catatan maksimal 1000 karakter.")
    csv_bytes = h.input_data.to_csv(index=False).encode("utf-8-sig")
    if len(csv_bytes) > MAX_CSV_BYTES:
        raise ProjectArchiveError("CSV terlalu besar untuk arsip (maksimal 10 MB).")
    if pdf_bytes is not None and (not isinstance(pdf_bytes, bytes) or not pdf_bytes.startswith(b"%PDF-") or len(pdf_bytes) > 15 * 1024 * 1024):
        raise ProjectArchiveError("PDF tidak valid atau melebihi 15 MB.")
    files: dict[str, bytes] = {"data/input.csv": csv_bytes}
    if pdf_bytes is not None:
        files["report/Laporan_K4_Beton.pdf"] = pdf_bytes
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "app_version": APP_VERSION,
        "id_arsip": str(uuid4()),
        "id_laporan": report_id_for(h, nama),
        "dibuat_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "nama_proyek": nama,
        "penanggung_jawab": owner,
        "catatan": catatan,
        "target_MPa": float(h.mutu_rencana),
        "jumlah_silinder": int(h.ringkasan["silinder"]),
        "jumlah_campuran": int(h.ringkasan["campuran"]),
        "jumlah_pengujian": int(h.ringkasan["jumlah_uji"]),
        "sumber": str(h.sumber_data)[:500],
        "files_sha256": {filename: sha256(blob) for filename, blob in files.items()},
        "peringatan": "Arsip bukan bukti keaslian data, sertifikat, atau tanda tangan digital.",
    }
    out = BytesIO()
    with ZipFile(out, "w", ZIP_DEFLATED, compresslevel=6) as z:
        for filename, blob in files.items():
            z.writestr(filename, blob)
        z.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8"))
    result = out.getvalue()
    if len(result) > MAX_ARCHIVE_BYTES:
        raise ProjectArchiveError("Ukuran arsip melebihi batas 25 MB.")
    return result


def baca_arsip_proyek(data: bytes) -> ProjectArchive:
    """Baca ZIP dengan pembatasan ukuran, whitelist anggota, hash, dan verifikasi komputasi."""
    if not isinstance(data, bytes) or len(data) == 0 or len(data) > MAX_ARCHIVE_BYTES:
        raise ProjectArchiveError("Ukuran arsip tidak valid (maksimal 25 MB).")
    try:
        with ZipFile(BytesIO(data), "r") as z:
            infos = z.infolist()
            names = [entry.filename for entry in infos]
            if len(infos) > 3 or len(set(names)) != len(names) or not {"manifest.json", "data/input.csv"}.issubset(names):
                raise ProjectArchiveError("Struktur arsip tidak lengkap atau memiliki nama file duplikat.")
            if any(name not in _ALLOWED_MEMBERS for name in names):
                raise ProjectArchiveError("Arsip mengandung file tidak diizinkan.")
            if sum(entry.file_size for entry in infos) > MAX_UNCOMPRESSED_BYTES:
                raise ProjectArchiveError("Arsip terkompresi berisi data terlalu besar.")
            if next(entry.file_size for entry in infos if entry.filename == "data/input.csv") > MAX_CSV_BYTES:
                raise ProjectArchiveError("CSV melebihi batas 10 MB.")
            if any(entry.flag_bits & 1 for entry in infos):
                raise ProjectArchiveError("Arsip terenkripsi tidak didukung.")
            try:
                manifest = json.loads(z.read("manifest.json"))
            except (UnicodeDecodeError, json.JSONDecodeError, TypeError) as e:
                raise ProjectArchiveError("Manifest JSON rusak.") from e
            if not isinstance(manifest, dict) or type(manifest.get("schema_version")) is not int or manifest["schema_version"] != SCHEMA_VERSION:
                raise ProjectArchiveError("Versi skema arsip tidak didukung.")
            for label, limit in [("nama_proyek",110),("penanggung_jawab",85),("id_laporan",30),("id_arsip",60)]:
                _text(manifest.get(label), label, limit)
            if not re.fullmatch(r"[0-9a-f-]{36}", manifest["id_arsip"]):
                raise ProjectArchiveError("ID arsip tidak sah.")
            tgt = manifest.get("target_MPa")
            if type(tgt) not in (float, int) or not math.isfinite(tgt) or not 0 < tgt <= 150:
                raise ProjectArchiveError("Target mutu pada manifest tidak valid.")
            digests = manifest.get("files_sha256")
            if not isinstance(digests, dict) or set(digests) != set(names)-{"manifest.json"}:
                raise ProjectArchiveError("Daftar hash berkas tidak konsisten.")
            contents = {}
            for name in set(names)-{"manifest.json"}:
                if not re.fullmatch(r"[0-9a-f]{64}", str(digests[name])):
                    raise ProjectArchiveError("Format SHA-256 tidak valid.")
                blob = z.read(name)
                if sha256(blob) != digests[name]:
                    raise ProjectArchiveError(f"Integritas berkas gagal: {name} berubah.")
                contents[name] = blob
    except (BadZipFile, OSError, EOFError, RuntimeError, ValueError, KeyError) as exc:
        if isinstance(exc, ProjectArchiveError):
            raise
        raise ProjectArchiveError("Arsip ZIP rusak atau format tidak sesuai.") from exc

    csv_bytes = contents["data/input.csv"]
    try:
        df = read_csv(csv_bytes)
        h = analisis(df, float(tgt))
    except Exception as exc:
        raise ProjectArchiveError("CSV dalam arsip tidak dapat dianalisis secara valid.") from exc
    if (type(manifest.get("jumlah_silinder")) is not int
        or type(manifest.get("jumlah_campuran")) is not int
        or type(manifest.get("jumlah_pengujian")) is not int
        or manifest["jumlah_silinder"] != h.ringkasan["silinder"]
        or manifest["jumlah_campuran"] != h.ringkasan["campuran"]
        or manifest["jumlah_pengujian"] != h.ringkasan["jumlah_uji"]
        or manifest["id_laporan"] != report_id_for(h, manifest["nama_proyek"])):
        raise ProjectArchiveError("Ringkasan/ID laporan tidak cocok dengan perhitungan ulang data.")
    pdf_bytes = contents.get("report/Laporan_K4_Beton.pdf")
    if pdf_bytes is not None and not pdf_bytes.startswith(b"%PDF-"):
        raise ProjectArchiveError("File PDF dalam arsip tidak valid.")
    return ProjectArchive(manifest, csv_bytes, pdf_bytes)


class LocalHistoryStore:
    """SQLite OPSIONAL untuk instalasi pribadi; JANGAN gunakan pada website publik tanpa login."""

    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._db() as connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS k4_history (
                id_arsip TEXT PRIMARY KEY,
                dibuat_utc TEXT NOT NULL,
                nama_proyek TEXT NOT NULL,
                target_MPa REAL NOT NULL,
                sha256_arsip TEXT NOT NULL,
                arsip BLOB NOT NULL
            )""")

    def _db(self):
        return sqlite3.connect(str(self.path), timeout=10)

    def save(self, blob: bytes) -> str:
        snapshot = baca_arsip_proyek(blob)
        meta = snapshot.metadata
        with self._db() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO k4_history VALUES (?, ?, ?, ?, ?, ?)",
                (meta["id_arsip"], meta["dibuat_utc"], meta["nama_proyek"], meta["target_MPa"], sha256(blob), blob),
            )
        return meta["id_arsip"]

    def list(self, limit: int = 50) -> list[dict]:
        with self._db() as connection:
            rows = connection.execute(
                "SELECT id_arsip,dibuat_utc,nama_proyek,target_MPa FROM k4_history "
                "ORDER BY dibuat_utc DESC, id_arsip DESC LIMIT ?", (max(1, min(200, int(limit))),)
            ).fetchall()
        return [dict(zip(("id_arsip", "dibuat_utc", "nama_proyek", "target_MPa"), row)) for row in rows]

    def load(self, id_arsip: str) -> bytes:
        with self._db() as connection:
            result = connection.execute("SELECT arsip,sha256_arsip FROM k4_history WHERE id_arsip=?", (id_arsip,)).fetchone()
        if result is None:
            raise ProjectArchiveError("Arsip tidak ditemukan pada riwayat lokal.")
        blob, expected = result
        if sha256(blob) != expected:
            raise ProjectArchiveError("Arsip di database telah berubah/rusak.")
        baca_arsip_proyek(blob)
        return blob
