"""Uji modul statistik lanjutan dan sensitivitas target mutu."""
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from concretelab.engine import analisis, DataValidationError
from concretelab.advanced import (
    statistik_lanjutan, sensitivitas_target, rekap_sensitivitas_target,
)

DATA = Path(__file__).resolve().parents[1] / "data" / "contoh_18_silinder.csv"


@pytest.fixture
def result():
    return analisis(pd.read_csv(DATA), 30.0, sumber="Data ilustratif")


def test_basic_extended_statistics(result):
    table = statistik_lanjutan(result)
    assert len(table) == 3
    assert table["n"].tolist() == [6, 6, 6]
    assert table.set_index("campuran").loc["B", "mean_MPa"] == pytest.approx(33.10, abs=0.02)
    assert (table["q1_MPa"] <= table["median_MPa"]).all()
    assert (table["median_MPa"] <= table["q3_MPa"]).all()
    assert (table["iqr_MPa"] >= 0).all()
    assert table["ci95_rerata_bawah_MPa"].notna().all()
    assert (table["ci95_rerata_bawah_MPa"] <= table["ci95_rerata_atas_MPa"]).all()


def test_bootstrap_deterministic(result):
    a = statistik_lanjutan(result, bootstrap_iterasi=600, seed=123)
    b = statistik_lanjutan(result, bootstrap_iterasi=600, seed=123)
    pd.testing.assert_frame_equal(a, b)


def test_test_result_level_does_not_claim_unavailable_ci(result):
    table = statistik_lanjutan(result, tingkat="hasil_uji")
    assert table["n"].tolist() == [3, 3, 3]
    assert table["ci95_rerata_bawah_MPa"].isna().all()
    assert table["ci95_rerata_atas_MPa"].isna().all()


def test_single_sample_nan_sd_and_ci(result):
    df = result.input_data[result.input_data.campuran.eq("A")].iloc[:1].copy()
    one = analisis(df, 30.0)
    stats = statistik_lanjutan(one)
    assert stats.iloc[0].n == 1
    assert np.isnan(stats.iloc[0].sd_MPa)
    assert np.isnan(stats.iloc[0].ci95_rerata_bawah_MPa)


def test_invalid_level_and_bootstrap_args(result):
    with pytest.raises(ValueError):
        statistik_lanjutan(result, tingkat="none")
    with pytest.raises(ValueError):
        statistik_lanjutan(result, bootstrap_iterasi=199)


def test_target_sweep_values(result):
    df = sensitivitas_target(result, [25, 30, 35, 40])
    assert len(df) == 12
    cur = df[df.target_MPa.eq(30)].set_index("campuran")
    assert cur.loc["B", "status_simulasi"] == "Memenuhi simulasi"
    assert cur.loc["A", "status_simulasi"] == "Belum memenuhi simulasi"
    assert cur.loc["C", "status_simulasi"] == "Belum memenuhi simulasi"
    assert cur.loc["B", "persen_silinder_capai_target"] == pytest.approx(100)
    assert cur.loc["C", "persen_silinder_capai_target"] == pytest.approx(0)


def test_target_sweep_monotonic_pass_rate(result):
    v = sensitivitas_target(result, list(np.arange(15, 45, 2.5)))
    for _, mix in v.groupby("campuran"):
        assert (mix["persen_silinder_capai_target"].diff().fillna(0) <= 1e-7).all()


def test_target_sweep_no_input_mutation(result):
    original = result.input_data.copy(deep=True)
    original_evaluasi = result.evaluasi.copy(deep=True)
    sensitivitas_target(result, [20, 30, 40])
    pd.testing.assert_frame_equal(result.input_data, original)
    pd.testing.assert_frame_equal(result.evaluasi, original_evaluasi)


def test_undecidable_not_conflated_with_fail(result):
    only_two_tests = result.input_data[result.input_data.id_pengujian.isin(["A01", "A02"])].copy()
    short = analisis(only_two_tests, 30.0)
    df = sensitivitas_target(short, [25, 30, 40])
    assert set(df.status_simulasi) == {"Tidak dapat dievaluasi"}
    summary = rekap_sensitivitas_target(df)
    assert (summary.tidak_dapat_dievaluasi == 1).all()
    assert (summary.belum_memenuhi_simulasi == 0).all()


def test_invalid_sweep_values(result):
    for targets in ([], [0], [151], [float('nan')], [float('inf')], ['bad'], range(1, 303)):
        with pytest.raises(DataValidationError):
            sensitivitas_target(result, targets)


def test_duplicate_targets_removed(result):
    df = sensitivitas_target(result, [30, 30, 20])
    assert df.target_MPa.nunique() == 2


def test_summary_weighted_percentage(result):
    out = sensitivitas_target(result, [25, 30, 35])
    s = rekap_sensitivitas_target(out)
    assert len(s) == 3
    assert s.loc[s.target_MPa.eq(30), "jumlah_campuran"].iloc[0] == 3
    assert s.loc[s.target_MPa.eq(30), "memenuhi_simulasi"].iloc[0] == 1
    assert ((s.persen_silinder_capai_target >= 0) & (s.persen_silinder_capai_target <= 100)).all()


def test_plotly_ecdf_available(result):
    import plotly.express as px
    fig = px.ecdf(result.benda_uji, x="kuat_tekan_MPa", color="campuran", ecdfnorm="percent")
    assert len(fig.data) == 3


def test_plotly_errorbar_visible_native_bool(result):
    """Regresi bug Streamlit Cloud: plotly menolak numpy.bool sebagai visible."""
    import plotly.graph_objects as go
    lanjut = statistik_lanjutan(result)
    fig = go.Figure()
    for row in lanjut.itertuples(index=False):
        value = float(row.mean_MPa)
        lo, hi = float(row.ci95_rerata_bawah_MPa), float(row.ci95_rerata_atas_MPa)
        has_ci = bool(np.isfinite(lo) and np.isfinite(hi))
        fig.add_trace(go.Scatter(x=[str(row.campuran)], y=[value], mode="markers",
            error_y=dict(type="data", symmetric=False,
                         array=[max(0, hi-value)] if has_ci else [0],
                         arrayminus=[max(0, value-lo)] if has_ci else [0],
                         visible=has_ci)))
    assert len(fig.data) == len(lanjut)
