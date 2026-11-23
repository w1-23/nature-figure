"""Inventory the pinned source, optionally materialize the redistributable files."""

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import posixpath
import re
import subprocess

import yaml


ROOT = Path(__file__).resolve().parents[1]
PIN = "c6701dbea29afa7c596d029b957b7edc92130ea5"
TREE = "0d3920cb8902776d3ed3f2b2e262d3691678c828"
SOURCE = "https://github.com/Yuan1z0825/nature-skills"
FIGURE = "skills/nature-figure/"
SHARED = "skills/nature-shared/"
ARCHIVE = "vendor/upstream/"
AUDITS = {"audit_figure_collisions.py", "audit_panel_alignment.py", "audit_pdf_text.py", "validate_figure.py"}
THIRD_PARTY = FIGURE + "assets/figures4papers/"
NOTICE = THIRD_PARTY + "THIRD_PARTY_NOTICES.md"
LINK = re.compile(r"!?\[[^\]\n]*\]\(([^)\s]+)\)|(?:src|href)=[\"']([^\"']+)[\"']")
SHARED_REF = re.compile(r"(?:\.\./)+nature-shared/[a-zA-Z0-9_./-]+\.(?:md|py|yaml)")


def git(repo, *args):
    return subprocess.check_output(["git", "--no-optional-locks", "-C", str(repo), *args])


def destinations(name):
    if name == "LICENSE":
        return ["LICENSE"], "upstream_apache_license"
    if name.startswith(THIRD_PARTY) and name != NOTICE:
        return [], "third_party_rights_unconfirmed"
    if name.startswith(FIGURE + "assets/") and name != NOTICE:
        return [], "image_provenance_not_individually_verified"
    paths = [ARCHIVE + name]
    if name.startswith(FIGURE + "scripts/") and PurePosixPath(name).name in AUDITS:
        paths.append("scripts/audits/" + PurePosixPath(name).name)
    return paths, "upstream_notice" if name == NOTICE else "upstream_project_source"


def manifest_targets(manifest):
    return sorted(set(manifest["always_load"] + list(manifest["axes"]["backend"]["values"].values())
                      + [manifest["preference"]["backend_script"]]
                      + [route[key] for route in manifest["routes"].values()
                         for key in ("reference", "script") if key in route]
                      + [item["path"] for item in manifest["references"]["on_demand"]]))


def verify_archive():
    inventory = ROOT / ARCHIVE / "inventory.json"
    recorded = json.loads(inventory.read_text(encoding="utf-8"))
    if (recorded["repository"], recorded["commit"], recorded["tree"]) != (SOURCE, PIN, TREE):
        raise SystemExit("Archive source identity differs from the fixed upstream pin.")

    records = recorded["files"]
    copies = set()
    for source, record in records.items():
        if record["paths"]:
            relative = PurePosixPath(source)
            if relative.is_absolute() or ".." in relative.parts:
                raise SystemExit(f"Unexpected upstream path: {source}")
        paths, disposition = destinations(source)
        if paths != record["paths"] or disposition != record["disposition"]:
            raise SystemExit(f"Archive disposition differs from policy: {source}")
        for path in paths:
            target = ROOT / path
            if not target.is_file() or target.resolve() != target:
                raise SystemExit(f"Missing or linked archive file: {path}")
            content = target.read_bytes()
            if len(content) != record["bytes"] or hashlib.sha256(content).hexdigest() != record["sha256"]:
                raise SystemExit(f"Archive file differs from its inventory: {path}")
            copies.add(target)

    expected = {path for path in copies if path.is_relative_to(inventory.parent)} | {inventory}
    actual = {path for path in inventory.parent.rglob("*") if path.is_file() or path.is_symlink()}
    if actual != expected:
        raise SystemExit("Archive file set differs from its inventory.")

    manifest = yaml.safe_load((ROOT / ARCHIVE / FIGURE / "manifest.yaml").read_text(encoding="utf-8"))
    targets = [posixpath.normpath(FIGURE + path) for path in manifest_targets(manifest)]
    dependencies = recorded["nature_shared_dependencies"]
    if manifest["version"] != recorded["figure_manifest_version"] or targets != recorded["manifest_paths_verified"]:
        raise SystemExit("Archived manifest differs from its inventory.")
    if any(ROOT / (ARCHIVE + path) not in copies for path in targets + dependencies):
        raise SystemExit("An archived manifest target or shared dependency is missing.")
    print(f"Verified {len(copies)} retained copies, {len(targets)} manifest paths, {len(dependencies)} direct shared references.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkout", type=Path, nargs="?")
    parser.add_argument("--verify-only", action="store_true", help="check retained files against the local inventory")
    parser.add_argument("--materialize", action="store_true")
    args = parser.parse_args()
    if args.verify_only:
        if args.checkout or args.materialize:
            parser.error("--verify-only uses only the local inventory")
        verify_archive()
        return
    if args.checkout is None:
        parser.error("supply a pinned checkout or use --verify-only")
    checkout = args.checkout.resolve()
    if git(checkout, "rev-parse", "HEAD").decode().strip() != PIN:
        raise SystemExit(f"Upstream checkout must be {PIN}.")
    records, raw_text = {}, {}
    for entry in git(checkout, "ls-tree", "-rz", PIN, "--", "LICENSE", FIGURE, SHARED).split(b"\0"):
        if not entry:
            continue
        metadata, path = entry.decode().split("\t", 1)
        mode, kind, blob = metadata.split()
        if kind != "blob" or mode not in {"100644", "100755"}:
            raise SystemExit(f"Unexpected upstream entry type: {path}")
        content = git(checkout, "cat-file", "blob", blob)
        if (checkout / path).read_bytes() != content:
            raise SystemExit(f"Checkout differs from the pinned blob: {path}")
        copies, disposition = destinations(path)
        records[path] = {"paths": copies, "disposition": disposition, "bytes": len(content),
                         "sha256": hashlib.sha256(content).hexdigest()}
        if copies and path.endswith((".md", ".yaml")):
            raw_text[path] = content.decode("utf-8")
        for destination in copies:
            target = ROOT / destination
            if args.materialize:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
            if target.read_bytes() != content or target.is_symlink():
                raise SystemExit(f"Vendor content differs from upstream: {destination}")

    manifest = yaml.safe_load(raw_text[FIGURE + "manifest.yaml"])
    targets = [posixpath.normpath(FIGURE + path) for path in manifest_targets(manifest)]
    if any(not records.get(path, {}).get("paths") for path in targets):
        raise SystemExit("An upstream manifest path is absent from the raw archive.")
    dependencies = set()
    unavailable = set()
    for source, text in raw_text.items():
        links = {first or second for first, second in LINK.findall(text)}
        if source.startswith(FIGURE):
            links.update(SHARED_REF.findall(text))
        for link in links:
            if link.startswith(("#", "/")) or "://" in link or link.startswith("mailto:"):
                continue
            target = posixpath.normpath(posixpath.join(posixpath.dirname(source), link.split("#")[0]))
            if source.startswith(FIGURE) and target.startswith(SHARED) and target in records:
                dependencies.add(target)
            if target in records and not records[target]["paths"]:
                unavailable.add((source, target, records[target]["disposition"]))
            elif target not in records and not any(item.startswith(target + "/") for item in records):
                unavailable.add((source, target, "outside_retained_scope_or_already_unresolved_upstream"))
    if len(dependencies) < 3 or any(not records[path]["paths"] for path in dependencies):
        raise SystemExit("Expected actual nature-shared dependencies are missing.")
    result = {"repository": SOURCE, "commit": PIN,
              "tree": git(checkout, "rev-parse", f"{PIN}^{{tree}}").decode().strip(),
              "figure_manifest_version": manifest["version"], "manifest_paths_verified": targets,
              "nature_shared_dependencies": sorted(dependencies), "raw_link_exceptions": sorted(unavailable),
              "files": records}
    encoded = json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    inventory = ROOT / ARCHIVE / "inventory.json"
    if args.materialize:
        inventory.write_text(encoded, encoding="utf-8")
    if inventory.read_text(encoding="utf-8") != encoded:
        raise SystemExit("Upstream inventory differs from the pinned checkout.")
    verify_archive()
    print(f"Verified {len(records)} upstream files, {len(targets)} manifest paths, {len(dependencies)} direct shared references.")


if __name__ == "__main__":
    main()
