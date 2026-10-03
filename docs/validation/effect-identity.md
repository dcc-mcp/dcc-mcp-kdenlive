# Native identity regression check

Use a task-local output directory and an isolated official Core/server/CLI 0.20.41 runtime. Keep the optional gateway disabled. Discover/load the project, media, timeline, effects, export and interchange tools; validate each call against actual schemas.

Create a 640×360, 24 fps project with one video track, add a 24-frame color clip, then use typed add_effect for a clip Dynamic Text, track brightness 0.8, and two master Dynamic Text captions. Add a clip fade_from_black effect using MLT brightness, in 0/out 11, level 1 and alpha 0=0;11=1. Supply complete explicit text style values so font/environment choices remain controlled. Native IDs must match installed definitions; passing a structural identity through parameters must reject before output.

Package into a new root-empty directory and render all 24 frames through MCP. Open a byte-exact copy in the native editor from a separate working directory. Verify both clip effects, track brightness and both master captions, including frames 0/5/11/12/23. Save Copy to a new file and reopen it without changing parameters. Verify all five effects and caption values again. Close the editor normally, then render the input and native-saved copy through MCP in the same display/font environment. Independently decode all 24 frames as RGB and RGBA and compare complete movie bytes.

Keep the parameter-Undo issue in older Kdenlive 24.12.3 separate from this untouched-save gate. Raw GUI traces and native-saved files can contain local paths; keep them private until audited. The public receipt intentionally contains no raw local paths, endpoint addresses, or process IDs.
