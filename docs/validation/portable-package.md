# Initial portable native package acceptance

New `package_project` capability, developed against main fd0a6cc. It uses existing Core discovery, jobs and typed tool dispatch. This page records the initial Core 0.20.39 qualification. See [the later Core 0.20.41 evidence](portable-package-current-core.md) and [publication validation](portable-package-publication.md) for subsequent changes and checks.

## Checked

- 14 package safety/portability tests: duplicate content, basename collision, missing/out-of-root media, symlink components, existing/concurrent destination, cancellation, remote references, residual private metadata, byte budgets, source revision
- Full suite: 46 passed, one real-host test skipped. Isolated writable HOME/XDG paths were used; an earlier unrestricted-default test invocation failed because Core attempted job persistence under the read-only default home. Those failures were environment setup, not silently ignored tests
- Real official MCP SDK2.2.0 / Core0.20.39 / Kdenlive adapter0.1.1 development source: discovery, package call and terminal Core job, native file inspection and validation, then real MLT re-render and FFprobe
- A five-image, five-track, 660-frame1280×800 process film retained its editable producers, overlays, fades and timeline. All660 decoded video frames are identical after relative-path packaging and re-render. Source locations do not occur in native XML or public manifest

Native MLT render acceptance is distinct from opening the Kdenlive editor GUI; no GUI acceptance is claimed here. Linux directory publication was actually tested. Windows no-replace rename code is not qualified by this run; unsupported platforms fail closed.

## Boundaries

Only explicit local file/color producers, selected known effects/transitions and audited media extensions are supported. Indirect title resources, external effect dependencies and unknown producer types are rejected. Caller roots must already be authorized. This controlled-workspace workflow is not a sandbox against malicious native parsers or concurrent directory attackers. The tool cannot confer consent merely because a caller supplies a path.

The public manifest omits original dependency filenames. Content-addressed media names eliminate basename collisions and deduplicate identical content. Staging is cleaned on failure/cancellation. Atomic publication never replaces an existing destination. Other editor/user metadata is preserved and needs review before sharing a package.
