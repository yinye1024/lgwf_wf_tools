class EdgeMapping:
    """Compatibility stub for the removed Authoring DSL v1 mapper."""

    def supports(self, statement: object) -> bool:
        return False

    def lower(self, statement: object, context: object) -> None:
        return None
