# OpenSCENARIO Visual Knowledge Graph Export

This bundle exports a visualization-friendly OpenSCENARIO + VTD graph view.
Name-policy nodes, concrete VTD assets, variants, and dense name-constraint
edges are removed; VTD family bindings are aggregated by asset kind.

- Project root: `D:/wyj/OPenscenario`
- Nodes: `810`
- Edges: `1989`
- Focus node: `osc-element:TrafficSignalStateAction`

Regenerate with:

```bash
py -3.14 scripts/export_visual_knowledge_graph.py
```
