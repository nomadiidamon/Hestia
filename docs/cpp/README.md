# C++ Implementation

Build, dev, and contributor notes specific to the C++ side of this project.
For cross-language concepts and behavior guarantees, see
[`../concepts.md`](../concepts.md) and [`../semantics.md`](../semantics.md).
For why the repo is laid out this way, see [`../architecture.md`](../architecture.md).

## Layout

```
cpp/
├── premake5.lua     # Build configuration
├── src/              # Library/application source
├── scripts/          # Dev scripts (build helpers, formatting, codegen)
└── tool/             # Standalone CLI tool(s)
```

## Requirements

- A C++ compiler supporting the standard declared in `project.ini`
  (`[compatibility] cpp_standard`).
- [premake5](https://premake.github.io/)

## Building

```bash
cd cpp
premake5 gmake2      # or: vs2022, xcode4, ninja, etc.
make -C build config=release
```

> TODO: fill in the actual generated-project directory name and any
> project-specific premake5 options once `premake5.lua` exists.

## Running the Tool

```bash
# TODO: once tool/ has a real entry point
./build/bin/release/<tool-name>
```

## Running Tests

```bash
# TODO: wire up your test runner (Catch2, GoogleTest, doctest, etc.)
```

## Scripts

See `cpp/scripts/` for developer helper scripts (formatting, codegen, local
CI reproduction, etc.). Document each script here as it's added:

| Script | Purpose |
|---|---|
| _`scripts/example.sh`_ | _TODO: describe_ |

## Versioning / Metadata

This tree should read project name/version/contributors from the shared
[`../../project.ini`](../../project.ini) rather than hardcoding them — see
"Shared Metadata" in `../architecture.md` for the intended mechanism.
