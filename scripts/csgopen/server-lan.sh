#!/bin/bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
STATE="$ROOT/.csgopen"
RUNTIME="$STATE/server-lan"
BINARY="$ROOT/src/eclipse-recoil_server_native"

[[ -x "$BINARY" ]] || { echo "Binario server mancante: eseguire scripts/csgopen/dev.sh build" >&2; exit 1; }
[[ $# -eq 0 ]] || { echo "Uso: $0" >&2; exit 1; }

mkdir -p "$RUNTIME" "$STATE/logs"
export REDECLIPSE_HOME="$RUNTIME"
export ECLIPSE_RECOIL_HOME="$RUNTIME"
unset REDECLIPSE_DATADIR REDECLIPSE_EXTRADIRS REDECLIPSE_PATH
unset ECLIPSE_RECOIL_DATADIR ECLIPSE_RECOIL_EXTRADIRS ECLIPSE_RECOIL_PATH
cd "$ROOT"

cat > "$RUNTIME/servinit.cfg" <<'EOF'
exec "config/csgopen/tdm.cfg"
exec "config/csgopen/server-maps.cfg"
serverip "0.0.0.0"
serverport 28801
serverlanport 28799
servermaster ""
masterserver 0
httpserverip "0.0.0.0"
httpserverport 28888
httpserver 1
EOF

echo "Server LAN: gioco UDP 28801, discovery UDP 28799, mappe TCP 28888."
echo "Nella console client: /serverlanport 28799 e /searchlan 1, poi aggiornare la lista server."
exec "$BINARY" "-h$RUNTIME" "-p$ROOT/data/csgopen" \
    "-g$STATE/logs/server-lan.log" -sm -ss1 -sp28801
