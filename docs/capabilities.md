# Capability contract

| Domain | Implemented structured route | Editor route / limitation |
| --- | --- | --- |
| Project | Create, inspect, reference validation, guides | Open/save/undo/settings through UI; disk edits are separate copies |
| Project bin | File/color/title-template import, relink | Folders, tags, proxy settings and clip jobs through UI |
| Timeline | Ungrouped append/gap, split, remove, single-playlist ripple | Insert-overwrite, trim/slip/slide, groups/mixes, nested/multiple sequences, multicam through UI |
| Video effects | Dynamic service/asset discovery, attach/remove, native parameters and keyframes | Plugin availability depends on installation; producer effects apply to every use |
| Audio | Native audio filters/parameters, track effects, WAV rendering | Recording/mixer interaction and device setup through UI |
| Compositions | MLT transitions between tractor tracks and native parameters | Interactive mix edits through UI |
| Titles | Import native `.kdenlivetitle` templates | Design/edit text, fonts, paths and layout through title designer UI |
| Subtitles | New UTF-8 SRT from timed text | Import and project subtitle tracks, styling, speech recognition through UI |
| Export | Explicit frame-range async MP4/WebM/ProRes/WAV, cancel, probe verification | Other native export presets, render queue UI and hardware-specific encoding through UI |
| Assets | Installed effects, transitions, producers, consumers, profiles, templates, LUTs/lumas | Online resource accounts/downloads require their normal host setup |
| AI / tracking | Discover relevant installed assets | Speech models, tracking, rotoscoping and analysis are editor workflows, not native adapter endpoints |
| UI / settings | Core ui-control skill with exact PID/HWND | Requires DCC-CUA readiness; blocked controls are reported explicitly |

This release does not claim every editor operation has a typed native API.
The project schema is based on Kdenlive's documented MLT serialization and the
1.04 document graph. Newer documents are inspected and unknown XML is preserved;
complex timeline changes must use the editor's model. Native 26.08 editor roundtrip
acceptance is tracked separately from XML and render tests.

Sources:

- [Kdenlive project file details](https://docs.kdenlive.org/en/project_and_asset_management/file_management/project_files.html)
- [Kdenlive rendering](https://docs.kdenlive.org/en/exporting/render.html)
- [MLT melt command line](https://www.mltframework.org/docs/melt/)
- [Kdenlive source](https://invent.kde.org/multimedia/kdenlive)
