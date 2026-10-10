# Changelog

## [0.1.5](https://github.com/dcc-mcp/dcc-mcp-kdenlive/compare/v0.1.4...v0.1.5) (2026-10-10)


### Documentation

* refresh the generated DCC-MCP host matrix pointer ([#24](https://github.com/dcc-mcp/dcc-mcp-kdenlive/issues/24)) ([5a83cba](https://github.com/dcc-mcp/dcc-mcp-kdenlive/commit/5a83cbad7c987e32b86a5314996951ac91311c3b))

## [0.1.4](https://github.com/dcc-mcp/dcc-mcp-kdenlive/compare/v0.1.3...v0.1.4) (2026-10-09)


### Bug Fixes

* **ci:** anchor release identity on the tag, not github.sha ([18c4831](https://github.com/dcc-mcp/dcc-mcp-kdenlive/commit/18c4831a62c758e1dda14ca9a3999ab91856c4e9))

## [0.1.3](https://github.com/dcc-mcp/dcc-mcp-kdenlive/compare/v0.1.2...v0.1.3) (2026-10-06)


### Bug Fixes

* omit scalar project-bin browser metadata from portable packages ([#20](https://github.com/dcc-mcp/dcc-mcp-kdenlive/issues/20)) ([e712709](https://github.com/dcc-mcp/dcc-mcp-kdenlive/commit/e712709032adcadab591096220347d54feeebaf6))
* preserve project packaging during skill regeneration ([#17](https://github.com/dcc-mcp/dcc-mcp-kdenlive/issues/17)) ([0d1a1cc](https://github.com/dcc-mcp/dcc-mcp-kdenlive/commit/0d1a1cc2bfe0ff203384d174549217a1ca57191a))

## [0.1.2](https://github.com/dcc-mcp/dcc-mcp-kdenlive/compare/v0.1.1...v0.1.2) (2026-10-03)


### Features

* export bounded lossless PNG frames ([#16](https://github.com/dcc-mcp/dcc-mcp-kdenlive/issues/16)) ([159991c](https://github.com/dcc-mcp/dcc-mcp-kdenlive/commit/159991c9c4c2626e4815cbcd527a5917be6221a1))
* package portable native projects with AVI media ([888abad](https://github.com/dcc-mcp/dcc-mcp-kdenlive/commit/888abad0b1758d24604c941f142b800b87191a0b))


### Bug Fixes

* preserve native Kdenlive effect identities ([#15](https://github.com/dcc-mcp/dcc-mcp-kdenlive/issues/15)) ([d8dc977](https://github.com/dcc-mcp/dcc-mcp-kdenlive/commit/d8dc9773dfa89ecac21a449493b6338ca4607d6f))
* resolve portable media from the opened document ([#14](https://github.com/dcc-mcp/dcc-mcp-kdenlive/issues/14)) ([44268aa](https://github.com/dcc-mcp/dcc-mcp-kdenlive/commit/44268aab83f3867b75d39c78cc3df2b3cd096826))


### Documentation

* index the portable-package validation snapshots ([#11](https://github.com/dcc-mcp/dcc-mcp-kdenlive/issues/11)) ([573acde](https://github.com/dcc-mcp/dcc-mcp-kdenlive/commit/573acdef48acb303234cbd093919f44f830b2873))
* qualify portable validation evidence ([#12](https://github.com/dcc-mcp/dcc-mcp-kdenlive/issues/12)) ([437aaca](https://github.com/dcc-mcp/dcc-mcp-kdenlive/commit/437aacad53ba0c0e9910508f9d19ce5ff991471c))

## [0.1.1](https://github.com/dcc-mcp/dcc-mcp-kdenlive/compare/v0.1.0...v0.1.1) (2026-09-14)


### Features

* add experimental native Kdenlive editor bridge ([e58a52b](https://github.com/dcc-mcp/dcc-mcp-kdenlive/commit/e58a52bcab7e9bb45ba8b0050bfe562af279e2d1))


### Bug Fixes

* preserve exact Kdenlive window binding ([#5](https://github.com/dcc-mcp/dcc-mcp-kdenlive/issues/5)) ([da305d9](https://github.com/dcc-mcp/dcc-mcp-kdenlive/commit/da305d94c0e8f0b30a7bcc37a236d1a0dc11f213))
* refresh active sequence after native undo ([540e407](https://github.com/dcc-mcp/dcc-mcp-kdenlive/commit/540e40791970d1f0938b7b30cf932bb556919290))


### Documentation

* add Kdenlive installation and lifecycle runbook ([b73753f](https://github.com/dcc-mcp/dcc-mcp-kdenlive/commit/b73753fda1d492b57e1805930f9c60a4b46d3510))
* explain Skills and MCP with concept art ([#6](https://github.com/dcc-mcp/dcc-mcp-kdenlive/issues/6)) ([9ae4db3](https://github.com/dcc-mcp/dcc-mcp-kdenlive/commit/9ae4db3c59dd3a961a3842e15165a2106201b4da))
* illustrate headphone video editing workflow ([#7](https://github.com/dcc-mcp/dcc-mcp-kdenlive/issues/7)) ([db719e6](https://github.com/dcc-mcp/dcc-mcp-kdenlive/commit/db719e633cc0b344281d5761e05b13659e7d0663))
* showcase a vertical Kdenlive edit ([#4](https://github.com/dcc-mcp/dcc-mcp-kdenlive/issues/4)) ([5ad60bc](https://github.com/dcc-mcp/dcc-mcp-kdenlive/commit/5ad60bca3b702640d46c07610f3b836206777abd))

## 0.1.0 (2026-09-13)


### Features

* expose Kdenlive project and rendering tools through DCC-MCP ([7013328](https://github.com/dcc-mcp/dcc-mcp-kdenlive/commit/7013328c92fad553d9d0f1cc3f8da954c80ac8a6))


### Bug Fixes

* serialize project XML on native Python 3.7 ([e9917a0](https://github.com/dcc-mcp/dcc-mcp-kdenlive/commit/e9917a092eb985fd1bb5b547ac4136227b3decbd))
* support catalog entry point and document native acceptance ([a462a9a](https://github.com/dcc-mcp/dcc-mcp-kdenlive/commit/a462a9abfd0cc6938be845adbfa7247cdade726b))
* support Python 3.7 build isolation ([174e90d](https://github.com/dcc-mcp/dcc-mcp-kdenlive/commit/174e90dc6bc8246dfcf93b37473e6bf6b2bdcb26))
