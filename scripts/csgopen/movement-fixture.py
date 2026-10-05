#!/usr/bin/env python3
"""Stage a local native map and scripts for the opt-in movement test client.

Run from any directory; all generated assets and profiles stay in .csgopen.
Build the MPZ with build/build.cfg, then copy build/maps/csgopen_movement.*
into data/maps before running verify/verify.cfg. See doc/csgopen/validation.md.
"""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / '.csgopen/movement-fixture'
MODEL = BASE / 'data/csgopen/movement-fixture'
HEIGHTS = {1: 7, 2: 7.5, 3: 13, 4: 14, 5: 6, 6: 13, 7: 13, 8: 13, 9: 13}


def stage():
    MODEL.mkdir(parents=True, exist_ok=True)
    vertices, faces = [], []

    def box(x0, x1, y0, y1, z0, z1):
        start = len(vertices)
        vertices.extend([
            (x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
            (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1),
        ])
        for quad in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
                     (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
            for triangle in ((quad[0], quad[1], quad[2]), (quad[0], quad[2], quad[3])):
                faces.extend([tuple(start+i+1 for i in triangle),
                              tuple(start+i+1 for i in reversed(triangle))])

    for index, height in HEIGHTS.items():
        y = 80+40*index
        box(160, 240, y-14, y+14, 512, 512+height)
        if index in (5, 8):
            box(155, 245, y-15, y+15, 512+height+19, 512+height+23)

    (MODEL / 'fixture.obj').write_text(
        'g solid\n'+''.join(f'v {-y:g} {z:g} {x:g}\n' for x, y, z in vertices)
        + ''.join('f '+' '.join(map(str, face))+'\n' for face in faces))
    shutil.copy2(ROOT / 'data/textures/default.png', MODEL / 'skin.png')
    (MODEL / 'obj.cfg').write_text(
        'objload "fixture.obj"\nobjskin "*" "skin.png"\n'
        'mdlcullface 0\nmdlscale 100\nmdltricollide 1\n')
    maps = BASE / 'data/maps'
    maps.mkdir(exist_ok=True)
    (maps / 'csgopen_movement.cfg').write_text('mapmodel "csgopen/movement-fixture"\n')
    for purpose in ('build', 'verify'):
        profile = BASE / purpose
        profile.mkdir(exist_ok=True)
        (profile / 'init.cfg').write_text('firstrun 0\nfullscreen 0\nscreenw 640\nscreenh 480\n')
        rules = 'exec "config/csgopen/tdm.cfg"\nsv_botbalance 0\n' if purpose == 'verify' else ''
        (profile / 'localinit.cfg').write_text(rules+'servermaster ""\nserverlanport 0\nhttpserver 0\n')
        (profile / 'autoexec.cfg').write_text('exec "config/csgopen/client.cfg"\n')
    (BASE / 'build/build.cfg').write_text('''edit csgopen_movement
sleep 10000 [
    edittoggle
    newmapfloor 1
    newmap 10 csgopen_movement
    mapmodelreset 0
    exec "maps/csgopen_movement.cfg"
    newent mapmodel 0 0 0 0 100 100
    entpos 0 0 0
    entcancel
    newent playerstart 1 270 0 0 0 0 0
    entpos 100 80 544
    entcancel
    newent playerstart 2 270 0 0 0 1 0
    entpos 100 480 544
    entcancel
    savemap csgopen_movement
    echo MOVEMENT_FIXTURE_BUILT
    sleep 1000 [quit]
]
sleep 45000 [echo MOVEMENT_FIXTURE_TIMEOUT; quit]
''')
    (BASE / 'verify/verify.cfg').write_text('''name "Movement fixture"
showloadoutmenu 0
tdm csgopen_movement
sleep 10000 [loop i 10 [movementcase $i]; movementjump; movementdone; sleep 1000 [quit]]
sleep 60000 [echo MOVEMENT_TIMEOUT; quit]
''')
    print(BASE)


if __name__ == '__main__':
    stage()
