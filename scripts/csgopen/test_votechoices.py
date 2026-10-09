#!/usr/bin/env python3
"""Run a native client/server shortlist smoke test in isolated loopback profiles."""
import argparse
from pathlib import Path
import socket
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--no-vote', action='store_true', help='exercise empty-ballot fallback')
    parser.add_argument('--mid-match', action='store_true', help='exercise immediate solo majority while playing')
    args = parser.parse_args()
    state = ROOT / '.csgopen/votechoices-test'
    state.mkdir(parents=True, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix='run-', dir=state))
    server_profile, client_profile = run / 'server', run / 'client'
    server_profile.mkdir()
    client_profile.mkdir()
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    (server_profile / 'servinit.cfg').write_text(f'''exec "config/csgopen/tdm.cfg"
exec "config/csgopen/server-maps.cfg"
sv_mainmaps "echo dutility ennui park"
sv_votestyle {3 if args.mid_match else 0}
sv_timelimit 1
sv_gamespeed 100
sv_intermlimit 100
sv_votelimit 3000
sv_waitforplayers 0
sv_botlimit 0
sv_savevars
serverip "127.0.0.1"
serverport {port}
serverlanport 0
servermaster ""
masterserver 0
httpserver 0
''')
    ballot = '''test_chosen = (at $votemaps 0)
        start $mapname $gamemode $mutators
        sleep 250 [
            test_check (= (getvote -1) 0) outside_shortlist_rejected
            start (concatword "maps/" $test_chosen) $gamemode $mutators
            sleep 500 [
                test_check (= $gamestate $G_S_VOTING) solo_vote_waits
                test_check (> (getvote -1) 0) vote_registered
            ]
        ]'''
    result = '(=s $mapname (concatword "maps/" $test_chosen))'
    if args.no_vote:
        ballot = 'test_check (= (getvote -1) 0) empty_ballot'
        result = '(>= (indexof $test_choices (substr $mapname 5)) 0)'
    if args.mid_match:
        ballot = '''test_chosen = (at $votemaps 0)
        start $mapname $gamemode $mutators
        sleep 250 [
            test_check (= (getvote -1) 0) current_map_rejected
            sleep 2000 [start (concatword "maps/" $test_chosen) $gamemode $mutators]
        ]'''
        result = '(=s $mapname (concatword "maps/" $test_chosen))'
    (client_profile / 'autoexec.cfg').write_text(f'''exec "config/csgopen/client.cfg"
showloadoutmenu 0
name "Vote shortlist test"
test_failures = 0
test_check = [if (! $arg1) [test_failures = (+ $test_failures 1); echo (concat CHECK_FAIL $arg2)] [echo (concat CHECK_PASS $arg2)]]
test_poll = [
    if (= $gamestate ${'G_S_PLAYING' if args.mid_match else 'G_S_VOTING'}) [
        test_check (= (listlen $votemaps) 3) three_candidates
        test_choices = $votemaps
        test_check (< (indexof $votemaps (substr $mapname 5)) 0) excludes_current
        test_check (! (=s (at $votemaps 0) (at $votemaps 1))) distinct_01
        test_check (! (=s (at $votemaps 0) (at $votemaps 2))) distinct_02
        test_check (! (=s (at $votemaps 1) (at $votemaps 2))) distinct_12
        echo (concat SHORTLIST $votemaps)
        sleep 100 [gameui_open ui_gameui_vote]
        sleep 1500 [screenshot "ballot"]
        {ballot}
        sleep 7000 [
            echo (concat RESULT_MAP $mapname)
            test_check {result} selected_map_loaded
            test_check {'(= (listlen $votemaps) 3)' if args.mid_match else '(=s $votemaps "")'} shortlist_next_round
            echo (concat VOTECHOICES_DONE FAILURES $test_failures)
            quit
        ]
    ] [sleep 100 [test_poll]]
]
connect 127.0.0.1 {port}
sleep 7000 [spectate 0; test_poll]
sleep 120000 [echo VOTECHOICES_TIMEOUT; quit]
''')
    with (run / 'server.log').open('w') as output:
        server = subprocess.Popen([
            str(ROOT / 'src/eclipse-recoil_server_native'), f'-h{server_profile}',
            '-si127.0.0.1', '-sm', '-ss1', f'-sp{port}',
        ], cwd=ROOT, stdout=output, stderr=subprocess.STDOUT)
        try:
            time.sleep(2)
            if server.poll() is not None:
                raise RuntimeError((run / 'server.log').read_text())
            subprocess.run([
                str(ROOT / 'src/eclipse-recoil_native'), f'-h{client_profile}',
                f'-g{run / "client.log"}', '-sm', '-ss0', '-dw640', '-dh480', '-df0',
            ], cwd=ROOT, timeout=150, check=True)
        finally:
            server.terminate()
            server.wait(timeout=10)
    log = (run / 'client.log').read_text()
    assert 'VOTECHOICES_DONE FAILURES 0' in log, str(run / 'client.log')
    assert 'CHECK_FAIL' not in log and 'VOTECHOICES_TIMEOUT' not in log
    print(f'VOTECHOICES_DONE FAILURES 0: {run}')


if __name__ == '__main__':
    main()
