from __future__ import annotations

from pathlib import Path

import pytest

from openscenario_mcp.knowledge.vtd_parsers import (
    parse_addon_xml_descriptor,
    parse_dat_definitions,
    parse_decal_scatter,
    parse_pbr_objects,
    parse_resource_dirs,
)

FIXTURE_ROOT = Path("tests/fixtures/vtd_runtime")
FIXTURE_RESOURCE_DIRS = FIXTURE_ROOT / "Tools" / "resourceDirs.txt"
FIXTURE_PBR_OBJECTS = FIXTURE_ROOT / "Tools" / "pbr_objects.xml"
FIXTURE_DECAL_SCATTER = (
    FIXTURE_ROOT / "DefaultProject" / "Config" / "decalScatterConfig01.xml"
)
FIXTURE_ADDON_XML = FIXTURE_ROOT / "AddOns" / "OdrGateway" / "odrGateway.xml"
FIXTURE_EXTERNAL_DAT = (
    FIXTURE_ROOT
    / "VisualLib"
    / "Models"
    / "AddOns"
    / "CountryCN"
    / "SetupFiles"
    / "TT_EXTERNALS_ADD_COUNTRYCN.DAT"
)
FIXTURE_SIGNAL_DAT = (
    FIXTURE_ROOT
    / "VisualLib"
    / "Models"
    / "AddOns"
    / "CountryCN"
    / "SetupFiles"
    / "TT_SIGNALS_ADD_COUNTRYCN.DAT"
)


def test_parse_resource_dirs_splits_colon_packed_entries() -> None:
    entries = parse_resource_dirs(FIXTURE_RESOURCE_DIRS)

    assert [entry["resource_dir"] for entry in entries] == [
        "VisualLib/Styles/VTL/Full/TexturePool",
        "VisualLib/Styles/CountryCNAdd/TexturePool",
        "VisualLib/Models/AddOns/CountryCN/Signals",
        "VisualLib/ModelsPBR/AddOns/CountryCN/Signals",
        "AddOns/OdrGateway",
    ]
    assert entries[0]["source_path"] == entries[1]["source_path"] == (
        "tests/fixtures/vtd_runtime/Tools/resourceDirs.txt#L2"
    )
    assert entries[2]["source_path"] == entries[3]["source_path"] == entries[4][
        "source_path"
    ] == ("tests/fixtures/vtd_runtime/Tools/resourceDirs.txt#L4")


def test_parse_signal_dat_extracts_low_level_sigdef_fields() -> None:
    entry = parse_dat_definitions(FIXTURE_SIGNAL_DAT, definition_kind="signal")[0]

    assert entry["definition_kind"] == "signal"
    assert entry["tag"] == "SIGDEF"
    assert entry["filename"] == "CN_Sg101_Gefahrenstelle01.flt"
    assert entry["canonical_name"] == "CN_Sg101_Gefahrenstelle01"
    assert entry["aliases"] == ["Sg101Gefahrstelle01.flt"]
    assert entry["group_path"] == "CN-Signs-S"
    assert entry["source_path"] == (
        "tests/fixtures/vtd_runtime/VisualLib/Models/AddOns/CountryCN/SetupFiles/"
        "TT_SIGNALS_ADD_COUNTRYCN.DAT#L4"
    )


def test_parse_external_dat_extracts_low_level_extdef_fields() -> None:
    entry = parse_dat_definitions(FIXTURE_EXTERNAL_DAT, definition_kind="external")[0]

    assert entry["definition_kind"] == "external"
    assert entry["tag"] == "EXTDEF"
    assert entry["filename"] == "Railing_Post_Plastic_Green_CN_01.flt"
    assert entry["canonical_name"] == "Railing_Post_Plastic_Green_CN_01"
    assert entry["aliases"] == ["Railing_Post_Plastic_Green_CN_01"]
    assert entry["group_path"] == "China/Road-Elements/Posts"
    assert entry["source_path"] == (
        "tests/fixtures/vtd_runtime/VisualLib/Models/AddOns/CountryCN/SetupFiles/"
        "TT_EXTERNALS_ADD_COUNTRYCN.DAT#L4"
    )


def test_parse_dat_definitions_preserves_duplicate_aliases_literal_order(
    tmp_path: Path,
) -> None:
    fixture = tmp_path / "literal_aliases.dat"
    fixture.write_text(
        "#TAG   ModelName\tComment\tFilename\tLight.\tEle.\tKMW-Type\tvires-Type\t"
        "HAV\tHAV-Subnr.\tInitial\tIconpath\tGroup\tNumber\tValue\tLimit\tUnit\t"
        "Width\tAliases\n"
        "SIGDEF Alias1\tCN_TestSignal01\tCN_TestSignal01.flt\t0.30\t0.62\tSTATIC\t"
        "STATIC\t101\t-1\t-1\tVisualLib/Models/AddOns/CountryCN/Icons/"
        "CN_TestSignal01.xpm\tCN-Signs-S\t-1\t-1.00\t0\tnone\t0.85\tAlias1,,Alias2\n",
        encoding="utf-8",
    )

    entry = parse_dat_definitions(fixture, definition_kind="signal")[0]

    assert entry["aliases"] == ["Alias1", "Alias1", "Alias2"]


def test_parse_signal_dat_accepts_mixed_tabs_and_multi_spaces(
    tmp_path: Path,
) -> None:
    fixture = tmp_path / "signal_whitespace_drift.dat"
    fixture.write_text(
        "SIGDEF PoleSign01.flt                                    \tPoleSign01"
        "                                        \tPoleSign01.flt"
        "                                    \t0.20\t0.40\tSTATIC\tSTATIC\t-1\t-1"
        "\t-1\tVisualLib/Models/AddOns/Legacy2012/Icons/PoleSign01.xpm"
        "                                                          \tLegacy"
        "                                            \t-1\t-1\t0  none\n",
        encoding="utf-8",
    )

    entry = parse_dat_definitions(fixture, definition_kind="signal")[0]

    assert entry["tag"] == "SIGDEF"
    assert entry["filename"] == "PoleSign01.flt"
    assert entry["canonical_name"] == "PoleSign01"
    assert entry["aliases"] == ["PoleSign01.flt"]
    assert entry["group_path"] == "Legacy"


def test_parse_external_dat_accepts_mixed_tabs_and_multi_spaces(
    tmp_path: Path,
) -> None:
    fixture = tmp_path / "external_whitespace_drift.dat"
    fixture.write_text(
        "EXTDEF MiscSpeaker01  0.16\t0.32  MiscSpeaker01.flt\t"
        "VisualLib/Models/AddOnsRail/Standard/Icons/MiscSpeaker01.xpm\t"
        "0.00\t0.00  0.03\tRailMisc\t0.17\t    obstacle\n",
        encoding="utf-8",
    )

    entry = parse_dat_definitions(fixture, definition_kind="external")[0]

    assert entry["tag"] == "EXTDEF"
    assert entry["filename"] == "MiscSpeaker01.flt"
    assert entry["canonical_name"] == "MiscSpeaker01"
    assert entry["aliases"] == ["MiscSpeaker01"]
    assert entry["group_path"] == "RailMisc"


def test_parse_dat_definitions_rejects_rows_with_too_few_columns(
    tmp_path: Path,
) -> None:
    fixture = tmp_path / "malformed_signal.dat"
    fixture.write_text(
        "SIGDEF BrokenAlias\tCN_Broken\tCN_Broken.flt\t0.30\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Malformed DAT definition"):
        parse_dat_definitions(fixture, definition_kind="signal")


def test_parse_pbr_objects_reads_real_style_pbr_object_entries() -> None:
    entries = parse_pbr_objects(FIXTURE_PBR_OBJECTS)

    assert entries[0]["hcs"] == "SgTrafficLight01DirLeft-Top"
    assert entries[0]["pbr"] == "SgUS_Rd_TrafficLight_Left_01_PBR"
    assert entries[0]["cc"] == "USA"
    assert entries[1]["hcs"] == ""
    assert entries[1]["pbr"] == "Bld_Ind_Storage_Reg05_08a_PBR"
    assert entries[1]["cc"] == ""
    assert entries[0]["root_element"] == "PBRObjects"
    assert entries[0]["config_kind"] == "pbr_objects"
    assert entries[0]["source_path"] == "tests/fixtures/vtd_runtime/Tools/pbr_objects.xml"


def test_parse_decal_scatter_extracts_nested_real_style_decal_entries() -> None:
    entries = parse_decal_scatter(FIXTURE_DECAL_SCATTER)

    assert [entry["name"] for entry in entries] == [
        "RdMiscRoadDamagePatch01",
        "RdMiscRoadDamageCrack01",
    ]
    assert entries[0]["quantity"] == "2"
    assert entries[0]["alignment"] == "parallelorthogonal"
    assert entries[0]["targettexture"] == "standard"
    assert entries[0]["root_element"] == "decalscatter"
    assert entries[0]["config_kind"] == "decal_scatter"
    assert entries[0]["source_path"] == (
        "tests/fixtures/vtd_runtime/DefaultProject/Config/decalScatterConfig01.xml"
    )


def test_parse_addon_xml_descriptor_extracts_multi_root_top_level_metadata() -> None:
    descriptor = parse_addon_xml_descriptor(FIXTURE_ADDON_XML)

    assert descriptor["top_level_elements"] == ["RDB", "Config", "Debug"]
    assert descriptor["top_level_descriptors"] == [
        {"element": "RDB", "attributes": {}},
        {
            "element": "Config",
            "attributes": {
                "inhibitCurvatureApproximation": "false",
                "verbose": "false",
            },
        },
        {
            "element": "Debug",
            "attributes": {
                "driver": "false",
                "enable": "true",
                "lightSource": "false",
            },
        },
    ]
    assert descriptor["config_kind"] == "addon_xml_descriptor"
    assert descriptor["source_path"] == (
        "tests/fixtures/vtd_runtime/AddOns/OdrGateway/odrGateway.xml"
    )
