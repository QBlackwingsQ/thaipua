"""Thai cluster classification through the single `try_key` entry point."""

import logging

from _pytest.logging import LogCaptureFixture

from thaipua.core.domain.cluster import ThaiCluster, try_key
from thaipua.core.font.map_validation import IssueSeverity, validate_pua_map
from thaipua.core.font.specs import decompose_thai_cluster, iter_composite_specs
from thaipua.core.layout import canonical_layout
from thaipua.gui.state import group_composites_by_consonant, pua_specs_for_consonant


def test_decompose_accepts_any_mark_order() -> None:
    assert decompose_thai_cluster("กํ่") == decompose_thai_cluster("ก่ํ") == (0x0E01, None, 0x0E4D, 0x0E48)
    assert decompose_thai_cluster("ก" + chr(0x0E49) + chr(0x0E38)) == (0x0E01, 0x0E38, None, 0x0E49)
    assert decompose_thai_cluster("ก") == (0x0E01, None, None, None)


def test_decompose_rejects_illegal_clusters() -> None:
    assert decompose_thai_cluster("") is None
    assert decompose_thai_cluster("ก่้") is None
    assert decompose_thai_cluster("กุิ") is None
    assert decompose_thai_cluster("abc") is None
    assert decompose_thai_cluster("่ก") is None
    assert decompose_thai_cluster("กX") is None


def test_decompose_agrees_with_domain_objects() -> None:
    assert try_key("เก") is None
    for key in ("ก", "ก่", "กํ่", "กุ้"):
        cluster = try_key(key)
        assert cluster is not None
        assert ThaiCluster.from_key(key) == cluster
        decomposed = decompose_thai_cluster(key)
        assert decomposed is not None
        assert decomposed[0] == cluster.consonant.value


def test_iter_skips_malformed_entries_with_warning(caplog: LogCaptureFixture) -> None:
    mapping = {"ก่": "\ue000", "กุิ": "\ue001", "ok": "\ue002"}
    with caplog.at_level(logging.WARNING, logger="thaipua.core.font.specs"):
        specs = list(iter_composite_specs(mapping))
    assert [spec.thai_key for spec in specs] == ["ก่"]
    assert "กุิ" in caplog.text


def test_validate_reports_illegal_keys_as_errors() -> None:
    issues = validate_pua_map({"กุิ": "\ue000", "ก่้": "\ue001"}, None)
    assert {(issue.thai_key, issue.severity) for issue in issues} == {
        ("กุิ", IssueSeverity.ERROR),
        ("ก่้", IssueSeverity.ERROR),
    }
    assert validate_pua_map({"ก่": "\ue000"}, None) == []


def test_shipped_map_decomposes_fully() -> None:
    mapping = canonical_layout(0xE000)
    assert len(mapping) == 2016
    assert all(decompose_thai_cluster(key) is not None for key in mapping)


def test_try_key_shares_cached_instances() -> None:
    assert try_key("ก่") is try_key("ก่")
    assert try_key("ก่") == ThaiCluster.from_key("ก่")


def test_pua_specs_for_consonant_matches_grouped() -> None:
    mapping = canonical_layout(0xE000)
    grouped = group_composites_by_consonant(mapping)
    for cons_uni, expected in grouped.items():
        assert pua_specs_for_consonant(mapping, cons_uni) == expected
    assert pua_specs_for_consonant(mapping, 0x0041) == []
    for specs in grouped.values():
        assert [s.pua_code for s in specs] == sorted(s.pua_code for s in specs)
