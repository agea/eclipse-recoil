# Eclipse Recoil

Multiplayer FPS prototype based on Red Eclipse. The first milestone is a native
macOS baseline and a separate TDM preset; current settings do not yet reproduce
CS:GO movement or weapons.

- Work only in this repository; preserve the original gameplay.
- The CSGOpen TDM preset enables friendly fire for humans and bots, with a
  team damage multiplier of 1, as requested after the initial milestone.
- The TDM preset has no map pickups, ammunition loot, manual equipment drops,
  death loot, or prize drops (`sv_csgopennoloot 1`). Preserve the release and
  remaining fuse of already armed grenades when their holder dies.
- TDM weapon names follow the optional Urban Terror models. Existing weapon
  statistics remain their CS:GO references; the shotgun uses the SPAS-12 model/name
  with unchanged XM1014 statistics; PSG-1 uses the SCAR-20 row on the
  Flamer slot. Keep SR8, PSG-1 and AK-103 zoom input allowed in TDM. PSG-1 and AK-103
  use fixed zoom; AK zoom must preserve primary accuracy and burst buildup.
  PSG-1 and SR8 hide the unscoped crosshair while retaining the scope reticle.
  Imported weapon icons follow those models in equipment menus and HUD, with
  native fallback for the mine, absent pack and original gameplay.
- TDM Player Setup combines identity and loadout in one page. Hide colour,
  mixer and vanity controls there while preserving the original-profile UI.
- TDM HE, smoke and launcher projectiles stay opaque and have no countdown
  flare/light. Keep bounce/explosion effects and grenade physics unchanged.
- TDM spawn protection lasts 4000 ms; preserve the original shoot/cook/objective
  interruption rules and 3000 ms human/bot respawn delays.
- TDM servers start without bots (`sv_botbalance 0`, `sv_botoffset 0`). Bot
  filling must be explicitly enabled after loading the preset. Offline Match
  can opt into an exact bot count when the player presses Begin; keep the
  local-only override disabled on startup (`sv_csgopenbotcount -1`).
- Always write and update README files and `AGENTS.md` in English. This includes
  `README.md` and `doc/csgopen/README.md`. Open
  README files with Eclipse Recoil's overall purpose before current milestone details.
- Official branding: Eclipse Recoil, tagline "Be kind, reload". Keep supplied
  branding assets in `data/csgopen/branding/`, outside upstream asset submodules.
  The TDM launcher applies `config/csgopen/branding.cfg` before SDL initialization;
  preserve the upstream presentation in the original profile.
- Read `doc/csgopen/README.md`, `doc/csgopen/gameplay.md`, and
  `doc/csgopen/validation.md` before changing the build, launchers, or rules.
  Distinguish executed tests, code inspection, and pending manual checks.
- Use the upstream Makefile and C++ style (four spaces, braces on separate
  lines, existing variable macros and synchronization). Prefer CubeScript.
- Verified macOS commands: `scripts/csgopen/dev.sh check`, `build`, `original`,
  `tdm`, and `server`. Run the explicit smoke test in `config/csgopen/smoke.cfg`
  with the local dedicated server running; check for `SMOKE_DONE FAILURES 0`,
  not just exit code 0.
- Do not hardcode Homebrew prefixes. Do not use `brew upgrade`, Rosetta, or
  XQuartz as default solutions. Preserve Linux and Windows build paths.
- Do not modify assets or maps in submodules. Use recorded commits:
  `git submodule update --init --recursive`, never `--remote`.
- Urban Terror soldier and weapon assets are tracked in
  `data/csgopen/soldiers.zip` and `weapons.zip` and
  required in client release packages, as requested by the project owner.
  Regenerate them with `scripts/csgopen/import-soldiers.py` and
  `scripts/csgopen/import-weapons.py`. Preserve source attribution and manifests;
  these third-party assets are not covered by the Eclipse Recoil source license.
- Keep logs, runtime profiles, and local results in `.csgopen/` (Git-ignored).
- Bind test servers to loopback, without public master registration or cloud
  deployment.
- The small-group server preset uses a random starting map and three random
  choices during play and at intermission (`sv_votechoices 3`). Mid-match
  changes require a strict majority of connected humans, including spectators
  and excluding bots (`sv_votestyle 3`); votes must agree on one destination.
  Keep the upstream free-vote
  behavior available with `sv_votechoices 0`; do not include `de_stmarc` in the
  preset until its conversion has been repaired.
- Do not perform destructive Git resets, commits, pushes, or publication unless
  requested.
