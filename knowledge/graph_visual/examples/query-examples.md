# Query Examples

## Find required children for a schema element

```cypher
MATCH (element {id: 'osc-element:Storyboard'})-[:REQUIRES_CHILD]->(child)
RETURN child.id, child.label;
```

## Follow a bridge rule into aggregated VTD asset kinds

```cypher
MATCH (rule:BridgeRule)-[:BINDS_TO_VTD_KIND]->(kind:VTDAssetKind)
WHERE rule.label = 'osc-vtd-binding:TrafficSignalStateAction:name'
RETURN kind.label, kind.family_count;
```

## Inspect a sample focused neighborhood

```json
{"focus_node": "osc-element:TrafficSignalStateAction"}
```
