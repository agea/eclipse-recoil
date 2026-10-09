# Eclipse Recoil

*Be kind, reload*

Eclipse Recoil is a multiplayer first-person shooter built from a fork of Red Eclipse.
The project's goal is a two-team Deathmatch experience inspired by
Counter-Strike: Global Offensive, with deliberate ground movement and weapons
that gradually move toward that style of play. Development proceeds in small,
testable steps while keeping the original Red Eclipse gameplay available as a
reference.

The longer-term scope includes community map conversion and a dedicated Linux
server. The first milestone focuses on a native macOS development baseline and
a separate TDM prototype using existing maps and assets. Its movement and
weapon values are starting points, not a faithful reproduction of CS:GO.

## Current milestone: native macOS baseline and TDM v0.1

Starting commit: `faf378d12558addc700d0e464e7e8c3a39fbceee`. Both the client
and dedicated server have been built and launched natively on the Mac, and the
local network smoke test passes. Visual inspection and keyboard/mouse gameplay
testing remain open. See the [results and checklist](validation.md) and the
[gameplay rules and units](gameplay.md).

## Setup

For client downloads and the automatic `master` release workflow, see the
[release guide](releases.md). It covers macOS Apple Silicon and Intel, Linux
x86_64 and ARM64, and Windows x86_64; release packages exclude the dedicated
server. Starting with the next release, a single Bash installer selects the
correct macOS/Linux client and downloads, verifies, joins and extracts its
files. Windows has a PowerShell installer. See
[quick installation](releases.md#quick-install) or copy the commands from a
specific release page; no compiler is needed to play.

You need an active Xcode/Command Line Tools installation, Homebrew matching
the architecture reported by `uname -m`, and a checkout with its recorded
submodule revisions:

```sh
git clone --recurse-submodules https://github.com/agea/eclipse-recoil.git eclipse-recoil
cd eclipse-recoil
git submodule update --init --recursive
brew install pkgconf sdl2 sdl2_image openal-soft libsndfile
scripts/csgopen/dev.sh check
scripts/csgopen/dev.sh build
```

For an already prepared checkout, run `check` and `build`. Do not use
`--remote` for the asset submodules. Dependencies are SDL2, SDL2_image,
OpenAL Soft, libsndfile, the SDK's zlib, and OpenGL.framework. ENet is built
from the included source. XQuartz and Rosetta are not required. `check`
discovers prefixes through Homebrew and pkg-config and verifies library
architectures with `lipo`.

If the toolchain is missing, install Xcode or run `xcode-select --install`;
select the appropriate installation without arbitrarily changing the system's
selection. The build has been tested on arm64; Intel has not been tested.

The script uses the upstream Makefile with four parallel jobs by default
(`CSGOPEN_JOBS=8 scripts/csgopen/dev.sh build` changes this). It runs exactly
`src/eclipse-recoil_native` and `src/eclipse-recoil_server_native`, with no fallback
to another installation. Repository paths and arguments are quoted; you can
invoke the script by its absolute path from another directory. Binaries are
not installed globally. The upstream launcher now recognizes Darwin and looks
for the `_native` suffix in `bin/<arch>/`, where the Makefile's install targets
place the binaries. Use the development script for this milestone.

## Local gameplay

The TDM preset automatically steps over obstacles up to 7 world units without
reducing horizontal speed. Walking into a higher ledge, up to 13 units, starts
a 450 ms climb. The pistol stays available; other weapons are hidden during
the climb and then take their normal draw time. Ground jumps use
`impulsejump=1.1` instead of 1.5. Clearance and a supported landing are required.
These settings apply across maps and are synchronized by the server; the
original profile keeps automatic traversal disabled. The network protocol is
now 285, so update clients and servers together. See [movement rules](gameplay.md#movimento)
and [native checks](validation.md#automatic-obstacle-traversal-and-lower-jumps-2026-10-05).

The TDM proximity mine recognizes valid contact normals on imported triangle
surfaces even when the engine also reports an internal overlap. It sticks to
these surfaces rather than detonating at first contact. The 1.5-second arming
delay and enemy-only proximity trigger are unchanged. This client-side fix
requires a rebuilt client; converted map packages do not need regeneration.

Grounded TDM players follow connected walkable slope facets with a short
tangent movement and a support check before the ordinary ramp solver. This
avoids treating a slope transition as a new ledge. Walls, low ceilings and
unsupported moves still block traversal. The change leaves terrain meshes,
displacement LOD and triangle counts unchanged; map ZIPs need no regeneration.

The Source converter also smooths solid props whose cavities cannot contain a
player passage: props below 10 map units in height, or narrower than 8 units in
both horizontal dimensions. It evaluates each instance's scale and rotation and preserves
door/window frames and architectural passage props. The convex collision is
used only when it reduces triangle count; rendered geometry stays separate.
Grounded TDM movement additionally checks this frame's supported destination
across seams within the map stair height, without requiring the farther climb
probe to find a tread. It also tries the slope tangent when entering a walkable
bevel from a flat tread. The swept body path and the normal walkable-slope limit still apply.

The TDM preset enables fall damage for humans and bots. Downward impact speeds
up to 100 world units/second are safe; each excess unit costs one health point.
Normal ground jumps remain safe. Water at half submersion cushions the landing,
and automatic climbing does not cause fall damage. The original profile leaves
it disabled. Rebuild and restart clients and servers together for protocol 285;
map packages do not need regeneration. See [fall damage](gameplay.md#fall-damage).

### Quake 3 / Urban Terror map converter

`scripts/csgopen/q3bsp.py` reads compiled Quake 3 `IBSP` version 46 data
directly from a `.bsp` or `.pk3`. It does not require an optional `.map` or
`.bak` brush source. With no output directory it prints a JSON summary:

```sh
python3 scripts/csgopen/q3bsp.py /path/to/ut4_example.pk3
```

With an output directory it writes an OBJ render mesh and a JSON conversion
manifest. The manifest contains the source bounds, solid collision-brush
planes and translated spawn intent (`red` to Alpha, `blue` to Omega, generic
starts to neutral). Polygon and mesh faces are exported, and quadratic patch
faces are tessellated.

```sh
python3 scripts/csgopen/q3bsp.py /path/to/ut4_example.pk3 .csgopen/map-convert/example
```

The end-to-end wrapper creates a temporary staged content package, extracts
directly referenced textures, and builds separate render and collision models.
The collision model duplicates each compiled surface with both windings, so it
does not depend on source brushes or on the source renderer's front-face
convention. The converter ray-tests each spawn against walkable BSP surfaces,
snaps it above the closest supporting floor with player clearance, records any
unsupported starts in the manifest, creates native Alpha/Omega/neutral player
starts, and uses the client editor to save an `.mpz`:

```sh
scripts/csgopen/convert-pk3.sh /path/to/ut4_example.pk3
```

The wrapper prints the package directory and an exact client command for
playing the converted map. A second BSP-name argument selects a map when an
archive name does not match its BSP name or the PK3 contains multiple maps.
Derived files stay under `.csgopen/map-convert/` and are not added to the
repository. This first backend keeps the map as a collidable model; conversion
to editable Cube 2 octree geometry remains future work. Permission to make and
distribute a converted map must still be checked per archive.

### Source 1 BSP map converter

`scripts/csgopen/sourcebsp.py` reads compiled Valve `VBSP` version 20/21 maps
directly, without a decompiled VMF. It reconstructs model 0 faces and terrain
displacements, translates Counter-Terrorist/Terrorist starts to Alpha/Omega,
and reads VMT/VTF assets first from the BSP pakfile and then from an optional
game VPK. DXT1, DXT3 and DXT5 textures are converted losslessly to DDS. Maps
with a `sky_camera` use a generous start-based envelope to exclude the remote
3D skybox model.

The end-to-end wrapper locates `pak01_dir.vpk` next to a normal Steam game
installation, generates a staged package, and uses the client editor to save a
native MPZ:

```sh
scripts/csgopen/convert-source-bsp.sh /path/to/game/maps/de_example.bsp
```

An explicit VPK, model scale, displacement LOD, and static-prop triangle
budget can be supplied as the second through fifth arguments. Defaults are
scale `0.25`, LOD `2`, and 300,000 prop triangles:

```sh
scripts/csgopen/convert-source-bsp.sh /path/to/de_example.bsp /path/to/pak01_dir.vpk 0.25 2 300000
```

The default LOD reduces every displacement axis by four. Render geometry is
partitioned into models below Eclipse Recoil's 65,535-index limit, including
the duplicated triangles required for isolated BIH meshes. Large maps such
as Canals retain their world geometry and share textures across model parts.
Collision is reconstructed from the BSP's authored solid and player-clip brushes, plus
compiled displacement terrain. Brush faces wholly enclosed by another solid or
player-clip brush are removed, including shared interior faces. This never splits
faces or adds triangles. Small non-solid player-clip ramps (at most 256 Source
units per axis, with an authored walkable incline) export their walking surfaces
without vertical foundation sides. Solid brushes and vertical player-clip barriers
keep their exterior walls. The curved Dust2 B stair prop has a separate reviewed
continuous collision surface; its 87 triangles replace 159 without changing render
geometry or other stair models.

The two opened leaves of Dust2's Long A door model use separate convex collision
surfaces derived from the full source mesh. The opening, frame and instance
transforms are retained; both leaves are never enclosed in one hull. The candidate
is used only within the existing collision triangle budget. Other door models
keep their existing geometry.

The reviewed `step_64x32` and `topstep_16x8` Vertigo modules used by Agency's
exterior access have continuous collision prisms: an incline for each flight
and a flat upper connector. The exported decorative edges remain visible, but
cannot catch the player's feet. The model-specific rule checks nominal bounds
and the triangle budget and keeps every instance transform. It is applied before
general prop smoothing, which must not replace the reviewed surface.

Low, regular rectangular stair props reuse the BSP walking surface when it
covers every sampled tread point within -1 to +8 Source units of the visual
surface. Coverage is checked after each instance transform; uncovered stairs
retain their prop collision. Curved, tapered and architectural stair models are
excluded. This removes redundant collision without generating triangles. On
Dust2 it removes the duplicated collider at the B tunnel entrance while retaining
the other three instances of the same stair model.

World collision is exported as double-sided OBJ carriers
partitioned into 1,024-Source-unit XY tiles, so the engine indexes local BIH
volumes for floors, stairs, walls and raised surfaces without altering the
visible material meshes. Only the brush face matching a displacement's footprint
is replaced; unrelated floors and walls sharing its plane keep their collision.
Version-21 brush sides decode `bevel` and `thin` as separate byte flags; thin
sides retain their collision, including stair treads and landings. Imported maps
also set `stairheight` to `20 * scale` (5 at scale 0.25): Source's 18-unit step
height plus two Source units of clearance for mesh edges. This map setting
lets players climb the tested bridge stairs without jumping.
Starts are
placed above their closest compiled walkable surface with native player
clearance, while Source yaw is preserved in Eclipse coordinates. Generated
maps disable the default `newmap` lower-half floor and rely only on imported
collision. Neutral collision backing is disabled by default: Source
`playerclip` volumes can span facades and sky boundaries, so rendering them as
gray geometry causes much more damage than the small holes it attempts to
hide. The low-level converter retains `--neutral-backing` as an experimental
diagnostic option, but reusable conversions should repair missing render
panels at the prop/mesh level instead.

Static props are decoded from the version-10/11 game lump and MDL/VVD/VTX assets
with Blender plus the Plumber addon. Playable instances are merged into local
tile models, reduced toward the requested global triangle budget, and textured
from the BSP pakfile and game VPK. BSP-local VMT definitions are also staged
for the decoder, preserving material paths on custom map props such as Agency's
furniture and architectural panels. The reducer identifies solid and
architectural props and reserves geometry for disconnected panels larger than
16x32 Source units. This prevents a low global decimation ratio from deleting
whole wall, door, arch, or window panels while still simplifying bolts, bars,
foliage, and other small detail aggressively. Set `BLENDER_BIN` and
`PLUMBER_DIR` when they are not installed at
`/Applications/Blender.app/Contents/MacOS/Blender` and
`.csgopen/tools/plumber111/plumber`; set `CSGOPEN_SOURCE_PROPS=0` only for a
world-shell conversion. Because protected panels can raise the final count,
the triangle budget is a target rather than a strict ceiling.

This is still not a complete Source runtime. Dynamic props, lightmaps,
cubemaps, Source shader effects, navigation data and non-spawn gameplay
entities are not converted. Static props marked solid by Source receive
invisible triangle-collision carriers built from their reduced render geometry.
Logs, fallen trees and construction/timber piles instead use a closed convex
hull built from the undecimated model, independently of the visible mesh. Bundled
construction boards (including `construction_wood_2x4_` props) use a 12-triangle
box in model space to remove small bevels and slots while preserving rotation
and outer bounds. This
fills small gaps and concave pockets that can trap a walking player. Selection
uses explicit model-name prefixes; stairs, fences, standing trees, furniture
and architectural props retain their existing collision to preserve openings.
The hull follows the same instance rotation and scale as the visible prop;
it can bridge visible recesses in a pile. Existing map ZIPs must be regenerated
to apply the change. Prop manifests record the affected models and instances.
The curved `de_inferno/bench_wood` model uses separate flat boxes for the seat,
back and each lower support. Seat and back meet without a slot; the space
between the lower supports remains open. This removes small collision edges
when stepping down from a wall onto the bench. Render geometry stays unchanged,
and the replacement is used only when it fits the existing collision triangle
budget. Prop manifests record `sectioned_collision_props` and their models.
These carriers also participate in bot line-of-sight ray tests. The converter
does not yet import the original PHY hulls, so collision is approximate, while
decorative non-solid props remain passable. Consequently a map can retain its
layout, props and base textures while still showing different lighting or
different fine collision around simplified props.

World brushes carrying Source `CONTENTS_WATER` are converted to real Eclipse
Recoil octree water volumes on an 8-unit grid. The importer applies the native
Red Eclipse water material only to empty cubes and omits Source `SURF_WARP`
faces from the render model, avoiding an incompatible flat Source-water mesh.
Volumes outside the playable envelope, such as 3D-skybox copies, are ignored.
Irregular or sloped Source water brushes are necessarily approximated by
grid-aligned bounds because Cube 2 materials occupy octree volumes.

The wrapper stages a conversion under `.csgopen/map-convert/`. To retain a
locally converted map independently of disposable profiles and converter
caches, package its `maps/*` files and `csgopen/imported/<map>/*` tree as
`data/csgopen/<map>.zip`. The TDM client adds `data/csgopen` as a package root,
and the dedicated server validates and mounts the selected map's ZIP before
reading its MPZ. The original profile excludes this package root. These local
ZIP packages are ignored by Git. Valve assets are read from the user's local
game and must not be committed or redistributed without the appropriate
permission.

With a locally installed `data/csgopen/cs_agency.zip`, launch Agency in TDM:

```sh
scripts/csgopen/dev.sh tdm cs_agency
```

With a locally installed `data/csgopen/de_canals.zip`, launch Canals in TDM:

```sh
scripts/csgopen/dev.sh tdm de_canals
```

### Valve VMF map converter

`scripts/csgopen/vmf.py` reconstructs convex brush geometry from a decompiled
Valve Map Format (`.vmf`) file. It includes world brushes and supported static
brush entities, creates separate render and collision OBJ models, translates
Counter-Terrorist/Terrorist starts to Alpha/Omega starts, and snaps every start
above a supporting brush. OBJ meshes are divided into BIH-safe groups without
single-triangle groups, which the current engine cannot index safely.

The end-to-end wrapper builds an isolated native MPZ and prints the exact play
command:

```sh
scripts/csgopen/convert-vmf.sh /path/to/de_example_d.vmf
```

This initial backend exports neutral geometry only. It does not recover Source
materials, textures, props, displacements, lighting or gameplay entities that
are absent from the VMF input. Generated packages remain under
`.csgopen/map-convert/`; check the source map's redistribution terms before
publishing a conversion.

The TDM launcher loads `config/csgopen/branding.cfg` before creating the window.
It uses `data/csgopen/branding/splash.png` (3344 × 1882) as the loading background
and `data/csgopen/branding/icon.png` (1254 × 1254, RGBA) as the SDL application
icon. Both are the supplied PNGs, copied without resizing or conversion.
The splash fits the viewport without cropping or distortion, with black
margins when the screen aspect differs. It replaces map thumbnails and animated
background effects during loading; the upstream logo and central information
panel are hidden so the artwork stays readable. Loading status and the progress
bar remain available. The original profile keeps its upstream presentation.

For a direct client launch, add `-bconfig/csgopen/branding.cfg`; `-b` executes
the configuration before SDL/window initialization. `splashtex` and
`windowicontex` are saved in the profile's `init.cfg`.

The supplied `data/csgopen/branding/logo.png` (2048 × 768, RGBA) replaces
`logotex` and `logocroptex`. Main-menu and welcome-screen headers scale it to
their available width while preserving its aspect ratio. The source PNG stays
unchanged. Client preferences reapply branding after loading saved settings,
so older profile overrides cannot restore the upstream logo in TDM.

```sh
scripts/csgopen/dev.sh original
scripts/csgopen/dev.sh tdm
```

The second command starts TDM on **Echo**, with no automatic bots. To explicitly
enable filling to two participants, use `/botbalance 2` on an authorized client
or set `sv_botbalance 2` after loading the server preset. Close
the client before switching profiles. Choose a player name when prompted,
then leave spectator mode through the menu or `/spectate 0` in the console.
`/tdm echo` is an alias present in this version. To use another included map:

```sh
scripts/csgopen/dev.sh tdm dutility
```

Echo is a native map with Alpha/Omega spawn points and a courtyard derived
from Cube 2. `bath` is absent from this checkout's submodules. The checklist
still needs to confirm which areas and routes are usable without parkour.
No map or asset files have been modified.

The preset sets actual spawn health to 100, disables regeneration, enables
friendly fire for humans and bots with a team damage multiplier of 1, and
starts with a three-second respawn delay. Normal jumping and
crouching remain enabled; parkour capabilities are disabled. A semiautomatic
pistol and one selected primary are assigned at spawn. Choose an optional SMG or up to four grenades in the equipment menu. The expanded loadout also offers AK-47, AWP, MP9, XM1014 and M249 profiles
on existing Red Eclipse weapon slots. Other weapons remain disabled. Primary
fire is available; secondary input is reserved for AWP zoom/scoped fire. Upstream respawn requires primary fire or jump input after
death; the delay does not imply automatic respawn without input.

Pistol and SMG primary fire now have nonzero projectile spread. Relative to
standing still, running triples spread and crouching halves it. Moving while
crouched returns to the standing spread; airborne fire adds a further penalty.
These are initial tuning values. Compare single shots or short bursts at the
same wall and distance, standing, moving, and crouched. Existing recoil remains.

Sustained primary fire also builds additional spread after each shot. The first
shot starts at normal accuracy; buildup is capped at an extra multiplier of
1.5 (up to 2.5x posture spread). Recovery is linear and takes 1.2 seconds from
the cap. Crouching still improves accuracy during a burst. Buildup is tracked
per weapon and cleared on spawn/reset; switching weapons does not clear the
previous weapon's buildup. Compare short bursts, a full magazine, and shots
after a pause. Server settings are `sv_spreadburstadd`, `sv_spreadburstmax`,
and `sv_spreadburstrecovery`. The pistol uses `sv_pistolspreadburstscale 2`
(0.7 buildup per shot) so repeated semiautomatic shots visibly lose accuracy
despite recovery between shots. The SMG retains 0.35 buildup per shot.

The ammunition ring around the crosshair expands with current primary-fire
spread and contracts during recovery or crouching. Bullet glyphs still show
remaining ammunition. Its radius uses the same posture and burst calculation
as firing, with a bounded square-root scale (standing SMG is the reference).
It is an indicative accuracy display, not a projected impact boundary. The
client preference `clipspread` enables it in Eclipse Recoil and defaults to off in
the original profile.

### Weapon reference: Desert Eagle and PP-Bizon

The pistol and SMG now use the [supplied weapon statistics sheet](https://docs.google.com/spreadsheets/d/11tDzUNBq9zIX6_9Rel__fdAUezAQzSnh5AVYzCP060c/edit?gid=0)
for torso damage, headshot multiplier, fire interval and magazine/reserve size.
The selected source rows are saved in `config/csgopen/weapon-reference.json`.

| Parameter | Pistol (Desert Eagle) | SMG (PP-Bizon) |
| --- | --- | --- |
| Torso damage, without armor | 53 | 27 |
| Headshot multiplier | 3.9 | 4 |
| Fire interval | 225 ms | 80 ms |
| Magazine / reserve | 7 / 21 | 64 / 128 |
| Hold to fire | No | Yes |

This is the first calibration step. Spread and burst recovery retain the
previously tested prototype values. Source recoil, inaccuracy and mobility use
different units and need a separate conversion. Armor, exponential distance
falloff, wall penetration and fixed recoil patterns are not implemented.
Limb damage and reload times still use upstream behavior. Existing projectile
weapons and models remain; this is not yet a full CS:GO weapon simulation.

### Expanded primary loadout

The loadout menu is enabled in the Eclipse Recoil client profile. Equipment
choices save immediately for the next spawn; the Desert Eagle is always granted
separately. Choose one primary, then either an SMG or up to four utility slots.
Selections persist across client restarts. Weapon names identify the reference;
models, icons and sounds reuse Red Eclipse assets.

| Reference | Red Eclipse slot | Torso damage | Interval | Magazine / reserve |
| --- | --- | --- | --- | --- |
| AK-47 | Zapper | 36 | 100 ms | 30 / 90 |
| AWP | Rifle | 115 | 1455 ms | 5 / 10 |
| MP9 | Plasma | 26 | 70 ms | 30 / 60 |
| XM1014 | Shotgun | 20 per pellet, 6 pellets | 350 ms | 7 / 32 |
| M249 | Minigun | 32 | 80 ms | 100 / 200 |
| PP-Bizon | SMG | 27 | 80 ms | 64 / 128 |

Each new profile uses a 4x headshot multiplier. AK-47, MP9, XM1014 and M249
are automatic; AWP is semiautomatic. Secondary input operates the AWP scope
without the original charging attack; scoped and unscoped shots share damage,
ammunition and cadence. Other alternate attacks remain blocked on client and
server. Eclipse Recoil allows Minigun in the loadout, whereas the original profile
retains its special-weapon classification.

New primary shots use impact projectiles without ricochet, splash damage,
residual status effects or fragments. They still travel at finite speed. Pistol, SMG and converted energy slots use the Bizon bullet
trail, muzzle and impact effects, including scoped AWP shots. Shotgun and
Minigun retain their original conventional muzzle, projectile and color
effects. All enabled shots stop on impact without ricochet or wall penetration. Energy weapon slots also use
the SMG firing sound; the original profile retains its own effects and sounds. Spread is provisional; recoil and reload timing are tuned per weapon. The shotgun currently has no CS:GO distance falloff; armor,
penetration and Source recoil patterns remain pending. This is a functional
arsenal prototype rather than a complete weapon simulation.

The TDM client makes bullet and pellet trails visible immediately, using short,
thin tracers: 12-unit trails, 50 ms bullet particles and 20 ms pellets.
The AK-47 has an explicit nonzero trail length, and former energy slots no
longer inherit beam-length trails.
These presentation settings preserve shot physics and the weapon-only
first-person view; original-profile trails retain their upstream values.
The native renderer refreshes cached muzzle/projectile effect references after
effect reloads so trails and impact marks keep their correct definitions.
The server preset sets effect scale and colour explicitly. Client-only variable
lookups must not be used in dedicated configuration: they become zero there,
making both tracers and impact stains invisible despite correct effect types.

For all-primary spawn and permission checks, run the dedicated server and:

```sh
scripts/csgopen/dev.sh tdm '-xexec "config/csgopen/arsenal-smoke.cfg"'
```

Expected result remains `SMOKE_DONE FAILURES 0`. This test also runs the
existing respawn and map-change checks after visiting every primary loadout.

### Equipment loadout

Press **comma (,)** to open the loadout menu. Choose one primary (AK-47,
AWP, Bizon, MP9, XM1014, M249 or the HE launcher); the Desert Eagle stays
as the fixed sidearm. Then choose **either** an additional Bizon/MP9 **or**
up to **four** utility slots, freely mixing HE, smoke and circular mines.
Slots can be empty; repeated types are allowed. A secondary cannot duplicate
the primary. Selecting an SMG clears all utility slots; selecting a grenade
clears the secondary. Switching back to grenades starts with empty slots.

Changes save immediately and apply at the **next respawn**, including after
restarting the game or changing maps. The server rejects invalid equipment,
ignores slots beyond four, and prevents secondary-plus-grenade combinations.
The launcher is a primary with its own **1+6 rounds**, independent of grenade
slots. Utilities are carried as ready quantities, without manual reloads;
the ammunition HUD shows the remaining quantity of the selected type.
Map pickups can replenish carried firearm ammunition but cannot grant new
weapons or replenish utilities. Respawn restores the chosen quantities.
Old primary-only profiles migrate to one HE, one smoke and one mine; bots
with no explicit loadout use the same utility defaults.

For dedicated-server equipment checks, run:

```sh
scripts/csgopen/dev.sh tdm '-xexec "config/csgopen/loadout-smoke.cfg"'
```

Expected result: `LOADOUT_DONE FAILURES 0`. This checks the menu save callbacks,
actual inventories over ten loadouts, malformed choices, respawn-only changes
and map persistence.

### HE grenade with fuse cooking

Each player and bot receives one HE independently of the primary loadout.
Press **G** to select it. Hold primary fire to start the **3-second fuse**;
release to throw. Time spent holding it is deducted from the remaining fuse.
Holding it for the full three seconds detonates it at the holder, rather than
throwing it automatically. Switching, dropping and pickups are blocked while
cooking. If the holder dies, an armed HE falls with the holder's momentum and
explodes when its remaining fuse expires. Death does not restart the fuse or
detonate it early. Carrying an unarmed grenade does not cause a death explosion.
The same rule applies to an armed smoke grenade and HE launcher round; smoke
opens normally when its remaining fuse expires. This requires rebuilt clients
and servers together for protocol 285; no map regeneration is needed.

The HE bounces off surfaces and players, and detonates immediately when hit by a bullet. The firearms
retain their no-bounce impacts. HE damage has no burn, status effects or extra
fragment projectiles. Self-damage and friendly fire remain active. Initial
tuning is 180 maximum base damage (scaled from 1800 engine damage) with a
72-unit blast radius and distance attenuation. These are prototype values,
not a verified CS:GO HE reproduction. One grenade is consumed per throw or
in-hand detonation. The loadout grants up to four utilities in total at respawn,
with no reserve or reload between throws. Utility pickups are blocked in this
preset so map loot cannot bypass the equipment choice. The Mine slot supplies the separate circular proximity mine.

### Smoke grenade

Smoke grenades occupy the same four utility slots as HE and mines. Press
**H** to select it, hold primary fire to cook the **3-second fuse**, then
release to throw. Holding it to the fuse limit deploys smoke at the holder.
Switching, dropping and pickups are blocked while cooking. Smoke causes no
damage, does not stick, and cannot be detonated by shooting it. An armed smoke
grenade falls on death and opens after its remaining fuse, even though the
owner is dead.

The cloud builds up over one second, lasts **18 seconds** including a two-second
fade, and has a **68-unit radius**. It persists after the thrower's death and
clears on map reset. Bullets pass through the cloud. Bots cannot acquire sight
through a dense cloud. Other player models, attachments and status effects
are also hidden when the viewing line crosses dense smoke, for both teams.
Player halos are disabled in Eclipse Recoil. Labels above weapons, pickups and
dropped loot are hidden; player labels are shown only for teammates.
Teammate labels and player radar indicators require sight without a wall or
dense smoke in between. Bots retain their existing last-seen memory, which can still cause shots. Inside the cloud, a gray overlay obscures the world; outside it,
dense alpha-blended particles provide the visual screen, with several
vertical layers and a central puff to conceal silhouettes. This initial spherical particle
implementation does not simulate smoke filling rooms or flowing around walls;
its shape, opacity and visibility at the edges require manual testing.
Clouds use live projectile replication; joining after deployment currently
does not reconstruct existing clouds. Models and inventory icons still use
the existing Grenade models, with gray tint for smoke and orange for HE.
The smoke inventory uses the otherwise unused Corroder slot. Smoke uses
zero damage and no blast, fragments, status effects or original mine explosion
FX. Respawn replenishes the chosen smoke quantity; no reserve is granted.

### Circular proximity mine

Press **J** to select the mine and fire toward the ground to place it with a
short throw. Each mine occupies one of the four utility slots, shared with
HE (**G**) and smoke (**H**). It attaches to geometry, arms fully **1.5 seconds after
landing**, then detects enemies within **32 units** in all directions with
an unobstructed line of sight. The owner and teammates do not trigger it.
Shooting the mine detonates it, including before it arms. Once triggered,
it explodes after 100 ms. Initial tuning is 180 base damage with a 64-unit
blast radius, with self-damage and friendly fire. It has no burn or fragments.
A mine also expires by exploding after 60 seconds; active mines persist after
the owner's death and clear on map reset. These are initial prototype values.

Smoke uses Corroder only as its internal inventory slot; it retains grenade
models, throwing physics, cooking and smoke behavior. Primary loadout selection
excludes this utility. Rocket now provides the HE grenade launcher. The original Red Eclipse profile retains its own weapons.

### HE grenade launcher

Press **K** to select the launcher when chosen as the primary weapon. It
spawns with **one loaded round and six reserves (seven total)**.
Fire launches an orange HE projectile with 650 initial speed versus 250 for
hand throws. Gravity, bounce behavior, 3-second fuse, 180 base damage and
72-unit blast radius match the HE. It can be detonated by shooting it;
self-damage and friendly fire remain active. Hold fire to cook the 3-second
fuse and release to launch; holding too long detonates it in the weapon.
Switching, dropping and picking up weapons are blocked while cooking.
A direct player hit deals 25 damage (25% of the preset's 100 HP), once per
target per grenade, before its later explosion. Recoil is gentle (0.1–0.2
vertical, no horizontal recoil, kick push reduced from 300 to 5). There is no guided flight. Press **R** to reload one round (1.8 seconds); the usual
client automatic reload preference can also reload it when empty. Ammunition
is independent of the hand-thrown HE. It uses the existing Rocket weapon model
and Grenade projectile model. Range and feel need manual tuning.

## Dedicated server on loopback

In one terminal:

```sh
scripts/csgopen/dev.sh server
```

In another terminal, run `scripts/csgopen/dev.sh tdm`, then use the game console:

```text
/connect 127.0.0.1 28801
```

Choose Alpha or Omega in the team menu before joining. `/spectate 0` remains
available for diagnostics with automatic team assignment.

The dedicated server uses the same preset, binds to **127.0.0.1**, and uses
UDP port 28801 for gameplay and 28802 for information queries. LAN discovery,
public master registration, and the master server are disabled. The native
HTTP server listens on **127.0.0.1:28888/TCP** for complete map-package downloads.
No router or cloud setup is
needed. Use exactly `127.0.0.1`: only this literal address is exempt from the
public-server guidelines prompt, without storing agreement to those terms.

For another port, use `CSGOPEN_PORT=28811 scripts/csgopen/dev.sh server` and
the same port in `connect`. Stop the server with Ctrl-C. Run only one instance
per profile; do not launch two Eclipse Recoil clients sharing the same profile.

### LAN server

Run `scripts/csgopen/server-lan.sh` to start the native dedicated server with
the same TDM preset and `config/csgopen/server-maps.cfg`. The separate
`.csgopen/server-lan/` profile listens on all IPv4 interfaces: UDP 28801 for
gameplay, UDP 28802 for information, UDP 28799 for LAN discovery, and TCP
28888 for map packages. Public master registration remains disabled.
The launcher writes its configuration on each run; stop it with Ctrl-C.

Start the dedicated server with `scripts/csgopen/server-lan.sh` for other
computers on the LAN. `scripts/csgopen/dev.sh server` is deliberately bound to
loopback and can only be reached from the same computer.

In the updated TDM client, open **Play Online**, click **Find LAN servers**,
and select the desired server from the list. The client preset enables LAN
discovery automatically, even after older persisted settings. Searching does
not connect to a server; entries and the connection panel show the destination
address and gameplay port. LAN discovery does not fetch the public master list;
**Refresh list** still explicitly requests that list.

If broadcast discovery is unavailable, use **Connect by IP** with the host
computer's LAN IPv4 address and game port `28801` (for example,
`192.168.1.10:28801`), or `/connect 192.168.1.10 28801` in the console.
For a server on the same computer, use `127.0.0.1` and port `28801`.
Allow incoming connections to the server if the macOS firewall asks.
Clients must share the LAN and use a compatible updated binary. The host must
run the updated client/server configuration; already installed release apps
need a rebuilt or new release package to include these changes.

TDM players connect as spectators and see **Pick your team** once the map
and server player state are ready, before joining the match. This also works
when joining from an active offline match, reconnecting, or using the console,
and does not depend on the equipment menu being enabled. Choose **Alpha** or **Omega**, or remain in **Spectate**. The menu
shows the connected server's IP and port. The existing server team request
performs the join; normal balance, capacity and spectator restrictions still
apply. **Change team** in the main menu opens the same chooser later. Player
Setup remains available for equipment selection. The original client profile
retains its existing loadout flow.

### Rotation, voting, and automatic map packages

`scripts/csgopen/dev.sh server` reads `config/csgopen/server-maps.cfg` without
injecting a fixed starting map. With `sv_defaultmap ""` and `sv_rotatemaps 2`,
the server selects a random starting map from the configured pool. The optional
`server <map>` argument still overrides the starting map for diagnostics.

The small-group pool contains 21 native maps (Ennui through Fortitude from the
local navigation-footprint comparison) and seven converted maps: `ar_baggage`,
`cs_agency`, `de_bank`, `de_canals`, `de_dust2`, `de_lake`, and `de_safehouse`.
`de_stmarc` is excluded because its conversion needs repair. Install all seven
converted ZIPs in `data/csgopen/` before using the pool. Edit the CFG and restart
the server to change the map list or match settings.

Matches last 10 minutes without a score limit or overtime, followed by 10
seconds of results and a 20-second ballot. `sv_votechoices 3` draws three
unique random maps from the rotation, excluding the current map. The server
synchronizes the shortlist through the read-only `votemaps` variable; updated
clients show three clickable map previews with titles in the voting panel. Votes must choose one of those
maps and retain the current mode and mutators. Earlier proposals are cleared,
and solo players cannot bypass the ballot through the upstream veto shortcut.
`sv_voteinterm 0` waits for the full ballot: the map with most votes wins,
ties are resolved randomly, and an empty ballot chooses randomly from the
three offered maps. Set `sv_votechoices 0` to restore upstream free proposals.
Both clients and server must be rebuilt for the shortlist menu and validation;
no new network message or protocol version is required.

The server announces each selected ZIP's name, byte size, CRC32, and HTTP port
before announcing the map. The TDM client enables `mapautodownload` and checks
its installed ZIP and private `map-packages/<map>_<crc>.zip` cache. Missing or
different packages download from `/map-package` on the **connected game
server's IP**, with progress on the loading screen. The client checks size and
CRC32, validates the ZIP's paths, mounts it, and only then loads the map.
Failed downloads remain outside gameplay and display a retry message. Reconnect
after correcting the problem. Failure and cancellation remove partial files.

Packages may contain only `maps/<map>.{mpz,cfg,png,txt,wpt}` and
`csgopen/imported/<map>/*`; MPZ and CFG are required. Limits are 512 MiB
compressed and 2 GiB uncompressed. Traversal, encrypted entries, malformed
directories, and files outside that map's namespace are rejected. ZIPs are
mounted rather than extracted. Downloaded versions take precedence over
installed content; imported models and textures refresh when mounted.
Replace ZIPs and restart the server to refresh its package metadata cache.
CRC32 detects corruption and identifies cached versions; it is not a
cryptographic signature.

Native maps need no extra ZIP and retain their existing automatic
MPZ/CFG/preview transfer. Both peers need builds containing this extension for
complete ZIP downloads; older clients do not understand the announcement.
It uses the existing reliable command channel without changing the upstream
protocol number. Downloaded caches remain inside the user's client profile.

The initial transport is **HTTP on loopback**, using the engine's asynchronous
network loop without an external downloader or new runtime dependency. HTTPS,
remote hosting, and public/LAN deployment are not configured by the development
launcher. `CSGOPEN_HTTP_PORT=28889 scripts/csgopen/dev.sh server` changes the
package port. A deployment profile must bind both gameplay and HTTP listeners
appropriately and make both ports reachable by its players.

The shortlist smoke test launches isolated native client/server profiles on
loopback and takes about one minute per run. It checks three distinct choices,
current-map exclusion, solo-vote timing, and the selected map; `--no-vote`
checks empty-ballot fallback. Logs stay under `.csgopen/votechoices-test/`.

```sh
python3 scripts/csgopen/test_votechoices.py
python3 scripts/csgopen/test_votechoices.py --no-vote
```

Package regression tests use an isolated loopback server without public registration:

```sh
python3 scripts/csgopen/test_server_maps.py -v
```

Repeatable smoke test, with the server already running on the default port:

```sh
scripts/csgopen/dev.sh tdm '-xexec "config/csgopen/smoke.cfg"'
rg 'CHECK_FAIL|RESPAWN_ELAPSED|SMOKE_DONE|SMOKE_TIMEOUT' .csgopen/logs/tdm-client.log
```

The test chooses a name, connects, checks synchronized rules and actual weapon
state, triggers suicide, requests another spawn through spectator/rejoin,
checks the delay, and changes the server map to Dutility. It closes the client;
the server keeps running. Expected result: `SMOKE_DONE FAILURES 0`, with no
`CHECK_FAIL` or timeout. The client's exit code alone is insufficient. This
test does not verify physical input, aiming, friendly fire from actual shots,
regeneration after damage, or rendering quality.

## Profiles, tuning, and troubleshooting

All local runtime state is ignored by Git. Locally imported Source content is
also ignored, but lives outside the disposable runtime tree:

| Path | Purpose |
| --- | --- |
| `.csgopen/original/` | Original configuration and cache |
| `.csgopen/csgopen-client/` | Preset client, integrated server, and cache |
| `.csgopen/server/` | Dedicated server |
| `.csgopen/logs/` | Build and launch logs; launch logs are overwritten on restart |
| `data/csgopen/<map>.zip` | Self-contained local map package: MPZ, CFG, preview, models, textures, and collision |

Launchers regenerate the managed initialization files for their own profiles.
Edit `config/csgopen/tdm.cfg` for server settings, then restart the sessions.
Edit `config/csgopen/server-maps.cfg` for dedicated-server rotation, voting,
match duration, and complete map-package distribution.
`config/csgopen/client.cfg` contains only client preferences. Server examples:
`sv_playerspawndelay` and `sv_botspawndelay` are in milliseconds;
`sv_movespeed` is a multiplier; `sv_moveaccelscale` and `sv_movebrakescale`
control ground velocity response. The new coefficients are needed because
upstream uses one coast parameter for both acceleration and braking.
`sv_savevars` preserves preset defaults across cleanup and map changes.
To return to the reference gameplay, quit and run `original`, which retains
arena defaults of 1000 health, speed 1, and the full set of impulse capabilities.

- Missing assets (`asset mancanti`) or mismatched submodules: complete the
  update to the recorded revisions. A partial clone cannot launch correctly.
- pkg-config errors: run `check` and inspect the native Homebrew installation.
  OpenAL Soft is keg-only; the script adds its pkg-config path.
- Linux X11/GL symbols: use this Makefile with the Darwin toolchain, without
  manually setting `PLATFORM` to a Linux target. X11 libraries are not needed.
- Missing or non-native binary: run `build` again. Do not use the prebuilt
  Linux executables included in the assets.
- Connection failure: check that the dedicated server is still running,
  verify the port, and inspect `server.log`. To inspect sockets, run
  `lsof -nP -iUDP:28801 -iUDP:28802`.
- Initial spawn blocked: set a name and leave spectator mode. Executing
  `primary 1` in CubeScript does not simulate a physical key press.
- Observed runtime warnings: PNG iCCP profiles with invalid CRCs and some
  missing upstream IQM animations. An Apple driver sampler warning also
  appears on the baseline. No features were disabled to hide these warnings;
  visual inspection remains necessary. Dutility also reports a rail outside
  the map; the smoke test uses it only to exercise map changes.

No automatic commits or pushes. Linux and Windows retain their existing build
branches, but have not been compiled on this Mac.


### Source ladders and window clearance

The converter exports authored ladder brushes as ladder material volumes with
fine one-unit placement, without adding render or collision triangles. The TDM
motor climbs them by holding forward and handles the roof transition. Reviewed
House window frames use four simple collision volumes around their openings,
within the original triangle budget. Player and bot scale is 0.8 in the TDM
preset, with a lower crouch silhouette; effective step/climb heights stay at
7/13 world units. The original gameplay profile keeps its dimensions and ladder
controls. See the Safehouse checks in [validation](validation.md).

The TDM first-person view displays weapon/arms without the separate body model,
so leg animations cannot obstruct the view on stairs. This is a client display
preference; it does not change traversal or require regenerating map packages.
