from openscenario_mcp.knowledge.xsd_inventory import load_xsd_inventory


def test_xsd_inventory_counts_distinct_element_names() -> None:
    inventory = load_xsd_inventory("knowledge/raw/schema/OpenSCENARIO.xsd")

    assert "OpenSCENARIO" in inventory.element_names
    assert "Storyboard" in inventory.element_names
    assert len(inventory.element_names) == 302
    assert len(inventory.simple_type_names) == 48
    assert len(inventory.complex_type_names) == 291
    assert len(inventory.group_names) == 13
