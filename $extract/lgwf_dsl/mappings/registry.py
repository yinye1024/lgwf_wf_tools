import lgwf_dsl.mappings.types as mapping_types


def default_mappings() -> list[mapping_types.StatementMapping]:
    """Return legacy statement mappings.

    Authoring DSL v2 lowers aliases directly in ``lgwf_dsl.lowerer``. The
    registry remains as a compatibility import surface for older callers, but
    no v1 mapper should be active.
    """

    return []
