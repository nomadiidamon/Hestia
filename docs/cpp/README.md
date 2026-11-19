@page cpp_implementation C++ Implementation

# C++ Implementation

Hestia provides system discovery, hardware analysis, reusable software
dependency checks, and AI model recommendations. This C++ tree is a placeholder
and does not implement these capabilities yet.

Build, dev, and contributor notes specific to the C++ side of this project.
For project concepts and intended behavior guarantees, see
[Concepts](https://nomadiidamon.github.io/Hestia/Concepts.html) and [Semantics](https://nomadiidamon.github.io/Hestia/Semantics.html).
For why the repo is laid out this way, see [Architecture](https://nomadiidamon.github.io/Hestia/Architecture.html).

## Layout

```
cpp/
+-- premake5.lua     # Build configuration
+-- src/              # Library/application source
+-- scripts/          # Dev scripts (build helpers, formatting, codegen)
`-- tool/             # Standalone CLI tool(s)
```

## Requirements

- A C++ compiler supporting the standard declared in `project.ini`
  (`[compatibility] cpp_standard`).
- [premake5](https://premake.github.io/)

## Building

### Linux and macOS: Make

```bash
cd cpp
premake5 gmake2
make -C build config=release
```

> TODO: fill in the actual generated-project directory name and any
> project-specific premake5 options once `premake5.lua` exists.

### Windows

Use a platform-appropriate premake5 action, such as `vs2022`, instead of
`gmake2`. Build instructions for the generated project remain to be documented.

## Running the Tool

### Linux and macOS

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
`project.ini` rather than hardcoding them - see
"Shared Metadata" in `../Architecture.md` for the intended mechanism.
