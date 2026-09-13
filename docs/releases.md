# Release operations

Conventional Commits feed Release Please. The release workflow runs the same
reusable CI gates before creating/updating a release PR. Merging that PR triggers
the checks again at its exact SHA, then Release Please creates the versioned
release. The artifact job checks out that release SHA and checks the package/tag
version before building and uploading anything.

Published files:

- `dcc_mcp_kdenlive-VERSION-py3-none-any.whl`
- `dcc_mcp_kdenlive-VERSION.tar.gz`
- `dcc-mcp-kdenlive-VERSION-skills.zip`
- `install-manifest.json` with immutable release URLs and wheel hash
- `SHA256SUMS` covering all payloads

GitHub artifact attestations bind payloads to the workflow and source SHA.
The wheel works on supported Python runtimes; Kdenlive, MLT and FFmpeg are installed
separately. Linux and Windows are CI targets; macOS is not a verified release target.

Optional PyPI publishing uses OIDC, never a committed token. Configure a PyPI
Trusted Publisher for this repository's `release.yml`, environment `pypi`, then
set repository variable `PUBLISH_PYPI=true`. Until that external setup is complete,
GitHub Releases is the package distribution channel.

For ecosystem catalog onboarding, use the published wheel URL and SHA-256 from
`install-manifest.json` in the core catalog and add the compatibility matrix row.
Catalog availability is distinct from a registered running instance. Installing
the wheel does not start Kdenlive.
