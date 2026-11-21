# Changelog

Notable changes to this repository, newest first. Each PR adds a Changie
fragment under `.changes/unreleased/`; merging to `main` releases them.

## v0.1.0 - 2026-11-21

### Added

* The image of the host server: the upstream ssh-mcp at tag v2.26.0, built from its commit with the steps of its own Dockerfile and no change of code, and its test against a fake host (bearer token, allowed hosts, the pinned tool list, a read as a normal user, a strict host key)
