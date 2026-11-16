from dataclasses import dataclass
from .features import FEATURES, DEFAULT_SERVER_FEATURES, SERVER_PLATFORMS, CLIENT_PLATFORMS

@dataclass(frozen=True)
class Plan:
    role: str
    platform: str
    features: tuple[str, ...]
    actions: tuple[str, ...]

class ConfigurationError(ValueError):
    pass

def _expand_dependencies(selected: set[str]) -> set[str]:
    expanded = set(selected)
    pending = list(selected)
    while pending:
        key = pending.pop()
        if key not in FEATURES:
            raise ConfigurationError(f"Unknown feature: {key}")
        for dependency in FEATURES[key].dependencies:
            if dependency not in expanded:
                expanded.add(dependency)
                pending.append(dependency)
    return expanded

def build_plan(config: dict) -> Plan:
    role = config.get("role", "server")
    platform = str(config.get("platform", "")).lower()
    if role not in ("server", "client"):
        raise ConfigurationError("role must be 'server' or 'client'")
    allowed = SERVER_PLATFORMS if role == "server" else CLIENT_PLATFORMS
    if platform not in allowed:
        raise ConfigurationError(
            f"Unsupported {role} platform '{platform}'. Supported: {', '.join(allowed)}"
        )
    selected = config.get("features")
    if selected is None:
        selected = list(DEFAULT_SERVER_FEATURES) if role == "server" else []
    if not isinstance(selected, list) or not all(isinstance(x, str) for x in selected):
        raise ConfigurationError("features must be a list of feature keys")
    expanded = _expand_dependencies(set(selected))
    for key in sorted(expanded):
        if role not in FEATURES[key].roles:
            raise ConfigurationError(f"Feature '{key}' is not available for role '{role}'")
    ordered = tuple(sorted(expanded))
    actions = (
        f"Detect and validate {platform} {role} host",
        "Check DNS, hostname, time synchronisation and network prerequisites",
        "Resolve package and service dependencies",
        "Generate reviewed installation plan (no changes applied)",
        "Require explicit operator approval before execution",
    )
    return Plan(role, platform, ordered, actions)
