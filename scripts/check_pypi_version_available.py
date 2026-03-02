"""Check that a specific package version exists on PyPI."""

from __future__ import annotations

import argparse
import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


def _fetch_pypi_package_json(package: str) -> dict[str, Any]:
    url = f"https://pypi.org/pypi/{package}/json"
    with urlopen(url, timeout=20) as response:  # noqa: S310 (trusted static URL)
        payload = response.read().decode("utf-8")
    return json.loads(payload)


def _version_exists(package_data: dict[str, Any], version: str) -> bool:
    releases = package_data.get("releases", {})
    if not isinstance(releases, dict):
        return False
    return version in releases


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate that a package version exists on PyPI.")
    parser.add_argument("--package", required=True, help="PyPI package name to query")
    parser.add_argument("--version", required=True, help="Version that must exist on PyPI")
    args = parser.parse_args()

    try:
        package_data = _fetch_pypi_package_json(args.package)
    except HTTPError as exc:
        print(f"failed to query PyPI package {args.package!r}: HTTP {exc.code}")
        return 1
    except URLError as exc:
        print(f"failed to query PyPI package {args.package!r}: {exc.reason}")
        return 1

    if not _version_exists(package_data, args.version):
        print(f"version {args.version!r} not found on PyPI package {args.package!r}")
        return 1

    print(f"confirmed {args.package}=={args.version} exists on PyPI")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
