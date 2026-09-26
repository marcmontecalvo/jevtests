from adapters.base import DecisionModel


def build_adapter(spec: dict) -> DecisionModel:
    """Model spec (config/models.yaml) -> adapter instance."""
    if spec.get("kind") == "cloud":
        from adapters.jev_cloud import JevCloud
        return JevCloud(spec)
    from adapters.http_systemone import HttpSystemOne
    return HttpSystemOne(spec)
