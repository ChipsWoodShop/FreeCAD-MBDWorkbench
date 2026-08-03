#!/usr/bin/env python3
"""Validate the FreeCAD Addon Manager metadata we can check locally."""

from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET


REPO_DIR = Path(__file__).resolve().parents[1]
PACKAGE_XML = REPO_DIR / "package.xml"
NS = {"fc": "https://wiki.freecad.org/Package_Metadata"}


def text(root, tag):
    node = root.find(f"fc:{tag}", NS)
    return "" if node is None or node.text is None else node.text.strip()


def require(condition, message, errors):
    if not condition:
        errors.append(message)


def validate():
    errors = []

    require(PACKAGE_XML.exists(), "package.xml is missing", errors)

    if errors:
        return errors

    try:
        root = ET.parse(PACKAGE_XML).getroot()
    except ET.ParseError as exc:
        return [f"package.xml is not well-formed XML: {exc}"]

    require(
        root.tag == "{https://wiki.freecad.org/Package_Metadata}package",
        "package.xml root must be the FreeCAD package metadata element",
        errors,
    )
    require(root.attrib.get("format") == "1", "package format must be 1", errors)

    required_tags = [
        "name",
        "version",
        "date",
        "description",
        "maintainer",
        "license",
        "icon",
        "content",
    ]

    for tag in required_tags:
        require(root.find(f"fc:{tag}", NS) is not None, f"missing <{tag}>", errors)

    package_name = text(root, "name")
    require(package_name, "package name is empty", errors)
    require(
        not re.search(r'[\\/\\?%\\*:|"<>]', package_name),
        f"package name contains unsafe characters: {package_name!r}",
        errors,
    )
    require(
        re.fullmatch(r"\d+\.\d+\.\d+", text(root, "version")) is not None,
        "version must use MAJOR.MINOR.PATCH semantic version form",
        errors,
    )
    require(
        re.fullmatch(r"\d{4}-\d{2}-\d{2}", text(root, "date")) is not None,
        "date must use YYYY-MM-DD format",
        errors,
    )

    maintainer = root.find("fc:maintainer", NS)
    require(
        maintainer is not None and maintainer.attrib.get("email"),
        "maintainer must include an email attribute",
        errors,
    )

    license_node = root.find("fc:license", NS)
    license_path = license_node.attrib.get("file") if license_node is not None else ""
    if license_path:
        require((REPO_DIR / license_path).is_file(), f"license file missing: {license_path}", errors)

    icon_path = text(root, "icon")
    require(icon_path and "\\" not in icon_path, "icon path must use / separators", errors)
    if icon_path:
        require((REPO_DIR / icon_path).is_file(), f"icon path missing: {icon_path}", errors)

    require((REPO_DIR / "README.md").is_file(), "README.md is missing", errors)
    require((REPO_DIR / "LICENSE").is_file(), "LICENSE is missing", errors)
    require((REPO_DIR / "SECURITY.md").is_file(), "SECURITY.md is missing", errors)

    workbenches = root.findall("fc:content/fc:workbench", NS)
    require(len(workbenches) == 1, "expected exactly one workbench content item", errors)

    for workbench in workbenches:
        classname = workbench.findtext("fc:classname", default="", namespaces=NS).strip()
        subdirectory = workbench.findtext("fc:subdirectory", default="", namespaces=NS).strip()
        workbench_icon = workbench.findtext("fc:icon", default="", namespaces=NS).strip()

        require(classname == "MBDWorkbench", "workbench classname must be MBDWorkbench", errors)
        require(subdirectory and "\\" not in subdirectory, "workbench subdirectory must use / separators", errors)
        if subdirectory:
            require((REPO_DIR / subdirectory).is_dir(), f"workbench subdirectory missing: {subdirectory}", errors)
        if workbench_icon:
            require((REPO_DIR / workbench_icon).is_file(), f"workbench icon missing: {workbench_icon}", errors)

    url_types = {
        node.attrib.get("type")
        for node in root.findall("fc:url", NS)
    }
    require("repository" in url_types, "repository URL is missing", errors)
    require("readme" in url_types, "README URL is missing", errors)
    require("bugtracker" in url_types, "bugtracker URL is missing", errors)

    tags = [node.text.strip() for node in root.findall("fc:tag", NS) if node.text]
    require("freecad" in [tag.lower() for tag in tags] or tags, "addon tags are missing", errors)

    return errors


def main():
    errors = validate()

    if errors:
        for error in errors:
            print(f"metadata error: {error}")
        return 1

    print("package metadata validation passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
