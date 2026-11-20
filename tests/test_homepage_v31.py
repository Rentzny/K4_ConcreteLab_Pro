"""Regresi struktur homepage; tidak membutuhkan server Streamlit atau browser."""
from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]
HOME = ROOT / "app_pages" / "home.py"


def test_homepage_python_syntax():
    ast.parse(HOME.read_text(encoding="utf-8"))


def test_beranda_link_terhubung_ke_halaman_yang_ada():
    source = HOME.read_text(encoding="utf-8")
    assert 'st.switch_page("app_pages/service.py")' in source
    assert 'st.page_link("app_pages/about.py"' in source
    assert (ROOT / "app_pages" / "service.py").is_file()
    assert (ROOT / "app_pages" / "about.py").is_file()


def test_homepage_tidak_menampilkan_data_ilustratif():
    source = HOME.read_text(encoding="utf-8")
    assert "st.file_uploader(" not in source
    assert "st.bar_chart(" not in source
    assert "st.line_chart(" not in source
    assert "pd.read_csv(" not in source
    assert "st.dataframe(" not in source
    assert "st.session_state.clear(" not in source


def test_homepage_tanpa_animasi():
    source = HOME.read_text(encoding="utf-8")
    assert "@keyframes" not in source
    assert "animation:" not in source
    assert "autoplay" not in source


def test_menu_tetap_beranda_service_about():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    for nav in ['title="Beranda"', 'title="Service"', 'title="About"']:
        assert nav in app
    assert 'position="top"' in app
