# Query Examples

## Find required children for a schema element

```cypher
MATCH (element {id: 'osc-element:Storyboard'})-[:REQUIRES_CHILD]->(child)
RETURN child.id, child.label;
```

## Follow a bridge rule into VTD semantic families

```cypher
MATCH (rule:BridgeRule)-[:BINDS_TO_VTD]->(family:VTDAssetFamily)
WHERE rule.label = 'osc-vtd-binding:TrafficSignalStateAction:name'
RETURN family.label, family.asset_kind;
```

## Inspect a sample focused neighborhood

```json
{"focus_node": "osc-element:TrafficSignalStateAction"}
```
