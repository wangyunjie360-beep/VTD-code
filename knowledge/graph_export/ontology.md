# Ontology

## Node Types

- `OSCElement`: Structured OpenSCENARIO element record derived from the local XSD.
- `OSCAttribute`: Attribute slot on an OpenSCENARIO element, including required/reference metadata.
- `VTDAsset`: Concrete VTD runtime asset from the repository snapshot.
- `VTDAssetFamily`: Semantic family that groups VTD assets by canonical name and asset kind.
- `VTDAssetVariant`: Country-scoped or source-scoped semantic variant of a VTD asset family.
- `Country`: Normalized country scope from the VTD taxonomy.
- `NamePolicy`: Name collision / safe-name rule derived from VTD runtime naming constraints.
- `BridgeRule`: OSC-to-VTD field binding rule used during generation and repair guidance.
- `DiagnosticPattern`: Validator diagnostic classification pattern used for repair guidance.
- `ReferenceKind`: Reference target category carried by OpenSCENARIO attributes.

## Edge Types

- `HAS_CHILD`: Element allows a child element.
- `REQUIRES_CHILD`: Element requires the target child element or choice member.
- `HAS_ATTRIBUTE`: Element exposes an attribute node.
- `REFERENCES`: Attribute points at a named reference kind.
- `HAS_VARIANT`: VTD family exposes a semantic variant.
- `VARIANT_OF_ASSET`: Semantic variant resolves to a concrete VTD asset record.
- `APPLIES_TO_COUNTRY`: Node is scoped to a normalized country node.
- `CONSTRAINS_NAME`: Name policy protects or constrains a runtime asset family or asset.
- `BINDS_TO_VTD`: Bridge rule binds an OSC field to VTD semantic families.
- `HAS_REPAIR_PATTERN`: Element is associated with a validator repair pattern.
