from three_maps.config.ontology_catalog import (
    EMPTY_AUTHORITATIVE_CATALOG,
    MappingPermission,
    OntologyCatalog,
    OntologyCatalogError,
    SubThemeAxisMapping,
    SubThemeDefinition,
    ThemeDefinition,
)


def make_catalog():
    themes = tuple(ThemeDefinition(f"T{i:02d}", f"Theme {i}", "OV-0.2.0") for i in range(1, 21))
    subs = tuple(
        SubThemeDefinition(f"ST{i:03d}", f"T{((i-1)//10)+1:02d}", f"Sub {i}", "Authoritative definition", "OV-0.2.0")
        for i in range(1, 201)
    )
    mappings = tuple(
        SubThemeAxisMapping(s.id, "A01", MappingPermission.CORE, .80, "OV-0.2.0")
        for s in subs
    )
    return OntologyCatalog("OV-0.2.0", themes, subs, mappings)


def test_empty_catalog_is_explicitly_incomplete():
    assert not EMPTY_AUTHORITATIVE_CATALOG.is_complete


def test_authoritative_shape_is_publishable():
    assert make_catalog().is_complete
    make_catalog().require_publishable()


def test_orphan_subtheme_rejected():
    themes = (ThemeDefinition("T01", "Theme", "OV-0.2.0"),)
    subs = (SubThemeDefinition("ST001", "T99", "Sub", "Definition", "OV-0.2.0"),)
    try:
        OntologyCatalog("OV-0.2.0", themes, subs)
        assert False
    except OntologyCatalogError:
        pass


def test_duplicate_mapping_rejected():
    c = make_catalog()
    s = c.sub_themes[0]
    duplicate = SubThemeAxisMapping(s.id, "A01", MappingPermission.CORE, .80, "OV-0.2.0")
    try:
        OntologyCatalog(c.ontology_version, c.themes, c.sub_themes, (*c.mappings, duplicate))
        assert False
    except OntologyCatalogError:
        pass


def test_mapping_confidence_range_enforced():
    try:
        OntologyCatalog("OV-0.2.0", (), (), (SubThemeAxisMapping("ST001", "A01", MappingPermission.CORE, 1.1, "OV-0.2.0"),))
        assert False
    except OntologyCatalogError:
        pass
