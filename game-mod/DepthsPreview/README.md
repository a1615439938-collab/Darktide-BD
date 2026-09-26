# DepthsPreview — local talent preview mod (Alpha)

This folder is a Darktide Mod Framework mod that is developed together with the
`Darktide-BD` future-tree planner.

## Current alpha scope

- Accepts compact `DTP1` build codes exported by the website.
- Runs only when the local client has local gameplay authority:
  - SoloPlay single-player host; or
  - Realms/player-hosted local server.
- Does **not** modify the official backend character loadout.
- Applies only future nodes that are proven identical to a current live node.
- Changed/new future nodes are counted and reported as **pending custom
  implementation** instead of silently substituting the old behavior.
- Can restore the character's normal profile talents with `/depths_off`.

This is deliberately conservative. A preview is worse than useless if a node
looks selected but actually executes the old mechanic.

## Install (manual, no GitHub Actions required)

Copy the `DepthsPreview` folder into your Darktide mods directory next to your
other DMF mods, then add `DepthsPreview` to `mod_load_order.txt`.

Dependencies:

1. Darktide Mod Loader
2. Darktide Mod Framework
3. SoloPlay and/or Realms Server for local-authority testing

## Commands

- `/depths_import DTP1:...` — import and immediately try to apply the build.
- `/depths_apply` — re-apply the imported build.
- `/depths_status` — show class, selection counts, resolved live-compatible
  talents, and pending custom nodes.
- `/depths_off` — restore the current profile's normal talents.

## Build-code schema

`DTP1:20260929a:<class>:<comma-separated 1-based future-node indexes>`

The index list is intentionally compact so it can be pasted into a Darktide
chat command without spaces.

## Safety / limitations

- Local testing only. This mod intentionally refuses to apply when the local
  client is not the gameplay server.
- Local games do not grant official progression/rewards.
- Remote Realms guests are not yet assigned independent preview builds in this
  alpha. The first supported target is the host/local player.
- The September 29 final patch may differ from preview data; regenerate
  `future_data.lua` after updating `tree-core.js`.

## Regenerate runtime data

From the repository root:

```bash
python tools/generate_depths_preview_data.py
```

The generator marks a node as reusable only when slug, category, description,
and advanced description match the live tree.
