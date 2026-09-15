from three_maps.config.ontology import DEFAULT_ONTOLOGY


def test_canonical_28_axes_and_56_poles():
    assert len(DEFAULT_ONTOLOGY.all_axes()) == 28
    assert len(DEFAULT_ONTOLOGY.all_poles()) == 56


def test_axis_ids_are_complete():
    assert [a.id for a in DEFAULT_ONTOLOGY.all_axes()] == [f"A{i:02d}" for i in range(1, 29)]


def test_each_axis_has_two_distinct_poles():
    for axis in DEFAULT_ONTOLOGY.all_axes():
        assert axis.pole_a_id != axis.pole_b_id
        assert DEFAULT_ONTOLOGY.axis_for_pole(axis.pole_a_id).id == axis.id
        assert DEFAULT_ONTOLOGY.axis_for_pole(axis.pole_b_id).id == axis.id


def test_pole_sides_are_a_or_b():
    for pole in DEFAULT_ONTOLOGY.all_poles():
        assert pole.side in {"A", "B"}


def test_ontology_version_propagates():
    assert all(a.ontology_version == "OV-0.1.0" for a in DEFAULT_ONTOLOGY.all_axes())
    assert all(p.ontology_version == "OV-0.1.0" for p in DEFAULT_ONTOLOGY.all_poles())
