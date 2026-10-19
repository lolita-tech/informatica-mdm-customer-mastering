# Design limitations

This is a Python reference model, not the Informatica matching engine. It assumes validated trusted loyalty IDs represent individuals. Email conflicts trigger review; email alone never merges records. The model uses whole-record CRM preference and a deterministic source-key tie breaker, not field-level trust or latest-timestamp survivorship. Hashed synthetic IDs are not anonymization and must be replaced by actual MDM master IDs in the native build.

The source fixture is a full snapshot. Merge/unmerge history, steward approval UI, reference data management, address standardization and native MDM APIs remain pending. The local demo cannot prove native match quality or licensing availability.
