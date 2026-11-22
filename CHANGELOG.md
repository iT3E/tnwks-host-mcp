# Changelog

Notable changes to this repository, newest first. Each PR adds a Changie
fragment under `.changes/unreleased/`; merging to `main` releases them.

## v0.2.0 - 2026-11-22

### Changed

* The image builds the upstream ssh-mcp at tag v2.27.1. Upstream changed the command classifier only: commands inside the shell grammar, behind interpreter options and in split filters get the class of what they run, which closes two published advisories. The tool list, the tool schemas, the config, the audit log and the SSH handling did not change

## v0.1.0 - 2026-11-21

### Added

* The image of the host server: the upstream ssh-mcp at tag v2.26.0, built from its commit with the steps of its own Dockerfile and no change of code, and its test against a fake host (bearer token, allowed hosts, the pinned tool list, a read as a normal user, a strict host key)
