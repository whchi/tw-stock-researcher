"""Fail-closed case-directory and output-path resolution shared by fetchers."""

from pathlib import Path


class CaseResolutionError(RuntimeError):
    pass


def _root(path: Path) -> Path:
    return path.resolve()


def resolve_case_dir(stock_id: str, repo_root: Path) -> Path:
    if not stock_id.isdigit():
        raise CaseResolutionError(f"invalid Taiwan stock id: {stock_id!r}")
    root = _root(repo_root)
    matches = sorted(
        path.resolve()
        for path in (root / "companies").glob(f"{stock_id}-*")
        if path.is_dir()
    )
    if len(matches) != 1:
        names = ", ".join(path.name for path in matches) or "none"
        raise CaseResolutionError(
            f"expected exactly one companies/{stock_id}-*/ directory; found {len(matches)}: {names}"
        )
    return matches[0]


def case_output_path(stock_id: str, filename: str, repo_root: Path) -> Path:
    if Path(filename).name != filename:
        raise CaseResolutionError(f"output filename must not contain a path: {filename!r}")
    return resolve_case_dir(stock_id, repo_root) / filename


def validate_explicit_output(output: Path, repo_root: Path) -> Path:
    root = _root(repo_root)
    resolved = output.resolve()
    if resolved != root and root not in resolved.parents:
        raise CaseResolutionError(f"explicit output escapes repository: {resolved}")
    return resolved
