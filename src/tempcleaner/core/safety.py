from pathlib import Path


class SafetyError(ValueError):
    pass


def assert_path_safe(path: Path, allowed_roots: list[Path]) -> Path:
    resolved = path.expanduser().resolve(strict=False)
    if len(resolved.parts) <= 1:
        raise SafetyError(f"Refusing drive/root path: {resolved}")
    # Windows: Path('C:\\').parts may be ('C:\\',) — reject
    if resolved.parent == resolved:
        raise SafetyError(f"Refusing root path: {resolved}")
    roots = [r.expanduser().resolve(strict=False) for r in allowed_roots]
    for root in roots:
        try:
            resolved.relative_to(root)
            return resolved
        except ValueError:
            continue
    raise SafetyError(f"Path not under allowlisted roots: {resolved}")


def is_forbidden_top_level(path: Path) -> bool:
    resolved = path.resolve(strict=False)
    if resolved.parent == resolved:
        return True
    return resolved == Path.home().resolve(strict=False)
