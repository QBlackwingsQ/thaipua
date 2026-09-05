"""Guards for the settings hot path: no per-call model construction, no shared-state leaks."""

from thaipua.core.domain.settings import (
    ROLE_TONE_MARK,
    ConsonantSettings,
    Offset,
    default_placement_settings,
)

CONSONANT_KO_KAI = 0x0E01
CONSONANT_KHO_KHAI = 0x0E02
TONE_MAI_EK = 0x0E48


def test_absent_consonant_shares_one_empty_entry() -> None:
    settings = default_placement_settings()
    first = settings.for_consonant(CONSONANT_KO_KAI)
    second = settings.for_consonant(CONSONANT_KHO_KHAI)
    assert first is second
    assert first == ConsonantSettings()


def test_present_consonant_returns_the_stored_entry() -> None:
    settings = default_placement_settings().with_base_offset(CONSONANT_KO_KAI, ROLE_TONE_MARK, Offset(x=5, y=6))
    assert settings.for_consonant(CONSONANT_KO_KAI) is settings.consonants[CONSONANT_KO_KAI]


def test_edits_never_leak_into_the_shared_default() -> None:
    settings = default_placement_settings()
    edited = settings.with_mark_offset(CONSONANT_KO_KAI, ROLE_TONE_MARK, TONE_MAI_EK, Offset(x=9, y=9))
    assert edited.for_consonant(CONSONANT_KHO_KHAI) == ConsonantSettings()
    assert edited.for_consonant(CONSONANT_KO_KAI).mark_offsets[ROLE_TONE_MARK][TONE_MAI_EK] == Offset(x=9, y=9)
    assert settings.for_consonant(CONSONANT_KO_KAI) == ConsonantSettings()
