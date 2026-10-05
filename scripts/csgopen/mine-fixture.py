#!/usr/bin/env python3
"""Stage isolated profiles for the opt-in native mine contact tests."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / ".csgopen/mine-contact-test"


def stage():
    for name, mapname in (("lake", "de_lake"), ("native", "echo")):
        profile = BASE / name
        profile.mkdir(parents=True, exist_ok=True)
        (profile / "init.cfg").write_text("firstrun 0\nfullscreen 0\nscreenw 640\nscreenh 480\n")
        (profile / "localinit.cfg").write_text(
            'exec "config/csgopen/tdm.cfg"\nsv_botbalance 0\n'
            'servermaster ""\nserverlanport 0\nhttpserver 0\n'
        )
        (profile / "autoexec.cfg").write_text('exec "config/csgopen/client.cfg"\n')
        (profile / "verify.cfg").write_text(
            'name "Mine contact test"\nshowloadoutmenu 0\n'
            f'tdm {mapname}\n'
            'sleep 12000 [spectate 0; sleep 3000 [minecontacttest; sleep 1000 [quit]]]\n'
            'sleep 45000 [echo MINE_TIMEOUT; quit]\n'
        )
    print(BASE)


if __name__ == "__main__":
    stage()
