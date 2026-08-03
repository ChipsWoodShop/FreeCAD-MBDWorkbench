# Security Policy

## Supported Versions

This project is currently in `0.x` public-preview development. Security fixes will target the latest development branch until a stable release branch exists.

## Reporting a Vulnerability

Please report security issues privately by emailing Chip at Chip@chipswoodshop.com.

Include:

- A short description of the issue.
- Steps to reproduce, if safe to share.
- The FreeCAD version, operating system, and addon version or commit.
- Any affected STEP or FreeCAD files, if they can be shared safely.

Please do not publish exploit details before the issue has been reviewed.

## Scope

The workbench is intended to run locally inside FreeCAD. It should not perform network access or transmit model data. Potential security-sensitive areas include parsing imported STEP/AP242 files and handling user-provided file paths.
