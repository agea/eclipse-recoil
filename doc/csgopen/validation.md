# Verifica della milestone

Data: 30 settembre 2026. Implementazione e verifiche automatiche completate;
collaudo interattivo ancora necessario. Nessun commit o push automatico;
commit di snapshot successivamente richiesto dall'utente, senza push.

## Provenienza e ambiente

- Fork: `https://github.com/agea/csgopen-base.git`, remote `origin`.
- Upstream aggiunto: `https://github.com/redeclipse/base.git`.
- Commit iniziale: `faf378d12558addc700d0e464e7e8c3a39fbceee`, branch originario `master`.
- Branch di lavoro: `feat/tdm-prototype`. Nessun lavoro locale preesistente;
  nessun commit prima della richiesta esplicita di snapshot, nessun push.
- `sysctl -n hw.model`: Mac14,10; `uname -m`: arm64. macOS 27.0, build 26A428.
  Renderer rilevato dal client: Apple M2 Pro.
- Xcode: `/Applications/Xcode.app/Contents/Developer`; Apple clang 21.0.0,
  target arm64-apple-darwin27.0.0. GNU Make 3.81.
- pkg-config: pkgconf 2.5.1. SDL ABI 2.32.72 fornita da sdl2-compat (SDL3),
  SDL2_image 2.8.12, OpenAL Soft 1.25.2, libsndfile 1.2.2, zlib SDK 1.2.12.
- Homebrew ha segnalato macOS 27 come versione prerelease non supportata.

## Baseline senza modifiche al gameplay

1. `git clone --recurse-submodules https://github.com/agea/csgopen-base.git csgopen-base`.
   Rete del sandbox non disponibile; rieseguito con autorizzazione dell'ambiente.
2. `git remote add upstream https://github.com/redeclipse/base.git` e
   `git switch -c feat/tdm-prototype`.
3. Analisi del Makefile: Darwin finiva nel ramo pkg-config X11/GL Linux.
   Analisi launcher: Darwin non riconosciuto. `console.cpp` usava X11 su tutti
   i sistemi non Windows. Correzioni isolate in questi tre file.
4. `HOMEBREW_NO_AUTO_UPDATE=1 HOMEBREW_NO_INSTALL_CLEANUP=1 brew install sdl2 sdl2_image openal-soft libsndfile`.
   Installate le dipendenze mancanti. Homebrew ha anche aggiornato dipendenze
   transitive dei pacchetti richiesti; non è stato eseguito `brew upgrade` globale.
5. `PKG_CONFIG_PATH="$(brew --prefix openal-soft)/lib/pkgconfig${PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}" make -C src -j4 client server`.
   **PASS**: entrambi i binari Mach-O arm64. Log:
   `.csgopen/logs/baseline-build.log`. Avvisi upstream su funzioni non usate,
   precedenze/logica e conversioni; nessun errore.
6. `file` e `otool -L`: architettura arm64; OpenGL.framework nativo, SDL/Cocoa,
   OpenAL Soft e libsndfile. `lipo -verify_arch` sulle quattro librerie: **PASS**.
7. Primo avvio anticipato durante il clone: **FAIL**, contenuto `maps/readme.txt`
   ancora assente. Processo chiuso; non considerato una verifica grafica.
8. `bash -n scripts/csgopen/dev.sh` e `scripts/csgopen/dev.sh check`: **PASS**.

I log completi e la copia del diff di piattaforma sono in `.csgopen/logs/` e
non sono tracciati in Git. L'esito finale e la checklist seguono sotto.

## Verifiche eseguite

### Raffica: aggiornamento del 1 ottobre 2026

Aggiunto accumulo di dispersione per arma, con primo colpo invariato,
incremento 0.35, limite 1.5 e recupero dal limite in 1200 ms. Default
`spreadburstadd=0` conserva il profilo originale. Test delle funzioni reali
estratte da `game.h` e `weapons.cpp` nel harness C++ con dipendenze simulate:
**PASS** per raffica SMG, saturazione, recupero a 600/1200 ms, indipendenza
tra armi, bonus crouch, alt-fire escluso, accumulo disabilitato, indice invalido,
limite zero e actor nuovo. Mantiene i test della postura e delle 256
combinazioni originali. Log `.csgopen/logs/burst-unit.log`, sorgente locale
`.csgopen/burst-unit.cpp`. Non equivale a una prova di tiro con input reale.

Build client e dedicato: **PASS**, `.csgopen/logs/burst-build-stdout.log`.
Smoke aggiornato: **PASS**, `SMOKE_DONE FAILURES 0`, nessun timeout/comando
sconosciuto, respawn 2997 ms. Parametri burst confermati prima/dopo morte e
cambio Echo→Dutility; getter dell'accumulo zero agli spawn. Log:
`.csgopen/logs/burst-smoke.log`. Il test non produce una raffica fisica;
l'aumento nonzero e il recupero sono verificati nel harness, mentre rosata,
rinculo combinato e sensazione richiedono la prova manuale su muro.

### Taratura del movimento: primo feedback

L'utente ha giudicato l'arresto leggermente brusco nella prova su Echo senza
bot. `sv_movebrakescale` passa da 1.5 a 1.25; velocità 0.55 e accelerazione
0.75 restano quelle della prova. Aggiornato il valore atteso nello smoke.
La risposta a terra converge più lentamente; l'utente ha successivamente
approvato il movimento con frenata 1.25. Le esecuzioni storiche sotto usavano
frenata 1.5 e non costituiscono una verifica del nuovo valore.
Avvio locale rieseguito: personaggio vivo, speed 0.55, accel 0.75, brake 1.25,
impulse 1 e nessun bot, senza comandi sconosciuti. Log:
`.csgopen/logs/movement-brake-125.log`. Smoke completo non rieseguito per
questa taratura al momento del primo avvio.

### Conferme manuali e precisione delle armi

L'utente conferma salute senza regen, respawn con ripristino dell'equipaggiamento
e persistenza delle regole dopo cambio mappa/nuova partita, compreso friendly
fire attivo. Il log `.csgopen/logs/ff-manual.log` contiene anche uccisioni del
bot alleato. Movimento approvato con frenata 1.25. Questi sono risultati
manuali riferiti dall'utente, non misure strumentali della velocità o del danno.

L'utente non ha notato problemi di precisione nel preset precedente, poi ha
richiesto esplicitamente meno precisione correndo e più precisione in crouch.
La nuova taratura deve essere provata manualmente: non estendere a essa
l'approvazione delle armi precedenti.

Test della funzione reale `accmodspread` estratta da `weapons.cpp` e compilata
in un harness C++ con actor/ladder/lookup delle variabili simulati: **PASS**.
Pesi letti dal preset: standing 1, running/sprinting 3, crouch 0.5,
crouch moving 1, walking 2, running airborne 5, ladder senza penalità aria.
Con pesi originali, confronto con la funzione del commit HEAD su 256
combinazioni stato/arma/zoom: **PASS**, stesso risultato. Il test non simula
input fisico, collisioni o traiettorie dei proiettili. Sorgente e log locali:
`.csgopen/accuracy-unit.cpp`, `.csgopen/logs/accuracy-unit.log`.

`dev.sh build`: **PASS**, client ricompilato e dedicato già aggiornato,
binari arm64. Smoke completo con frenata 1.25 e tutti i nuovi parametri di
dispersione: **PASS**, `SMOKE_DONE FAILURES 0`, nessun timeout/comando
sconosciuto, respawn misurato 2996 ms. Parametri confermati prima/dopo morte
e dopo cambio Echo→Dutility. Log: `.csgopen/logs/accuracy-build-stdout.log`
e `.csgopen/logs/accuracy-smoke.log`. Il confronto della rosata con colpi
reali in piedi/corsa/crouch resta da eseguire manualmente.

### Aggiornamento: friendly fire attivo

Su richiesta successiva dell'utente, il preset abilita ora il friendly fire
per umani e bot: `playerteamdamage=7`, `botteamdamage=7`,
`damageteamscale=1`. Sostituisce l'obiettivo iniziale di disabilitarlo.
Smoke aggiornato rieseguito contro il dedicato loopback: **PASS**,
`SMOKE_DONE FAILURES 0`, respawn misurato 2999 ms, valori conservati dopo
respawn e cambio Echo→Dutility. Log: `.csgopen/logs/ff-smoke.log`.
Le prove della prima milestone riportate sotto sono storiche.

L'utente ha riferito che la prova di equipaggiamento (punto 5) sembra corretta;
non ha confermato separatamente tutte le varianti dopo respawn/cambio mappa.
Ha inoltre verificato che il preset precedente bloccava i danni al bot alleato,
con simbolo di divieto: quel risultato riguarda il comportamento ora sostituito.
Il danno reale tra alleati è stato poi confermato nella sessione manuale,
aspettando la fine della protezione di spawn. Una sessione con `sv_botbalance 4`
fornisce un bot alleato e due avversari; non serve un secondo client per questa
prima verifica umano→bot.

### Baseline avviata prima del gameplay

```sh
scripts/csgopen/dev.sh original '-xtdm echo; sleep 20000 [quit]'
```

**PASS avvio/log, non collaudo visivo**: exit 0, contesto OpenGL 4.1 Metal
(-91.7), GLSL 4.10, OpenAL Soft con uscita stereo 48 kHz, caricamento Echo
CRC `4f8346be`, scambio game info e inizio partita con bot. Copia preservata:
`.csgopen/logs/baseline-original.log` e `baseline-original-stdout.log`.
Non è stato necessario cambiare versione GL o disabilitare il rendering.

Il controllo UI non ha individuato l'eseguibile non impacchettato come app
controllabile; la selezione diretta del suo percorso è fallita. Non ho
osservato/interagito con la finestra del gioco. Il preview incluso della
mappa non costituisce prova del rendering di questo client.

### Prototipo e script

| Prova | Esito ed evidenza |
| --- | --- |
| Build client e dedicato dopo patch gameplay e loopback | PASS; `prototype-build.log`, `script-build-stdout.log`; binari arm64 |
| `bash -n scripts/csgopen/dev.sh`, `sh -n redeclipse.sh` | PASS; non è stato eseguito ShellCheck |
| `dev.sh check` | PASS; librerie native e SDK presenti |
| check/build da `/private/tmp` attraverso symlink con spazi nel percorso | PASS; `paths-and-errors.log`; nessuna dipendenza dal cwd |
| `CSGOPEN_JOBS=0` e nome mappa `invalid/path` | PASS: exit 1 e messaggi comprensibili, prima dell'avvio |
| Primo client TDM locale, uscita da spectator | PASS; stato vivo, salute reale 100, clip pistola 10 e SMG 40 |
| Dedicato e socket | PASS; solo UDP 127.0.0.1:28801 e 127.0.0.1:28802, `server-sockets.txt` |
| Reset default server (`sv_resetvars 1`) | PASS: salute 100 e speed 0.55 conservati, `server-stdout.log` |
| Smoke client→dedicato, morte e nuovo spawn | PASS; `final-smoke.log`, zero assert falliti, salute/equipaggiamento ripristinati |
| Cambio Echo→Dutility sul dedicato | PASS; CRC Dutility `7232560a`, game info, nuovo match, regole condivise ancora attive |
| Comandi preset e sincronizzazione | PASS nei log: nessun comando sconosciuto/errori di configurazione; health 100, impulse 1, abilities 7383, accel 0.75, brake 1.5 |
| Profilo originale dopo il prototipo | PASS avvio e default arena conservati; `final-original.log` |
| `git diff --check`, submodule ai commit registrati, stato asset | PASS; 40 submodule, nessun asset modificato, `submodules.txt`, `asset-status.txt` |

Il dedicato è stato avviato con:

```sh
scripts/csgopen/dev.sh server '-xecho CSGOPEN_SERVER_READY; echo (concat HEALTH $sv_playerhealth IMPULSE $sv_playerimpulse REGEN $sv_playerabilities ACCEL $sv_moveaccelscale BRAKE $sv_movebrakescale); sv_resetvars 1; echo (concat RESET_HEALTH $sv_playerhealth RESET_SPEED $sv_movespeed)'
```

Socket ispezionati con `lsof -a -p <PID-del-test> -nP -i`. HTTP, LAN discovery
e master disabilitati prima di aprire socket; nessun intervento sul router.
Il processo di test viene chiuso alla fine delle verifiche.

Smoke ripetibile del repository, dedicato sulla porta di default già attivo:

```sh
scripts/csgopen/dev.sh tdm '-xexec "config/csgopen/smoke.cfg"'
rg 'CHECK_FAIL|RESPAWN_ELAPSED|SMOKE_DONE|SMOKE_TIMEOUT' .csgopen/logs/tdm-client.log
```

Esito finale: `SMOKE_DONE FAILURES 0`, nessun timeout. Misura finale respawn:
2998 ms; altra esecuzione 3005 ms. La misura sottrae timestamp client di
messaggi distinti, non misura direttamente il clock del server: la verifica
usa tolleranza 50 ms e conferma che a 2500 ms il personaggio non sia vivo.
Il ritardo server resta precisamente `playerspawndelay=3000` ed è controllato
in `m_delay` e nella coda di spawn. Lo smoke verifica valori sincronizzati,
salute/armi reali e assenza delle altre 15 armi possedute, prima e dopo morte.
Richiede il nuovo spawn con spectator/rientro dopo il suicidio: **non prova
il click fisico di respawn**. Il cambio mappa verifica regole, CRC e match,
non la percorribilità di Dutility.

Controllo finale del profilo originale con lo stesso binario:

```sh
scripts/csgopen/dev.sh original '-xtdm echo; sleep 8000 [echo (concat ORIGINAL_DEFAULTS HEALTH $playerhealth SPEED $movespeed IMPULSE $playerimpulse ACCEL $moveaccelscale BRAKE $movebrakescale); quit]'
```

Atteso/osservato: salute actor 1000, speed 1, impulse 4095, nuovi coefficienti
entrambi 1. Log originale separato da quello CSGOpen.

### Prove fallite e correzioni

- Avvio senza asset completi: fallimento preservato nella baseline; risolto
  attendendo l'inizializzazione dei submodule.
- Prima connessione dedicata: prompt upstream delle linee guida pubbliche,
  con errori UI `p_label_align`. Copia `remote-smoke-guidelines-blocked.log`.
  Il documento upstream esclude uso offline/server senza master. Applicata
  eccezione limitata al literal 127.0.0.1 in `connectserv`; nessun consenso
  impostato. Connessione reale rieseguita con successo.
- Primo script respawn: `primary 1; primary 0` non genera un tasto premuto
  (`D` in `command.cpp` usa `keypressed`); personaggio rimasto morto. Sostituito
  con spectator/rientro, senza patch alla logica di respawn.
- Primo assert strettamente `>=3000` sui timestamp client: misura 2994 ms,
  fallimento del test. Introdotta tolleranza dichiarata, non abbassato il
  ritardo di gioco. Riesecuzione finale passata.

## Verificato soltanto nel codice

- TDM già nativo con Alpha/Omega, nessun mutatore team necessario.
- Regen subordinata alla capacità A_A_REGEN, rimossa per umani e bot.
- Friendly fire attivo: teamdamage A_T_PLAYER per umani e bot, fattore danno
  alleati 1 nei percorsi server/client (richiesta successiva al preset iniziale).
- Solo IM_T_JUMP conserva il salto normale; le altre capacità impulse non
  sono consentite. Crouch e le capacità MOVE/JUMP/CROUCH restano presenti.
- I nuovi coefficienti usano GFVAR e la sincronizzazione esistente; default 1
  conserva la precedente formula. Nessuna modifica al tempo globale.
- Server valida loadout/pickup e armi disabilitate; SMG è fullauto, Rifle no.
- Regole IDF_GAMEMOD, separate da IDF_MAP; configurazione letta prima dello
  spawn/socket, default salvati per cleanup. Nessun aggiornamento degli asset.
- Rami Linux/Windows preservati nella patch di piattaforma: non compilati qui.

Riferimenti a simboli, limiti e valori in [gameplay.md](gameplay.md).

## Procedure manuali e controlli residui

Vedere gli esiti confermati sopra per movimento, salute, respawn e persistenza.
Restano prove complete con due umani, percorribilità completa di Echo,
diagnosi visiva degli avvisi e taratura della nuova dispersione delle armi.

1. Avviare `original`: verificare finestra, testi, HUD, modelli e shader,
   audio, mouse/tastiera, ingresso in partita e assenza di artefatti grafici.
2. Avviare `tdm`, scegliere nome, `/spectate 0`; confermare squadre e spawn.
   Percorrere cortile e accessi di Echo senza parkour. Annotare spawn isolati
   o percorsi che richiedono movimenti vietati: Echo resta candidata finché
   questo controllo non passa.
3. Provare corsa, strafe, accelerazione, arresto; confronto con `original`.
   Annotare sensazione e velocità senza modificare `gamespeed`.
4. Saltare da fermo/in corsa, accovacciarsi. Provare ripetutamente salto in
   aria, dash, boost, wallrun/walljump, slide e vault: non devono attivarsi.
5. Alla comparsa verificare HP 100, pistola/SMG; sparo semiauto/automatico e
   ricarica. Passare sui pickup delle altre armi e tentare altri loadout:
   devono restare inutilizzabili. Controllare anche dopo respawn/cambio mappa.
6. Subire danno senza morire (dopo la protezione spawn), allontanarsi e
   attendere almeno 10 s: HP non deve risalire. Confermare danno reale e HUD.
7. Con un bot alleato (`sv_botbalance 4`) o due umani nella stessa squadra,
   sparare al compagno dopo protezione spawn e confermare danno e possibile
   morte; anche contro un avversario il danno deve esserci.
   Per due client sullo stesso Mac servono home/log separati; non usare due
   istanze del wrapper sul medesimo profilo. Un secondo computer non può
   collegarsi al bind loopback della milestone.
8. Morire e richiedere respawn con click/salto dopo l'animazione di morte;
   verificare limite di circa 3 s, armi/HP e capacità conservate. Variare
   spawndelay per umano e bot nel preset, riavviare e confrontare.
9. Cambiare mappa/ripartire partita e poi tornare a `original`: verificare
   isolamento delle regole anche con interazione completa.

## Problemi aperti e prossimo passo

Nessun blocco di compilazione o caricamento GL osservato. Restano avvisi
upstream: alcune animazioni IQM mancanti (zapper/claw/sword-idle2), profili
PNG iCCP con CRC errato e segnalazione driver Apple di sampler all'avvio.
Non sono stati corretti alterando gli asset né nascosti con feature toggle.
Dutility ha un rail fuori mappa e serve soltanto a provare il cambio livello.
Non è stato confermato visivamente se gli avvisi producano artefatti.

La milestone non è interamente collaudata finché la checklist non passa.
Prossimo intervento consigliato: chiudere il collaudo di Echo e misurare
velocità/tempi di accelerazione e arresto su un percorso a terra ripetibile;
tarare i tre coefficienti prima di introdurre un'arma o un rinculo nuovo.

## Cerchio munizioni e dispersione — 1 ottobre 2026

Build nativa client/dedicato completata e `git diff --check` superato.
Il client aggiornato è stato avviato su Echo senza bot; il log
`.csgopen/logs/ring-manual.log` conferma `RING_TEST_READY STATE 0 RING 1 ADD 0.35`.
Ispezione del codice: raggio calcolato con lo stesso spread del tiro primario,
scala limitata, glifi delle munizioni e animazioni conservati; default originale
0 e anteprime escluse. Verifica visiva di leggibilità, corsa, crouch, raffica
e recupero ancora da effettuare dall'utente.

## Accumulo pistola — 1 ottobre 2026

Incremento per colpo della sola pistola portato da 0.35 a 0.7 tramite
`pistolspreadburstscale 2`; SMG invariata. Build client/dedicato e diff check
superati. Harness locale delle funzioni reali get/addweapbloom: accumulo
crescente a intervalli 200/300/400 ms, limite, recupero e indipendenza arma
superati. Smoke dedicato `.csgopen/logs/pistol-smoke-retry.log`: FAILURES 0,
respawn 2995 ms, parametro sincronizzato e conservato dopo cambio mappa.
Il primo tentativo è andato in timeout durante l'avvio tardivo del server;
il secondo ha avuto un segfault nel caricamento grafico delle texture mixer.
Il terzo ha completato il collaudo. Causa del crash non determinata.
Valutazione della sensazione e visibilità della pistola demandata all'utente.

## Riferimento Desert Eagle / PP-Bizon — 1 ottobre 2026

Prima fase solo configurazione, nessuna modifica binaria o agli asset.
Fonte gid=0 esportata in CSV e righe selezionate conservate in JSON.
Smoke dedicato `.csgopen/logs/reference-smoke.log`: SMOKE_DONE FAILURES 0,
respawn 2998 ms. Controllati danni e moltiplicatori configurati, cadenza,
fullauto, caricatori e riserve reali (7+21 / 64+128) anche dopo respawn;
parametri preservati dopo cambio mappa. `git diff --check` superato.
Nessuna verifica automatica di colpi fisici/headshot: conteggi 2/4 torso e
1 testa sono previsioni dal codice danni, da confermare in gioco.
Dispersione/recoil, armatura, falloff e mobilità Source non riprodotti in
questa fase; limiti documentati nel README e gameplay.

## Arsenale esteso — 1 ottobre 2026

Build native client/dedicato superate. Primo test arsenale fallito su alcune
scelte perché rientro spettatore richiesto entro DEATHMILLIS; test corretto
con attesa di 1100 ms. Menu loadout esponeva anche un errore upstream di
alias p_label_align: aggiunto il default mancante al widget decortext.
Secondo test `.csgopen/logs/arsenal-smoke-retry.log`: FAILURES 0, respawn
2999 ms. Sei primarie effettivamente assegnate con caricatore/riserva e
pistola; canshoot primaria consentita per tutte, secondaria consentita solo
Rifle. Splash/residual primari disattivati. Non sono stati simulati input
fisici: uso del menu, zoom AWP e sensazione di tiro richiedono prova manuale.

Test finale `.csgopen/logs/arsenal-final-smoke.log`: SMOKE_DONE FAILURES 0,
respawn 2997 ms. Verificati anche danni, moltiplicatori testa, rays, cadenza,
fullauto, munizioni e collisione dei cinque nuovi slot dopo cambio mappa.
Nomi finali e sidearm fissa documentati; nessun commit o push automatico.

## Correzione salvataggio loadout — 1 ottobre 2026

Segnalazione utente: scelta AWP nel menu non visibile dopo suicidio.
Ispezione: validazione upstream dipendeva dal secondo slot nascosto e poteva
rifiutare la primaria con filtro casuale vuoto. Modificata validazione nel
preset, scelta primaria salvata immediatamente e callback UI literal.
`.csgopen/logs/loadout-menu-smoke.log`: SMOKE_DONE FAILURES 0, tutte le sei
primarie assegnate passando da gameui_player_loadout_set/validate/set, con
filtro vuoto. Rendering e click fisici del menu restano verifica manuale.

Regressione locale aggiuntiva `.csgopen/logs/loadout-suicide-manual.log`:
MENU_AWP_SELECTED 8 VALID 1; dopo suicidio e respawn STATE 0 WEAPON 8
CLIP 5 RESERVE 10. Sessione aperta senza bot con menu loadout.

## Effetti proiettile e assenza rimbalzi — 1 ottobre 2026

Build nativa riuscita, diff check superato. Test dedicato
`.csgopen/logs/bullet-smoke.log`: SMOKE_DONE FAILURES 0, respawn 3004 ms.
Verificati collide1=241 e FX muzzle/trail/power su tutte le sette armi,
anche scoped AWP, dopo respawn e cambio mappa. Ispezione dei flag collisione:
nessun BOUNCE/DRILL/STICK, impatto su geometria/player/shots.
Audio degli slot energetici rimappato al tiro primario SMG solo nel preset;
transit e loop energetici Zapper esclusi. Nessuna modifica agli asset.
Verifica visiva/sonora e traiettorie da input fisico ancora manuale.

Ripristinati in configurazione gli effetti convenzionali originali di
Shotgun/Minigun su richiesta utente; valori confrontati con weapons.h e
aspettative smoke aggiornate. Nessuna modifica a danno/cadenza/collisione.
Diff check superato; nuova verifica visiva da fare al successivo avvio.

## HE e cook — 1 ottobre 2026

Build native client/dedicato superate, strumentazione temporanea del motore
rimossa prima della build finale. `.csgopen/logs/he-fixture.log` verifica
armamento, blocco cambio/drop, consumo della singola granata e rilascio dopo
1500 ms con LIFE 1500. Overcook: LIFE 1, SPEED 0, CENTER_DISTANCE 0;
esplosione effettiva sul proprietario da 100 HP a -20 e morte.
La fixture invocava le funzioni gameplay, senza simulare input fisici.

Smoke su server dedicato `.csgopen/logs/he-smoke.log`:
SMOKE_DONE FAILURES 0, respawn 3000 ms. Verificati parametri HE, inventario
1+0, selezione diretta, rifornimento al respawn e persistenza cambio mappa.
`git diff --check` superato. Cook da mouse, rimbalzi, danno ad altri player
ed esplosione alla morte durante cook richiedono ancora verifica manuale.

HE potenziata su richiesta: danno base 120 → 180 e raggio 48 → 72 (+50%
entrambi), miccia invariata. Solo configurazione e documentazione.
`.csgopen/logs/he-tuning-smoke.log`: SMOKE_DONE FAILURES 0; valori
sincronizzati e persistenti al cambio mappa, diff check superato.
Bilanciamento e sensazione del nuovo raggio da verificare in gioco.

HE colpibile: collide1 784 → 920 aggiunge COLLIDE_PROJ e IMPACT_SHOTS.
Ispezione projs.cpp: registrazione in collideprojs; hiteffect sui proiettili
chiama projpush, che distrugge il bersaglio locale o notifica il proprietario
remoto. Usa il percorso di esplosione nativo, senza nuove modifiche C++.
`.csgopen/logs/he-shootable-smoke.log`: SMOKE_DONE FAILURES 0, collisione
sincronizzata verificata anche dopo cambio mappa. Diff check superato.
Colpo effettivo su HE in volo/a terra da verificare manualmente.

## Smoke fumogena — 1 ottobre 2026

Build native client/dedicato superate. Fixture temporanea projs.cpp rimossa
prima della build finale, nessun comando di test distribuito. La fixture
crea un proiettile Mine sintetico e usa update/destroy reali del motore:
`.csgopen/logs/smoke-grenade-fixture-retry.log` mostra BLOCKED 1, CLEAR 1,
OPACITY 1 e HP 100; successivamente COUNT 0, DURATION 18000.
Il primo tentativo usava un ID locale non registrato nel server (sync error
atteso dalla fixture); il retry evita la notifica sintetica. I tempi di
CubeScript sono wall-clock mentre le nubi usano lastmillis di simulazione;
la scadenza viene verificata nello stato del motore, non dal solo timestamp.
Nessun input fisico simulato e nessuna verifica multiplayer della nube qui.

Build finale `.csgopen/logs/smoke-grenade-final-build.log` superata.
Smoke dedicato `.csgopen/logs/smoke-grenade-smoke.log`:
SMOKE_DONE FAILURES 0, respawn 2999 ms. Verificati parametri sincronizzati,
Mine abilitata come smoke, clip 1/reserve 0 al respawn, niente damage/radial,
HE conservata e persistenza al cambio mappa. Diff check superato.
Rendering esterno/interno, cook da mouse, memoria di tiro dei bot e nube
su due client richiedono prova manuale. Late join non ricostruisce nubi
esistenti; nube sferica senza clipping ai muri, limiti nel README.

## Densità esterna smoke e bot — 1 ottobre 2026

Utente conferma resa interna adeguata, segnala esterno troppo trasparente.
Ispezione renderer: PART_SMOKE usa compositing additivo; passaggio a
PART_SMOKE_LERP (PT_LERP) per coprire le sagome. Tre strati da 16 particelle
più centro, vita 600 ms invece di 350, stessa emissione ogni 100 ms.
Raggio 56 → 68 (+21.4%); overlay interno, durata e miccia invariati.
Build `.csgopen/logs/smoke-density-build.log` superata. Test dedicato
`.csgopen/logs/smoke-density-smoke.log`: SMOKE_DONE FAILURES 0,
respawn 3000 ms; nuovo raggio persistente dopo cambio mappa.
Diff check superato. Opacità esterna e prestazioni richiedono prova manuale.
Sessione di prova con botbalance 4 (utente più tre bot), skill 20–25,
adattamento skill disabilitato solo per questa sessione.

## Sagome attraverso smoke/muri — 1 ottobre 2026

Screenshot utente: halo colorati visibili attraverso fumo e geometria.
Preset client playerhalos/playerhalodamage 0; guardia CSGOpen nel pass HALO
impedisce comunque la silhouette di altri player. Ispezione renderer:
renderplayer (modello e attachment) e rendercheck (effetti status) saltati
quando la linea camera-centro attraversa smoke densa, per entrambe le squadre.
Label/overlay e radar applicano smoke + raycubelos, senza bypass per compagni.
Controllo discreto sull’intero modello, possibili transizioni ai bordi.

Build `.csgopen/logs/smoke-visibility-build.log` superata. Test dedicato
`.csgopen/logs/smoke-visibility-smoke.log`: SMOKE_DONE FAILURES 0,
compresi no_player_halos/no_damage_halos dopo respawn e cambio mappa.
Diff check superato. I test automatici verificano impostazioni e ciclo di gioco;
la scomparsa visiva di modelli/indicatori richiede nuova prova manuale con bot.

## Etichette solo compagni — 1 ottobre 2026

Preset client entityitemui/entityprojui -1: niente etichette su pickup e loot.
Guardia player/playeroverlay richiede stessa squadra non neutrale, oltre
alla visibilità già verificata con smoke e raycubelos; nessuna etichetta nemico.
Build `.csgopen/logs/labels-build.log` superata; test dedicato
`.csgopen/logs/labels-smoke.log`: SMOKE_DONE FAILURES 0, compresi
no_pickup_labels/no_loot_labels dopo respawn e cambio mappa.
Diff check superato. Comportamento grafico delle etichette compagni da
verificare manualmente nella sessione con bot.

## Corroder smoke e mina circolare — 1 ottobre 2026

Smoke migrata a Corroder con inventario spawn condiviso umano/bot, modello,
animazioni, icona, suoni e fisica da Grenade; colori HE arancione/smoke grigio.
Mine torna una mina circolare separata; Rocket resta disabilitato e riservato.
H smoke, J mina, G HE. Nessun asset o protocollo modificato.

Fixture temporanea rimossa prima della build finale. Primo test positivo
usava un centro target coincidente; retry con target definito a due unità:
`.csgopen/logs/mine-fixture-retry.log` OWNER 0 ALLY 0 ENEMY 1 UNARMED 0
DISTANT 0 DEAD 0 WALL_FOUND 1 WALL 0, ARM 1500 RANGE 32 AGE 1600.
SMOKE_MODEL weapons/grenade/hwep THROWN 1; proiettile sintetico Corroder
attraverso update/destroy reali: COUNT 1 OPACITY 1 HP 100. Questo verifica
predicato di innesco e nube; non è una prova di lancio da input fisico né
un colpo contro una mina su due client.

Build `.csgopen/logs/mine-final-build.log` superata, nessun comando fixture
nel sorgente finale. Test dedicato `.csgopen/logs/mine-smoke.log`:
SMOKE_DONE FAILURES 0, mine e smoke 1+0 indipendenti dopo respawn;
verificati armamento, raggio, collisione, danno, colori, Rocket disabilitato,
e persistenza al cambio mappa. Diff check superato.
Placement, detonazione effettiva su nemico, shot-down, resa dei colori e
sincronizzazione visiva restano verifiche manuali nella sessione con bot.

## Lanciagranate HE — 1 ottobre 2026

Rocket ora è un lanciagranate disponibile allo spawn: un colpo caricato e sei
in riserva, ricarica singola da 1800 ms, velocità 650 contro 250 della HE a
mano. Stessa miccia di 3000 ms, danno, raggio e collisioni della HE, senza
cook o guida. K seleziona l'arma; tiro secondario escluso dal preset.

Build finale `.csgopen/logs/launcher-final-build.log` superata. Fixture nativa
con doshot/weapreload reali: primo tentativo interrotto da auto-danno di una
HE rimbalzata; retry con auto-danno disattivato solo nel test ha sparato sette
colpi, consumato le sei riserve e rifiutato tiro/ricarica finali. Log
`.csgopen/logs/launcher-fixture-retry.log`: SHOTS 7, RESERVE 0, CAN_FIRE 0;
modello weapons/grenade/proj, LIFE 3000, COLLIDE 920, velocità effettiva 357.5
(dopo movespeed 0.55). Fixture rimossa prima della build finale.

Test sul server dedicato `.csgopen/logs/launcher-smoke.log`:
SMOKE_DONE FAILURES 0, incluse regole HE e inventario 1+6, respawn e cambio
mappa. Diff check superato. Gittata e resa visiva da verificare manualmente;
nessuna simulazione di input fisico o prova visiva automatica effettuata.

### Cook, impatto e rinculo del lanciagranate

Cook LIFEN 8/3000 ms; stesso blocco cambio/drop/pickup della HE. A fine cook
shootv crea la granata al centro del giocatore con lifetime1 e velocità zero.
La morte mentre si cucina il Rocket usa quel proiettile e consuma la sua
munizione, senza consumare la HE separata. Kickpush ridotto da 300 a 5,
rinculo verticale 0.1–0.2 e orizzontale zero.

Contatto diretto aggiunge HIT_PROJ|HIT_FULL e registra il client colpito per
non danneggiarlo nuovamente con la stessa granata. Calcolo client/server:
25 HP nel preset con danno HE esplosivo invariato; auto-danno/friendly fire
seguono i moltiplicatori esistenti. Nessun nuovo messaggio di protocollo.

Fixture temporanea di calcdamage/shootv rimossa prima della build finale:
`.csgopen/logs/launcher-cook-fixture.log`, DIRECT25 BLAST180, lifetime
3000/1500/1 a cook0/0.5/1, velocità zero a cook completo. I tiri sintetici
condividono il giocatore (la spinta cambia la velocità ereditata fra i tiri);
il flag cooked non scala la velocità del lancio. Questa verifica non è un
contatto fisico su un bot né un test di impatto su due client.
Build finale `.csgopen/logs/launcher-cook-final-build.log` superata.
Test dedicato `.csgopen/logs/launcher-cook-smoke.log`: SMOKE_DONE FAILURES 0,
incluse impostazioni cook/rinculo, inventario, respawn e cambio mappa.
Diff check superato. Resta la prova manuale di contatto con un bot, cook da
input fisico e sensazione del rinculo.

## Loadout con SMG oppure cinque utility — 1 ottobre 2026

Una primaria (ora comprende Rocket), Deagle fissa e scelta esclusiva tra
Bizon/MP9 secondaria e cinque slot HE/smoke/Mine. Slot ordinati, duplicati e
vuoti conservati nel preset; validazione condivisa spawnstate e parser
originale invariato con csgopenweapons0. Clip utility cap5/store0, nessuna
ricarica fra lanci; pickup utility/armi nuove bloccati per evitare bypass.
Menu (,), salvataggio immediato e applicazione al respawn.

Build finale `.csgopen/logs/loadout-final-build.log` superata, fixture rimossa.
Test dedicato `.csgopen/logs/loadout-final-cases.log`: LOADOUT_DONE FAILURES 0.
Dieci combinazioni con inventario ricevuto dal server: mix2HE/2smoke/1mine,
cinque HE, launcher+SMG con utility richieste ma negate, AK+MP9, slot vuoti,
primaria/secondaria/utility non valide, doppia SMG identica, slot oltre il
limite, legacy M249, cinque smoke. Verificati Deagle, clip/riserve primarie,
callback del menu, esclusione reciproca, attesa del respawn e persistenza al
cambio mappa. Menu aperto tramite comando nativo, nessun errore di script;
controllo visivo non effettuato: il client non appare tra le app disponibili
al tool di computer use.

Fixture temporanea nativa in weapons.cpp con doshot reale (cook forzato a
1 ms, auto-danno disattivato solo nel test):
`.csgopen/logs/loadout-utility-fixture.log`, cinque lanci, clip4/3/2/1/0,
sesto tiro FIRED0, CAN_FIRE0/CAN_RELOAD0, reserve0. Pickup HE e nuova arma
negati. Il test verifica consumo senza reload, non input fisico o resa visiva.
Build finale ripristina danno e codice senza comandi fixture.

Test completi dedicati `.csgopen/logs/loadout-smoke.log` e
`.csgopen/logs/loadout-arsenal.log`: SMOKE_DONE FAILURES 0 in entrambi;
verificate tutte le primarie precedenti, permessi, respawn e cambio mappa.
Diff check superato. Original Red Eclipse verificato per ispezione delle
condizioni di preset; non rieseguito come sessione di gameplay.
Resta la prova manuale di disposizione del menu, click sui selettori e
contatori durante l'uso delle tre utility. Sessione con bot avviata per questo.

### Correzione larghezza menu loadout

Screenshot manuale dell'utente: pannello destro tagliato, slot5 e testi fuori
area. Il contenitore è fisso a0.5; cinque selettori0.12 più quattro gap0.01
richiedevano0.64. Nel preset selettori ridotti a0.08 (totale0.44), icone0.065;
pulsanti accessorio larghi0.2 ciascuno, titoli abbreviati e note su due righe
con wrap0.46. Dimensioni originali mantenute fuori dal preset. Nessuna modifica
alle callback o all'inventario; diff check superato. Prova visiva del menu
corretto richiesta nella nuova sessione, senza dichiararla automatizzata.

### Quattro slot granate

Menu limitato a quattro selettori; parser e spawnstate leggono sei posizioni
(primaria, secondaria, quattro utility). Capacità HE/smoke/Mine4; munizioni
Rocket sempre1+6. Profili da sette posizioni migrati conservando primaria,
secondaria e primi quattro slot. README aggiornati in inglese.
Build `.csgopen/logs/four-slots-build.log` e diff check superati.

Primo test matrice interrotto prima di DONE, con primary_clip AWP fallito;
non conteggiato come successo. Retry mirato `.csgopen/logs/four-slots-retry.log`:
inventari e limiti superati (mix2HE/1smoke/1mine, richiesta5HE limitata a4,
SMG esclude utility, richiesta5smoke limitata a4 anche dopo cambio mappa),
ma tre assert primary_selected falliti: LOADOUT_DONE FAILURES3. Il test non
è dichiarato interamente superato; causa dei cambi di arma selezionata non
stabilita. Questi assert non riguardano quantità o tipi assegnati.
Test generale `.csgopen/logs/four-slots-smoke.log` interrotto da SIGSEGV nel
caricamento della mappa, senza conclusione. Riavviato il server locale:
`.csgopen/logs/four-slots-smoke-retry.log` SMOKE_DONE FAILURES0, comprese
capacità HE/smoke/Mine4 dopo spawn, respawn e cambio mappa. Il crash iniziale
non è stato diagnosticato né dichiarato risolto dal cambio slot.
Anche primo avvio manuale SIGSEGV durante composizione texture mixer;
riavvio identico `.csgopen/logs/four-slots-manual-retry.log` riuscito:
FOUR_SLOTS_READY PRIMARY13 HE4, menu aperto e partita con bot attiva.
Rimane un crash intermittente di avvio da diagnosticare; non sono stati
modificati renderer o asset per attribuirgli una soluzione non verificata.

## Eclipse Recoil splash and icon — 1 October 2026

The supplied PNGs were copied unchanged into `data/csgopen/branding/`;
SHA-256 hashes match their source files. No upstream asset submodule was edited.
The TDM launcher applies branding before SDL initialization. The renderer fits
the complete splash, bypasses animated/map backgrounds, and hides upstream
loading logos and the central information panel while retaining loading status.

Executed checks:

- Native client/server build passed: `.csgopen/logs/branding-build.log`.
- Runtime loaded the splash as 3344 × 1882 and selected the supplied icon:
  `.csgopen/logs/branding-launch.log` and `branding-smoke.log`.
- Inspected native renderer screenshots in 16:9 and 4:3. The clean 4:3 capture
  `.csgopen/branding-check/splash-4x3-clean.png` shows the complete artwork with
  black margins. These captures use `forcenoview` after startup; they verify
  layout, rather than capturing every transient startup frame.
- The repository smoke test passed: `SMOKE_DONE FAILURES 0`, including respawn
  and map change, in `.csgopen/logs/branding-smoke.log`. The test used separate
  profiles and loopback port 28931; only the copied test's connection port changed.
- A fresh original profile launched with empty `splashtex` and
  `windowicontex = textures/icon`: `.csgopen/logs/branding-original.log`.
- `bash -n scripts/csgopen/dev.sh` and `git diff --check` passed.

The initial sandboxed launch failed because SDL could not access any display;
the graphical checks above ran successfully outside that restriction. Icon
selection is verified by runtime configuration and the existing
`SDL_SetWindowIcon` call; its appearance in the macOS Dock still needs a manual
visual check. No `.app` bundle or platform icon conversion was needed for this
native SDL launcher. Linux and Windows were not compiled in this check.

### Menu logo replacement

The supplied 2048 × 768 RGBA `logo.png` is copied unchanged into the branding
directory (matching SHA-256). Both `logotex` and `logocroptex` point to it.
Main-menu and welcome-screen images derive their height from the texture aspect
instead of stretching to the old 2:1 frame. The upstream logo is 1024 × 512,
so its original profile still receives the same 2:1 dimensions.

Inspected native screenshots `.csgopen/branding-check/logo-main.png` and
`logo-welcome.png`: both show the full Eclipse Recoil logo at the available
header width, without distortion. Runtime `.csgopen/logs/branding-logo.log`
confirms 2048 × 768 and both new paths. The test deliberately restored the old
logo variables before executing `client.cfg`; branding correctly reapplied.
No new binary build was needed: these changes only affect assets and CubeScript.
Existing smoke test on loopback port 28931 passed with
`SMOKE_DONE FAILURES 0`: `.csgopen/logs/branding-logo-smoke.log`, including
respawn and map change. `git diff --check` passed. Test sessions were closed.

## Client release workflow — 1 October 2026

Added `.github/workflows/release.yml` for pushes to `master` and manual runs.
It builds only the client target on five native hosts: macOS ARM64/Intel,
Linux x86_64/ARM64 and Windows UCRT64 x86_64. The publication job requires every
build to succeed, verifies all target checksum manifests, uploads into a draft
release, then publishes. Manual runs on other branches retain Actions artifacts
without publishing. Linux, Intel macOS and Windows builds have not been run
locally or on GitHub yet.

Executed locally on the ARM64 development Mac:

- `actionlint` 1.7.11 accepted the workflow without diagnostics. The downloaded
  tool's SHA-256 matched its official release checksum.
- Eight packaging regression tests passed: transitive Linux/Windows dependency
  closure, missing-library rejection, conflicting library names, inherited
  macOS rpaths, exact multipart reconstruction, download checksums and a
  single-file archive below the size limit.
- The native Makefile build check passed; no client/server recompilation was
  needed for the opt-in Windows Makefile changes. Log:
  `.csgopen/logs/release-build.log`.
- The full macOS ARM64 package was built from the local working tree, including
  all recorded assets, branding, runtime libraries, dependency notices, an ICNS
  icon and an ad-hoc signed `.app`. Log:
  `.csgopen/logs/release-package-final.log`.
- The initial archive exceeded GitHub's 2 GiB limit. Multipart packaging kept
  the full content in two parts (1500 MiB and approximately 700 MiB). The
  generated extraction helper verified all checksums and reconstructed/extracted
  the app successfully: `.csgopen/logs/release-extract-macos.log`.
- `codesign --verify --deep --strict` accepted the extracted app. Dependency
  inspection found SDL2's dynamically loaded SDL3 requirement, which is now
  included explicitly with a relocatable library name.
- The extracted app's launcher started successfully and completed the repository
  smoke test with **`SMOKE_DONE FAILURES 0`**, including respawn and map change:
  `.csgopen/logs/release-smoke-game-verified.log`. The test used an isolated
  profile copied from the previously verified smoke profile and a server bound
  to loopback port 28931. Only the copied fixture's connection port changed.
  Both test processes exited.
- Python syntax, shell launcher/extraction syntax and `git diff --check` passed.
  Windows ICO conversion was also exercised locally with Pillow.

Earlier package checks caught missing SDL3 before game initialization, and a
first network attempt reported a respawn timestamp 2 ms below the fixture's
tolerance before it ended without the final marker. A subsequent attempt was
interrupted during this conversation. Neither was counted as a passing smoke
test; the final completed run above supplies the passing evidence.

No GitHub run, release publication, commit or push was performed. The first CI
run must still establish native build/package compatibility on the other four
hosts. macOS downloads are ad-hoc signed, not Developer ID signed or notarized;
quarantine approval on a separately downloaded app remains a manual check.

### Windows CI fixture path correction — 1 October 2026

The supplied `windows-job-logs.txt` reports failure in
`test_linux_keeps_audio_closure_but_uses_host_glibc_and_gpu`. The job stops in
the Python regression suite before icon generation, client compilation or
Windows packaging. The simulated `ldd` output interpolated the Windows host's
temporary paths; the Linux dependency parser correctly expects absolute POSIX
paths, so neither fixture library was discovered.

The fixture now uses fixed Linux paths and maps them to real host-local files
at the filesystem boundary. Actual library copying and transitive dependency
checks remain exercised on every host. A regression case explicitly supplies
Windows-style fixture paths: the previous test reproduces the attached failure,
and the corrected suite passes all nine tests locally. `actionlint` and
`git diff --check` also pass. Production packaging, compiler flags and workflow
targets are unchanged.

The user reports successful builds on both macOS and both Linux targets.
Those outcomes are user-reported; only the attached Windows log was inspected
for this correction. Native Windows compilation and packaging still require
the next CI run, since the failed run did not reach those steps.

### Release checksum line endings — 1 October 2026

The supplied `win-job-logs.txt` shows nine passing tests and successful upload
of the Windows client package. `publish-job-logs.txt` shows all five packages
downloaded and the macOS/Linux checksums accepted. Publication then fails on
the Windows checksum manifest: Python's default text output on Windows adds
CRLF, and GNU `sha256sum` interprets the CR as part of each filename. The job
stops before creating or publishing the release.

Checksum manifests now use explicit UTF-8 bytes with LF on every host. Archive
parts and extraction scripts retain their content; their exact bytes are still
hashed. A regression simulates Windows text translation, fails before the fix,
and passes afterward. All ten packaging tests pass locally. A small multipart
Windows fixture generated under that simulation passes GNU coreutils 9.10
`sha256sum --check`. Converting its manifest to CRLF reproduces the missing-file
failure with the Mac's native `/sbin/sha256sum`; the newer local GNU version
accepts CRLF, unlike the Ubuntu runner in the supplied log.
`actionlint` and `git diff --check` also pass. No native rebuild was needed for
this Python-only correction. Full GitHub release publication remains pending
the next run with the corrected manifest generator.

### Compiled Quake 3 BSP conversion front end — 1 October 2026

The new Python front end was exercised against all six supplied Urban Terror
PK3 files: `ut4_thewall`, `ut4_quickfight`, `ut4_iran3`, `ut4_fastfight`,
`ut4_boxtrot_v1`, and `ut4_baeza`. It parsed their compiled IBSP 46 data
without relying on source brush files and found render geometry, solid
collision brushes, and player starts in every archive. Quickfight produced
7,916 source render vertices, 4,953 OBJ triangles, 389 solid brushes, and 32
recognized player starts.

The five synthetic regression tests pass. They cover compiled geometry and
collision data, red-team spawn translation, a PK3 containing only a compiled
BSP, rejection of an unsupported BSP version, and literal backslashes in
entity values. They also check two-sided collision generation and floor-backed
spawn placement. Python bytecode compilation and `git diff --check` also pass.

The collidable-mapmodel backend was then exercised end to end with Quickfight.
It extracted the two directly referenced image textures, generated the OBJ and
model configuration, transformed all 32 player starts, and saved a native MPZ
from an isolated editor profile. A TDM client loaded that MPZ and its staged
content package, joined Omega at an imported spawn with 100 health, rendered
the converted geometry and texture, saved a 1280x720 screenshot, emitted
`Q3PLAY_DONE ut4_quickfight`, and exited normally. One bot later fell to its
death in this initial implementation.

The collision backend was subsequently separated from the render model and
made two-sided. Spawn placement now ray-tests walkable compiled surfaces and
adds explicit player clearance. Quickfight generated 9,902 collision triangles
(both windings of 4,951 solid source triangles); all 32 starts found a supporting
floor with no fallback. A regenerated MPZ then completed a 35-second TDM run:
the human and bot moved and exchanged kills, the log contained no fall deaths,
and the client emitted `Q3PLAY_DONE ut4_quickfight` before exiting normally.
This removes the reproduced spawn/collision failure, though it is not a proof
of full traversal coverage for every map. A static support pass over all six
supplied archives found floors for every recognized start: The Wall 24/24,
Quickfight 32/32, Iran 3 41/41, Fastfight 55/55, Boxtrot 17/17, and Baeza
23/23. Missing optional `.txt` and `.wpt` files were logged but do not prevent
loading or play.

The first manual launch exposed a 90-degree world rotation: the engine OBJ
loader converts file coordinates with `(x, y, z) -> (z, -x, y)`. The exporter
now writes the exact inverse `(-y, z, x)`, so the resulting engine coordinates
match the BSP coordinates and the BSP Z axis remains vertical. The synthetic
OBJ regression checks this conversion explicitly.

After that correction, the complete wrapper also produced native MPZ packages
for The Wall, Iran 3, Fastfight, Boxtrot v1, and Baeza. Every editor run emitted
its `Q3IMPORT_DONE` marker and every expected MPZ exists. The conversions wrote
all recognized supported starts (24, 41, 55, 17, and 23 respectively), with no
unsupported-start fallback. These five packages have not yet received the same
interactive traversal check as Quickfight.

The `convert-pk3.sh` wrapper was also run from the original PK3 through MPZ
generation and package assembly. It found the completion marker and produced a
self-contained staged package under `.csgopen/map-convert/`. Conversion to
editable Cube 2 octree geometry, shader-script translation, indirect shader
texture discovery and systematic collision traversal remain future work.

### Decompiled Valve VMF conversion — 1 October 2026

The VMF front end was exercised with `de_safehouse_d.vmf` from ReagentX's
decompiled CS:GO maps repository. The source contains brush/entity data but no
CS:GO material or model assets, so the prototype intentionally uses a neutral
skin. It reconstructed 1,990 solid brushes, 9,051 render triangles and 11,555
collision triangles. All 25 recognized CT/T player starts found a supporting
brush and were written as native Alpha/Omega starts.

An initial gameplay load crashed in `BIH::build`. The macOS crash report showed
recursive stack exhaustion, and inspection found 19 one-triangle OBJ groups
created by material changes. The OBJ exporter now writes BIH-safe groups of at
most 100 triangles and merges a final one-triangle remainder into the previous
group. The same rule applies to render and collision meshes. Nine synthetic
converter tests pass, including the regression for material changes and a
one-triangle chunk remainder.

The corrected client loaded the generated MPZ, started a TDM match, allowed a
bot kill, saved a 1280x720 screenshot, emitted `VMFPLAY_DONE de_safehouse`, and
exited with status 0. The complete `convert-vmf.sh` wrapper then regenerated a
self-contained package at
`.csgopen/map-convert/de_safehouse.FpYLNV/data`; the editor emitted
`VMFIMPORT_DONE de_safehouse` and the expected MPZ exists. This verifies loading,
collision initialization and imported starts, but not complete traversal of the
house. Props, displacements, Source materials/textures, lighting and non-spawn
gameplay entities remain unsupported. The upstream repository's licensing and
the original game's redistribution terms must be reviewed before publishing any
derived package; no converted Safehouse content is tracked in this repository.

### Direct Source 1 BSP conversion — 2 October 2026

The reusable `convert-source-bsp.sh` workflow was executed against the Steam
CS:GO Legacy `de_dust2.bsp` and its local `pak01_dir.vpk`. The parser identified
VBSP version 21, 375 entities, 9,715 world-model faces, 8,324 displacement
records and 30 starts (15 Counter-Terrorist and 15 Terrorist). Every start found
a supporting compiled surface. LOD 2 plus 3D-skybox exclusion produced 16,164
render triangles and 48,492 authored OBJ render vertices. The collision copy
contains both windings as 32,328 triangles.

All 81 referenced playable world materials resolved through the BSP/VPK content
store; none were missing and none used an unsupported VTF compression format.
The wrapper emitted `SOURCEIMPORT_DONE de_dust2`, produced the expected MPZ and
assembled a local staged package under `.csgopen/map-convert/`. The client then
loaded that MPZ in 2.7 seconds, started a TDM match, emitted
`SOURCEPLAY_DONE de_dust2`, saved a 1280x720 screenshot and exited with status
0. The final automated run did not crash in render-VBO or BIH construction.

The screenshot also establishes the current fidelity limit: the compiled world
shell and base textures render, but the scene is visibly incomplete and unlike
the finished Source presentation. Source props, brush submodels, lightmaps,
shader blending and other runtime systems are not present. This run verifies
direct BSP/VPK extraction, MPZ generation, loading and start serialization; it
does not claim a faithful or fully traversable Dust II port. No Valve-derived
map or texture asset is tracked in Git. A parser-only reuse smoke test also read
`de_shortdust.bsp` as VBSP 21 and reported 443 entities, 31 starts, 11,425 world
faces and 205 materials; full staging correctly remains subject to the model
index limit.

A follow-up inspection identified the large green/black plane in that screenshot
as the default solid lower half created by Eclipse's `newmap`, not Source
geometry. The engine now exposes `newmapfloor`, which defaults to the original
behaviour; the Source build job sets it to zero before creating its empty map.
The imported collision shell is divided into 51 double-sided BIH carriers on a
1,024-Source-unit XY grid.

The remaining fall-through was traced to editor selection state rather than the
BIH data. Each scripted `newent` remained selected, so every following `entpos`
moved all prior render, collision and spawn entities. All 82 entities therefore
ended at the final Terrorist start. The generator now executes `entcancel` after
positioning each entity. A fresh package placed the render model and all 51
collision carriers at `(1240, 672.5, 2160.155)` while retaining all 30 distinct
starts.

Two TDM launches validated the result without the default octree floor. An Alpha
start on the lower side remained at Z `2148.498` for three samples with physics
state `floor`; an Omega start on a raised surface remained at Z `2203.247` for
three samples with the same state. Both reported non-axis-aligned normals from
the imported Source triangles, emitted `SOURCEPLAY_COLLISION_FIXED` or
`SOURCEPLAY_RAISED_FIXED`, and exited normally. This verifies collision on both
lower and raised compiled surfaces; exhaustive traversal and unsupported Source
runtime objects remain outside this smoke test.

The collision backend was then replaced with the compiled BSP brush topology.
Dust II exposes 2,357 world-tree brushes; 1,990 carry solid or player-clip
contents, including 1,243 authored player-clip volumes that the earlier
visible-surface collision could not see. Together with displacement terrain,
the new backend generated 31,383 source collision triangles, written with both
windings as 62,766 triangles in 72 local BIH carriers. The editor again emitted
`SOURCEIMPORT_DONE de_dust2`; 30/30 starts found support without a synthetic
floor.

The version-11 static-prop lump contains 3,158 instances and 1,258 model names.
After excluding the remote 3D skybox, the reusable Blender/Plumber batch decoded
1,022/1,022 model assets and wrote 2,253/2,253 playable instances. A global
decimation ratio of `0.167383` reduced 4,480,736 instanced source triangles to
750,994 triangles across 68 ushort-safe tile models. All 189 referenced prop
materials and all 81 world materials resolved; there were no missing models,
textures or unsupported VTF formats.

The combined package registers 141 mapmodels: one visible world shell, 72
collision carriers and 68 static-prop tiles. It compiled to an MPZ, loaded into
a bot-free TDM client, captured a 1280x720 spawn screenshot, emitted
`SOURCEPLAY_STRUCTURAL_DONE de_dust2`, and exited normally. The screenshot shows
the previously absent roof, beams, crates, trim and other assembled architecture
aligned with the textured world. This is a structural and spawn smoke test;
manual route traversal is still required, and static props without authored
brush/player-clip support do not yet receive their PHY collision hulls.

Manual traversal of that first structural package exposed occasional invisible
steps and two delayed exits. Both macOS crash reports identify stack exhaustion
in `BIH::build`; the prop OBJ stream still allowed a material used by exactly
one triangle to form a one-triangle mesh. The shared safe-chunk helper now
duplicates an isolated render triangle, and every generated render group is
limited to 100 triangles. A full scan of the lighter package found 4,095 OBJ
groups and zero singleton groups.

The default prop budget is now 300,000 triangles. Dust II produced 306,706
triangles in 60 prop tiles, down from 750,994 triangles in 68 tiles. Collision
also omits the undeformed source plane replaced by each displacement, reducing
the double-sided result from 62,766 to 59,620 triangles and removing a likely
source of invisible flat ledges over deformed terrain. The new package compiled
successfully, loaded from a second spawn, remained active for the one-minute
automated run, emitted `SOURCEPLAY_LIGHT_STABLE de_dust2`, captured a 1280x720
screenshot and exited normally. No new macOS crash report was created. Longer
manual traversal remains the decisive stability and collision test.

A subsequent manual pass found a small number of transparent but non-passable
wall patches. The generator now adds a neutral DXT1 backing shell for solid
brush faces, inset by two Source units so ordinary textured surfaces remain in
front. That first pass still left a wall transparent where bullet decals proved
collision existed: the barrier used `CONTENTS_PLAYERCLIP`, not
`CONTENTS_SOLID`. The fallback therefore includes near-vertical player-clip
faces (`abs(normal.z) < 0.25`) while excluding horizontal caps, floors, ramps
and displacement source planes. Dust II adds 10,576 backing triangles (31,728
vertices), remains below the ushort model limit and introduces no singleton OBJ
groups. The regenerated package compiled successfully; the preceding solid-only
version also completed the one-minute test, emitted
`SOURCEPLAY_LIGHT_STABLE de_dust2`, and created no new crash report.

Further manual traversal showed that the aggressive whole-model collapse pass
could erase disconnected panels inside architectural static props. The result
looked like large triangular holes even though bullet decals and collision
proved that the wall still existed. A planar-only prototype preserved those
panels but expanded the props to 3,365,264 triangles; protecting every loose
island still required 1,751,470. The final reducer counts connected islands by
surface area and reserves eight triangles only for architectural islands of at
least 512 square Source units. Tiny bars, bolts, trim and foliage remain under
the ordinary global ratio. Dust II now contains 352,702 prop triangles in 62
tile models, only about 15 percent more than the 306,706-triangle light build.
A scan of 4,247 OBJ groups found zero singleton or empty groups. Together with
16,164 world triangles, 59,364 double-sided collision triangles, and 10,576
neutral-backing triangles, the package compiled and loaded in 4.9 seconds. It
completed a bot-free one-minute run, emitted
`SOURCEPLAY_PANEL_SAFE_STABLE de_dust2`, exited normally, and created no new
macOS crash report. Manual inspection at the formerly damaged walls remains
the final visual acceptance test.

That manual inspection also rejected the neutral-backing workaround. Although
it covered isolated transparent collision walls, large `playerclip` volumes
painted whole facades and parts of the sky dark gray. Neutral backing is now
disabled by default and available only through the explicit experimental
`--neutral-backing` switch. A clean rebuild from an empty profile contains 135
mapmodel definitions (one world shell, 72 collision carriers, and 62 prop
tiles), no fallback model reference, and retains the panel-aware prop reducer.

Safehouse exposed the older version-10 static-prop layout: its 318 records are
76 bytes each and predate the version-11 per-instance scale field. The parser
now accepts versions 10 and 11, assigning Source's default scale of `1.0` to
version-10 props; an isolated fixture covers this layout and all 11 Source BSP
tests pass. A direct conversion of the local CS:GO Legacy `de_safehouse.bsp`
resolved all 93 world materials, supported all 25 player starts, decoded all 91
prop models and wrote all 318 prop instances into 45 tile models. The package
compiled to an MPZ, loaded in TDM, captured a 1280x720 screenshot, emitted
`SOURCEPLAY_DONE de_safehouse`, and exited normally. The screenshot confirms
the house, terrain, walls, trees and fences render, but also shows the expected
lighting and foliage differences from the Source runtime; complete route and
collision traversal remains manual work.

Interactive checks of Dust II, Safehouse and Lake showed the imported layout
reflected left-to-right. Source BSP conversion now reflects X consistently in
world render geometry, brush/displacement collision, static props and player
starts; spawn yaw is reflected with the same transform. Lake also exposed
passable rocks and bot sight through them because every prop tile explicitly
used `mdlcollide 0`. The prop exporter now emits separate invisible triangle
carriers for Source props whose solid type is nonzero, leaving decorative
foliage passable. The rebuilt Lake package contains 257 solid props in 35
collision tile models and 457,752 double-sided collision triangles. It loaded,
captured a 1280x720 screenshot, emitted `SOURCEPLAY_COLLISION_DONE de_lake`,
and exited normally. Twenty-one converter tests and `git diff --check` pass;
manual traversal against representative rocks and a bot line-of-sight check
remain required because the carriers approximate, rather than decode, PHY
hulls.

Dust II and Safehouse were then rebuilt through the same corrected path.
Safehouse retained 25/25 supported starts and 93/93 resolved world materials;
226 solid props produced 41 collision tiles. Dust II retained 30/30 starts and
81/81 resolved world materials; 1,010 solid props produced 36 collision tiles.
Both packages loaded in isolated TDM clients, emitted their respective
`SOURCEPLAY_COLLISION_DONE` markers and exited normally.

Lake's missing water was traced to a format mismatch rather than a missing
bitmap: its generated CFG already declared Red Eclipse's native water texture,
but the converter exported Source `SURF_WARP` faces as an ordinary OBJ and did
not create any octree material volume. The BSP contains eight
`CONTENTS_WATER` world brushes. Seven fall inside the playable envelope; the
eighth is the remote 3D-skybox copy. The converter now emits seven grid-aligned
`editmatbox water` operations, omits all Source warp surfaces from the render
mesh, and reports water counts in its manifest. Lake rebuilt with 7/7 playable
water volumes, 69 resolved world materials with none missing, and all 30
player starts supported. A bot-free TDM client loaded the rebuilt MPZ, emitted
`WATER_OMEGA_DONE de_lake`, and captured the native reflective water surface
from the Omega side. Sixteen converter tests, the native client/server build,
and `git diff --check` pass.

The final corrected Dust II, Safehouse, and Lake packages were subsequently
installed as one self-contained, Git-ignored ZIP per map in the
main-repository-owned `data/csgopen` package root. Each archive carries its
MPZ/CFG/preview plus generated models, collision carriers, and textures under
their normal virtual paths. The TDM and dedicated-server launch paths add this
package root and the engine mounts its ZIP files automatically; the
original-game path remains isolated from it. After archive extraction checks
and a load test from the persistent location, the expanded copies and the
disposable `.csgopen` conversion workspace and profiles were removed. A later
launcher invocation recreates only the runtime profile and log directories it
needs.

Bank was imported through the same self-contained path. Its Source BSP yielded
38/38 supported starts, 148/148 resolved world materials, 9,997 rendered world
triangles and no water brushes. Blender/Plumber decoded all 192 referenced prop
models and wrote 716 playable instances; the simplified result contains
303,003 prop triangles, while 459 solid props generated 26 collision tile
models. A bot-free TDM client entered the match at a textured parking-lot
spawn, then an isolated profile loaded `maps/de_bank` directly from the
installed `data/csgopen/de_bank.zip` with no expanded map or imported-asset
directory present and emitted `BANK_ZIP_DONE`.

### macOS desktop fullscreen resize loop — 1 October 2026

The downloaded ARM64 release (build 3, commit
`296c16541d510c09750b9f106ab6a6908077d32b`) logged `Fatal signal 11` immediately
after loading Echo. The user observed repeated transitions between fullscreen
and windowed mode. A separate LLDB run reproduced those transitions, with
repeated display reports of 1728 × 1117 versus a 1728 × 1084 fullscreen client
area, but exited normally without reproducing the segmentation fault. The
engine's signal handler had prevented an ordinary macOS crash report from
being available for the original failure; no faulting stack was captured.

`setupdisplay` previously forced every fullscreen client area to match the
display mode, triggering another exit/re-entry whenever resize events reported
the smaller client area. It now enforces that match only for exclusive
fullscreen, accepting window-manager dimensions for desktop fullscreen. The
SDL desktop flag includes the fullscreen bit, so the masked flags must be
compared explicitly; checking either bit alone would retain the loop.

Executed on the development Mac:

- Native client build passed; log `.csgopen/logs/fullscreen-fix-build.log`.
- A diagnostic copy of the corrected client was linked to all runtime libraries
  from the downloaded release via a local symlink. The downloaded app and the
  user's profile were preserved. Using the downloaded assets, it loaded Echo,
  switched fullscreen → windowed → fullscreen and reached
  `BUNDLED_FULLSCREEN_CHECK_DONE`, exiting with status 0. The repeated reset
  loop disappeared; log `.csgopen/logs/release-crash-bundled-fixed-game.log`.
- The corrected client with the downloaded libraries completed the explicit
  network smoke test in fullscreen: **`SMOKE_DONE FAILURES 0`**, including
  respawn and map change. Log `.csgopen/logs/fullscreen-smoke-client.log`.
  Test profiles were isolated in `.csgopen/`; the test server used loopback port
  28941 with public registration, LAN discovery and HTTP disabled.
- `git diff --check` passed. Gameplay rules and assets are unchanged.

This establishes the resize-loop fix; it does not prove the original signal
11 arose from that loop. A fresh packaged GitHub release, other platforms,
exclusive fullscreen and longer manual play remain untested for this change.
The existing downloaded release can temporarily be launched with `-df0` to
use a window until a release containing the engine fix is available.

## Dedicated-server rotation and complete map packages (2026-10-02)

The development server now loads `config/csgopen/server-maps.cfg` before its
first map selection. With no map argument, `sv_defaultmap` is empty and
`sv_mainmaps` supplies the initial and subsequent random rotation. The CFG
sets 10-minute TDM matches, no score limit/overtime, 10 seconds of results,
20 seconds of voting, and a 50% early-pass threshold. The native HTTP server
serves the selected map's complete ZIP to the connected client's IP/port pair.
The client validates size, CRC32, and archive namespace before mounting and
loading. Original gameplay defaults leave package distribution/downloads off.

Executed checks on macOS arm64:

- Native client/server build passed with the upstream Makefile. Log:
  `.csgopen/logs/server-maps-build.log`. No new runtime dependency was added.
- `python3 scripts/csgopen/test_server_maps.py -v`: **5 tests passed**. An
  isolated loopback server streamed an 8 MiB binary fixture byte for byte;
  wrong versions, traversal, missing names, and maps outside the allowlist
  returned 404. Additional fixture starts rejected ZIPs attempting to override
  configuration, another map, or an imported path outside their namespace.
  Log: `.csgopen/logs/server-maps-tests.log`.
- A client installation without custom map ZIPs downloaded **63,810,457 bytes**
  for `de_bank`, mounted the validated package, and loaded its imported models.
  The cached file matched `data/csgopen/de_bank.zip` byte for byte, with CRC32
  **90597195**. The final native build produced
  `PACKAGE_FINAL_READY MAP maps/de_bank`, then the full existing gameplay smoke
  test passed: **`SMOKE_DONE FAILURES 0`**, including respawn and switching to
  Dutility. Log: `.csgopen/logs/map-download-final-client.log`.
- A second connection using the downloaded cache produced `Using cached map
  package: de_bank`, with no HTTP download and `PACKAGE_SPAWN_STATE 0` (alive).
  Log: `.csgopen/logs/map-cache-client.log`.
- Starting `scripts/csgopen/dev.sh server` without a map argument selected
  `de_dust2` from the CFG, with a valid server-side MPZ CRC. The dedicated
  server mounted the ZIP itself rather than asking the first client to upload
  the map. That session also passed the original gameplay smoke test.
  Log: `.csgopen/logs/server-maps-smoke-client.log`.
- Shell syntax and `git diff --check` passed. All test servers used loopback,
  with public registration and LAN discovery disabled; profiles, caches,
  fixtures, and logs remained under `.csgopen/`.

Code inspection confirms voting/fallback behavior in the existing server
state machine and package interruption/failure handling. A shortened native
rotation session ended before an automatic fallback transition was observed.
Automatic fallback over a full match, voting with multiple human clients,
mid-download disconnection, replacing a package version while reusing loaded
assets, cross-platform runtime behavior, and visual progress-bar QA remain
manual checks. This initial transport is HTTP, not HTTPS, and the launcher
still supports local loopback testing rather than public/LAN deployment.


## Release build label (2026-10-02)

The shared menu/loading-screen version formatter now reports `Build N` from
`versionbuild`. The window title and native client/server version banner use
that same build number. Unnumbered local binaries report `Development build`;
`versionstring` retains the upstream engine version for diagnostics. Code
inspection confirms all release platforms already compile with
`PLATFORM_BUILD="$GITHUB_RUN_NUMBER"`, matching the release tag and manifest.

Executed on macOS arm64:

- Native client/server builds passed for build 4 and for the restored default
  local build. Logs: `.csgopen/logs/build-version-4-build.log` and
  `.csgopen/logs/build-version-final-local-build.log`.
- The running build-4 client evaluated the shared UI formatter and produced
  `VERSION_CHECK NUMBER 4 LABEL Build 4 ENGINE 2.0.9` and
  `VERSION_CHECK_PASS`. Both client and dedicated-server version banners
  reported `Eclipse Recoil Build 4`. Logs:
  `.csgopen/logs/build-version-4-client.log` and
  `.csgopen/logs/build-version-4-server.log`.
- The full gameplay smoke test on the loopback dedicated server passed:
  **`SMOKE_DONE FAILURES 0`**, including respawn and the change to Dutility.
  Log: `.csgopen/logs/build-version-4-client.log`.
- After restoring the local build, the running client produced
  `VERSION_CHECK NUMBER 0 LABEL Development build ENGINE 2.0.9` and
  `VERSION_CHECK_PASS`. Log: `.csgopen/logs/build-version-local-client.log`.

These checks evaluate the actual UI text and engine version banner; visual
layout inspection and other platform runs remain pending. Test processes were
stopped, and no release was published.

## Automatic release download installers (2026-10-02)

The release publication job now generates two small, release-pinned assets:
`eclipse-recoil-install.sh` for macOS/Linux and `eclipse-recoil-install.ps1`
for Windows x86_64. Release notes lead with copyable commands for that exact
build. README/release-guide commands use GitHub's latest-asset URL; the
installer itself retains its original tag throughout the download. These
assets become available when the next release containing this change is
published; existing published releases were not modified.

Both installers select the client, download its checksum manifest and files,
verify SHA-256, join split parts when needed and extract into a new game
folder. They reject existing installations, invalid filenames and missing or
unordered parts. Verified downloads survive failure for retries; partial
files and failed extraction directories are removed. Successful installation
removes download files. The Bash script supports macOS's bundled Bash 3.2;
Apple Silicon detection also handles an Intel/Rosetta terminal. Windows uses
native `tar.exe` to extract ZIPs, including archives exceeding 2 GiB, and
supports Windows PowerShell 5.1. Neither installer executes downloaded legacy
extraction helpers or starts the game.

Executed checks on macOS arm64:

- `python3 scripts/release/test_installers.py -v`: **12 passed, 2 skipped**.
  Small local HTTP fixtures exercised the real Bash installer with simulated
  OS/CPU detection for macOS ARM64/Intel and Linux ARM64/x86_64, including
  single and split archives, a destination containing spaces, checksum
  failure/retry with cache reuse, malformed paths, a missing part, invalid
  archives, unsupported CPUs and preserving existing installations. macOS
  extraction used native `ditto`; Linux fixtures used `tar`. Metadata checks
  verified pinned tags, build/commit consistency and release instructions.
  Log: `.csgopen/logs/release-installer-tests.log`.
- The two native Windows installer tests were skipped because PowerShell and
  Windows `tar.exe` are unavailable on this Mac. Windows integration tests,
  including the same failure/retry cases, now run in the Windows release job.
- `python3 scripts/release/test_package.py`: **10 passed**. Log:
  `.csgopen/logs/release-installer-package-tests.log`.
- Workflow YAML parsed successfully with Ruby YAML. All four workflow shell
  blocks and the generated Bash installer passed `bash -n`; Python source
  compilation and `git diff --check` passed.

Fixtures and generated preview notes remain under `.csgopen/`; HTTP servers
were loopback-only and were stopped after testing. Actual public asset
availability, native Linux/Windows runs, and multi-gigabyte end-to-end
installation remain CI/release checks. No release was published locally.

## Windows installer CI failure correction (2026-10-02)

The supplied Windows job log failed during installer tests, before the C++
client build. Three extraction tests selected MSYS2's `tar.exe` from `PATH`;
GNU tar interpreted `D:\...` as a remote archive and reported
`Cannot connect to D: resolve failed`. The metadata test also raised a
`UnicodeDecodeError` while reading generated UTF-8 through the Windows CP1252
default. The existing 10 packaging tests had passed in that job.

The PowerShell installer now invokes Windows' native `tar.exe` by its absolute
system path, using `Sysnative` from a 32-bit process on 64-bit Windows and
`System32` otherwise. Template reads, generated release-note writes and test
reads explicitly use UTF-8. Added regression cases simulate CP1252 defaults
and, on Windows, put an invalid `tar.exe` first on `PATH` to ensure it cannot
replace the native extractor.

Executed on macOS arm64:

- `python3 scripts/release/test_installers.py -v`: **13 passed, 3 skipped**,
  including the new CP1252 regression. The native Windows archive tests and
  PATH-shadow regression remain for the Windows CI runner. Log:
  `.csgopen/logs/windows-installer-fix-tests.log`.
- Python source compilation, generated Bash syntax and `git diff --check`
  passed. The test HTTP servers were loopback-only and stopped on completion.

A new Windows CI run is required to confirm native extraction and reach the
client compiler. No remote workflow was triggered and no release was published.

## Build 5 macOS startup crash investigation (2026-10-02)

The downloaded arm64 build 5 (`4de9fb35`) was reported to crash after loading
on every launch, without input. Its log ends while loading Echo. Repeated
launches of the original package, including LaunchServices and isolated
profiles, did not reproduce the user's failure on this machine. An
AddressSanitizer build using the downloaded package's assets exposed two
invalid memory accesses in the same startup path:

- `getlocalparam` retained pointers to temporary shader parameter names such
  as UI-generated `objcolor0`. ASan reported a stack-buffer-overflow in the
  subsequent hash-table string comparison during the loading screen. The
  registry now interns names through the existing persistent shader-name
  pool. Log: `.csgopen/logs/startup-asan-before-fix.log`.
- Model material commands registered `siif` despite accepting a string,
  three integers and a float. After fixing the first fault, LLDB stopped
  in OBJ `setmaterial` for Echo's `bark01` mesh with the final argument equal
  to address `0x40`. The registration now uses `siiif`, matching the function
  and allowing omitted arguments to receive the command interpreter's
  defaults. Log: `.csgopen/logs/startup-asan-fixed-lldb.log`.

Executed on macOS arm64:

- Native client/server builds and the separate ASan client build passed.
  Logs: `.csgopen/logs/startup-material-fix-build.log` and
  `.csgopen/logs/startup-asan-material-fix-build.log`.
- A fresh-profile ASan startup reached Echo and `ASAN_FIXED_READY`, then
  exited cleanly without a sanitizer report or fatal signal. Logs:
  `.csgopen/logs/startup-asan-both-fixes-{game,runtime}.log`.
- The complete TDM smoke test with ASan passed **`SMOKE_DONE FAILURES 0`**,
  including respawn and Echo-to-Dutility map loading. Logs:
  `.csgopen/logs/startup-asan-smoke-tdm-{game,runtime}.log`. Preliminary
  smoke runs lacked the launcher's client preferences or local TDM setup
  and failed preset assertions; the final run includes both configuration
  files and passes all assertions.
- A local preview app uses the corrected native binary with build 5 assets
  and runtime libraries, relocated library references and renewed ad-hoc
  signatures. Signature verification passed. Three fresh-profile
  LaunchServices starts reached `FIXED_APP_READY` and exited cleanly. Log:
  `.csgopen/logs/startup-fixed-app-first-boot.log`.
- The preview app's complete TDM smoke also passed
  **`SMOKE_DONE FAILURES 0`** with the bundled runtime libraries. Logs:
  `.csgopen/release-5-fixed/smoke-profile/game.log` and
  `.csgopen/logs/startup-fixed-app-smoke-runtime.log`.
- `git diff --check` passed. Test servers were loopback-only and stopped.

The preview is `.csgopen/release-5-fixed/Eclipse Recoil.app` and identifies
itself as a Development build. The downloaded app and the user's profile
were not modified. These are confirmed startup memory defects; attributing
the original release's specific crash to either one remains an inference
until the user tests the corrected app. The release compiler and other
platforms require CI verification. No commit, push or release was published.


## Agency Source BSP conversion (2026-10-04)

The local CS:GO Legacy `cs_agency.bsp` was converted with the direct Source
backend and installed as the Git-ignored `data/csgopen/cs_agency.zip`.
The initial prop pass exposed a material lookup gap: the decoder saw BSP-local
MDL files but not their VMT definitions, collapsing custom materials to an
unknown placeholder. Staging BSP-local VMTs alongside the requested model
files preserves those material paths. The final prop pass resolves 131/131
materials, compared with 35 resolved materials and an unknown placeholder
before the correction. Texture extraction remains in the existing BSP/VPK
content store.

Executed on macOS arm64:

- The converter decoded all 178 playable prop models and wrote all 1,185
  playable instances out of 1,197 source props; the playable envelope excludes
  the remaining 12. The reduced props contain 305,759 triangles in 33 render
  tiles; 810 solid props produce 25 collision tiles and 393,864 double-sided
  collision triangles.
- World geometry contains 15,392 render triangles, 473/473 resolved materials,
  47 collision tiles, no water volumes, and 32/32 supported starts.
  The editor emitted `SOURCEIMPORT_DONE cs_agency` and saved the native MPZ.
  Logs: `.csgopen/logs/convert-cs_agency.log`,
  `.csgopen/logs/sourceprops-cs_agency.log`, and
  `.csgopen/logs/sourceimport-cs_agency.log`.
- ZIP namespace and extraction checks passed: 819 files, 62,007,391 bytes.
  An isolated client loaded only the installed ZIP package root, entered TDM,
  spawned on Alpha and Omega, and reported floor physics for both teams.
  It emitted **`AGENCY_ZIP_DONE FAILURES 0`** and exited normally.
  Log: `.csgopen/logs/cs-agency-verify.log`; screenshots:
  `.csgopen/cs-agency-verify/screenshots/cs_agency-alpha.png` and
  `.csgopen/cs-agency-verify/screenshots/cs_agency-omega.png`.
- The full existing network smoke test passed **`SMOKE_DONE FAILURES 0`**
  against the Agency package, including actual inventory/rules, a 2,997 ms
  respawn interval and the subsequent switch to Dutility. The server bound
  to loopback port 28971 with public registration, LAN discovery and HTTP
  disabled; both test processes stopped on completion. Logs:
  `.csgopen/logs/cs-agency-network-{server,client}.log`.
- All 16 Source BSP unit tests and `git diff --check` passed.

Visual inspection confirms textured rooftop and office spawn areas. Lighting,
transparency and some coplanar panels differ from Source, and the simplified
prop collision remains approximate. Full route traversal, bot navigation,
dynamic props and non-TDM entities remain manual checks or converter limits.
The dedicated-server rotation was not changed; Agency can be selected
explicitly with `scripts/csgopen/dev.sh server cs_agency`.

## Canals Source BSP conversion (2026-10-05)

The local CS:GO Legacy `de_canals.bsp` was converted and installed as the
Git-ignored `data/csgopen/de_canals.zip`, using scale 0.25, displacement LOD 2,
and a 300,000-triangle prop target. Three converter corrections were needed:

- The world shell exceeded one model's 65,535-index limit even at maximum
  displacement reduction. BIH-safe material groups are now packed into
  separate render models, accounting for singleton duplication and sharing
  textures. Canals emits two world models with 65,424 and 20,403 vertices.
- Three materials used unquoted VMT base-texture paths. The resolver now
  accepts both quoted and unquoted paths. The existing prop carriers were
  retained and their four affected mesh skins rebound after re-extracting
  the two spotlight textures; all world and prop materials now resolve.
- Initial visual verification found Omega below the visible pavement despite
  reporting floor physics. Collision reconstruction excluded every brush face
  on any displacement plane, including distant coplanar floors. It now
  excludes only matching displacement footprints. All 16 Omega starts then
  resolve to the authored pavement at Source Z 96, rather than the lower
  canal geometry. The native MPZ and ZIP were regenerated and verified again.

Executed on macOS arm64:

- All 431 playable prop models decoded without failure; 2,385/2,390 source
  instances were retained, with five outside the playable envelope. Props
  contain 325,416 triangles in 53 render tiles. The 1,990 solid instances
  produce 51 collision tiles with 586,522 double-sided triangles. Prop
  materials resolve 209/209.
- World geometry contains 28,609 emitted render triangles, 577/577 resolved
  materials, 69 collision tiles with 53,964 double-sided triangles, 35 native
  water selections, and 32/32 supported starts. The editor emitted
  `SOURCEIMPORT_DONE de_canals` and saved MPZ CRC `0x79ea8c61`.
  Stage: `.csgopen/map-convert/de_canals-source.8rRDpF/`; logs:
  `.csgopen/logs/convert-de_canals.log`, `sourceprops-de_canals.log`, and
  `sourceimport-de_canals.log` in the same log directory.
- ZIP integrity and namespace checks passed: 1,139 files, 284,623,728 bytes
  compressed and 507,021,007 bytes uncompressed. An isolated client using
  only the installed package root loaded TDM, spawned on Alpha and Omega,
  and verified health, floor physics and camera height above the pavement.
  It emitted **`CANALS_ZIP_DONE FAILURES 0`** and exited normally. Log:
  `.csgopen/logs/de-canals-verify.log`; final screenshots:
  `.csgopen/de-canals-verify/screenshots/de_canals-alpha.0001.png` and
  `.csgopen/de-canals-verify/screenshots/de_canals-omega.0001.png`.
- The full existing network smoke test passed **`SMOKE_DONE FAILURES 0`**
  against Canals, including synchronized rules and inventory, a 2,983 ms
  measured respawn interval, and the switch to Dutility. The isolated server
  used loopback port 28973 with public registration, LAN discovery and HTTP
  disabled; both processes stopped on completion. Logs:
  `.csgopen/logs/de-canals-network-{server,client}.log`.
- All 18 Source BSP unit tests and `git diff --check` passed. Regressions
  cover model index limits, retained faces and texture paths, generated model
  entity indices, unquoted VMT paths and distant coplanar collision floors.

Visual inspection confirms textured Alpha waterfront and Omega courtyard
spawn areas above the pavement. Lighting, transparency and simplified prop
collision differ from Source. Full route traversal, water interaction and bot
navigation remain manual checks; dynamic props, Source lighting and non-TDM
entities remain converter limits. The server rotation was not changed. Launch
the installed map with `scripts/csgopen/dev.sh tdm de_canals` or select it
explicitly with `scripts/csgopen/dev.sh server de_canals`.

## Imported Source stair traversal repair (2026-10-05)

A reported jump requirement on the canal bridge near the Terrorist spawn was
reproduced with the native player movement code. At Source Y 1904, the forward
crossing stopped after 47.876 native units; at Y 1936, the reverse crossing
stopped after 56.396 units. Other central lanes crossed successfully, explaining
why the issue depended on the approach to the stairs.

Two corrections are applied by the Source converter:

- Version-21 brush sides store byte-sized `bevel` and `thin` flags separately.
  Reading them as a single short wrongly excluded thin sides from collision.
  The decoder now retains thin surfaces and preserves the version-20 short
  layout. On the nearby waterside stair landing, supporting Source Z is now
  96 instead of 24. Canals world collision grows from 53,964 to 130,270
  double-sided triangles in the same 69 carriers.
- Generated maps set `stairheight` to `20 * scale`, or 5 at scale 0.25. The
  [Source SDK default](https://github.com/ValveSoftware/source-sdk-2013/blob/master/src/game/server/world.cpp)
  is 18 Source units; two additional Source units provide clearance at the
  imported mesh edges. Collision repair alone still blocked both bridge
  approaches with the upstream 4.1-native-unit threshold. At 4.5 and 4.6 one
  reverse approach still blocked, while 5 completed both. This is a saved
  per-map variable; the engine default and TDM preset are unchanged.

Executed checks:

- A separate diagnostic client exercised `physics::moveplayer` with the normal
  actor dimensions and TDM movement, without jump input. All ten 150-unit
  crossings passed at Source Y 1888, 1904, 1920, 1936 and 1952, in both
  directions, ending on floor physics. Maximum downward movement per sample
  was 0.190 native units. Logs: `.csgopen/logs/stairprobe-bridge-before.log`,
  `stairprobe-bridge-after.log`, `stairprobe-height.log`, and
  `stairprobe-final.log`. The diagnostic command exists only in an ignored
  test binary; its temporary source include was removed and the production
  physics object rebuilt without it.
- All six installed Source packages were regenerated using their existing prop
  assets: Canals, Bank, Dust2, Lake, Safehouse and Agency. Native import markers,
  ZIP integrity, namespace and the saved MPZ `stairheight` value were checked.
  Original ZIPs are retained under `.csgopen/stair-repair/*-before.zip`.
  Import logs: `.csgopen/logs/stair-repair-import-<map>.log`.
- The production client loaded only the installed package root and verified
  the saved stair height, health and supported Alpha/Omega spawns on all six
  maps: **`MAP_REPAIR_DONE FAILURES 0`**. Log:
  `.csgopen/logs/stair-repair-verify.log`.
- The final Canals package has MPZ CRC `0x6e476584` and contains 1,139 files in
  a 285,577,652-byte ZIP. The loopback multiplayer test passed the synchronized
  stair-height check and **`SMOKE_DONE FAILURES 0`**, including inventory,
  rules, a 2,991 ms respawn and the switch to Dutility. Logs:
  `.csgopen/logs/de-canals-network-{server,client}.log`.
- All 20 Source BSP unit tests and `git diff --check` passed. Regressions cover
  retained thin-side support and compatibility with version-20 bevel flags;
  the stage integration check also verifies the generated stair setting.

The initial regenerated Canals multiplayer check caught the editor profile
reusing its previously saved map configuration and therefore saving 4.1 again.
Canals was rebuilt with a fresh editor profile and the MPZ value was checked
before replacing the installed package. Prop collision remains approximate;
full traversal of every stair in the other maps remains a manual check.


## Automatic obstacle traversal and lower jumps (2026-10-05)

The opt-in TDM movement rules now use a 7-unit fast step, a 13-unit maximum
climb and a 450 ms automatic climb. Actor scale applies to both heights.
Non-pistol weapons disappear during climbing and require their normal
`delayswitch` afterwards; the pistol remains usable. Client and server share
weapon restrictions, timed climb events and welcome/resume snapshots. Protocol
283 requires matching updated clients and servers. Original movement remains
behind `csgopenmovement=0`; map-specific stair settings are retained.

Executed native checks:

- Production client and dedicated server built on macOS arm64. A separate
  opt-in client includes the production physics implementation and adds only
  test commands: `src/tests/csgopenmovement.cpp`. The normal client does not
  link these commands. Build with `CSGOPEN_MOVEMENT_TEST=1` and a separate
  `APPCLIENT` path; the Makefile rejects the normal client path.
- A synthetic collision-model fixture tested flat ground; a 7-unit step;
  7.5- and 13-unit climbs; a 14-unit wall; insufficient headroom above low
  and high obstacles; pistol climbing; a cooking HE grenade; and disabled
  automatic movement. **`MOVEMENT_DONE FAILURES 0`** in
  `.csgopen/logs/movement-fixture-verify.log`. The 100-unit walk took 1,940 ms
  both on flat ground and across the 7-unit step. Minimum horizontal speed
  at the step was 54.990 units/s, within 2% of the flat target. Each eligible
  high obstacle produced exactly one completed climb. Tests checked weapon
  visibility, shooting and switch restrictions during climbing, draw blocking
  even with weapon-state skip flags, the exact weapon draw deadline and the
  pistol exemption. A full weapon/spawn reset cleared traversal state.
- With the same actor and native jump physics, changing `impulsejump` from
  1.5 to 1.1 reduced the apex from 18.979 to 11.870 units and airtime from
  825 to 680 ms. Jump remained higher than the fast-step threshold.
- The installed Canals package passed ten 150-unit bridge crossings without
  jump input or a climb: five lanes in both directions. All reached the target
  distance. **`MOVEMENT_DONE FAILURES 0`** in
  `.csgopen/logs/movement-canals.log`. Early tests caught a classification
  regression at rounded tread edges: body clearance can be valid before the
  contact normal is flat enough for a landing. Height classification now checks
  nearby body clearance; the step/climb destination still checks support.
- A real actor and an observer connected to a dedicated loopback server on
  the synthetic map. The actor automatically climbed with an SMG; the observer
  saw both the shared climbing flag and the subsequent draw deadline.
  **`MOVEMENT_NETWORK_DONE FAILURES 0`** in
  `.csgopen/logs/movement-network-observer.log`; no weapon sync error was found.
- The canonical `config/csgopen/smoke.cfg` was rerun on the dedicated Canals
  loopback server, with only its test port changed to 28973. It passed all
  original checks plus synchronized traversal heights, climb duration and
  lower jump strength: **`SMOKE_DONE FAILURES 0`**, including inventory,
  2,995 ms respawn and map change to Dutility. The final production build
  passed the same smoke check again with a 2,990 ms respawn. Logs:
  `.csgopen/logs/de-canals-network-{server,client}.log`. Prior stair-only
  network logs are preserved with a `-stairs-only` suffix.
- All 20 Source converter unit tests and `git diff --check` passed.

To reproduce the fixture on macOS, run these commands from the checkout root.
The build and verification launches need access to the native display:

```sh
python3 scripts/csgopen/movement-fixture.py
fixture_dir="$PWD/.csgopen/movement-fixture"
src/eclipse-recoil_native "-h$fixture_dir/build" "-p$fixture_dir/data" -sm -ss0 -dw640 -dh480 -df0 '-xexec "build.cfg"'
# Require MOVEMENT_FIXTURE_BUILT in the build profile log before copying.
cp "$fixture_dir"/build/maps/csgopen_movement.* "$fixture_dir/data/maps/"
movement_alprefix=$(HOMEBREW_NO_AUTO_UPDATE=1 brew --prefix openal-soft)
PKG_CONFIG_PATH="$movement_alprefix/lib/pkgconfig${PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}" make -C src -j4 CSGOPEN_MOVEMENT_TEST=1 APPCLIENT=../.csgopen/csgopen-movement-test client
.csgopen/csgopen-movement-test_native "-h$fixture_dir/verify" "-p$fixture_dir/data" -sm -ss0 -dw640 -dh480 -df0 '-xexec "verify.cfg"'
```

Require `MOVEMENT_DONE FAILURES 0` in the verification log. All generated
assets and profiles stay under `.csgopen/`; no submodule map is edited.
Keyboard/mouse feel, presentation of the climbing animation, narrow irregular
props and exhaustive traversal on other maps remain manual checks. The test
requires enough clearance for the full body and a supported landing; it does
not authorize climbing through ceilings or onto other players.


## Small-group rotation and three-map ballot (2026-10-05)

The server preset now has 21 native maps and seven locally converted maps;
`de_stmarc` is deliberately excluded pending conversion repair. The initial
map is random. Every ballot offers three distinct random maps excluding the
current map, retains the current game rules, and runs for the full configured
20 seconds. Most votes wins; ties and empty ballots resolve randomly, with
empty ballots restricted to the offered choices.

Executed checks:

- Native client and dedicated-server build completed successfully.
- All 28 configured map names were unique and had installed native MPZ files
  or converted ZIPs containing their required MPZ and CFG files.
- The isolated loopback client/server smoke test passed with
  `VOTECHOICES_DONE FAILURES 0`: three distinct candidates, current-map
  exclusion, rejection of an outside proposal, a solo vote waiting for the
  ballot deadline, loading the voted map, and clearing the shortlist.
- The empty-ballot smoke test passed with `VOTECHOICES_DONE FAILURES 0`:
  the server loaded one of the three offered maps and cleared the shortlist.
- All five existing map-package HTTP regression tests passed.
- The final voting-panel screenshot was inspected: three distinct buttons
  render above the vote status without overlapping it.

The existing equal-vote random selection was inspected in `checkvotes`;
this run did not simulate multiple human voters. Full matches with two teams
and human mouse interaction remain manual checks. Rebuild both clients and
server before using the new shortlist UI. Repeat the smoke tests with
`python3 scripts/csgopen/test_votechoices.py` and the `--no-vote` variant;
logs and screenshots are retained under `.csgopen/votechoices-test/`.


## Map previews in the shortlist (2026-10-05)

The three-map ballot now uses clickable preview cards with map titles instead
of text-only buttons. It reads the same `maps/<name>.png` previews as the map
browser and shows a question-mark fallback when an image is unavailable.
The seven converted-map PNGs were copied from the installed ZIPs into the
Git-ignored `data/csgopen/maps/` package directory for local preview access
before a map is mounted. Other clients need their own preview assets.

The isolated native client/server empty-ballot smoke test passed with
`VOTECHOICES_DONE FAILURES 0`. Its screenshot was inspected and shows all
three map images and titles, with the vote status below them. This is a
CubeScript UI change; no native rebuild is required. Human clicking of the
new cards remains a manual check.


## Continuous timber prop collision (2026-10-05)

Selected Source static props now use a closed convex hull of their undecimated
local mesh for collision. Render decimation is unchanged. The selection is
limited to logs, fallen trees and construction/timber piles; architectural
props keep their existing collision. Hulls fill visible recesses and gaps,
so they remain an approximation rather than imported Source PHY hulls.

Executed checks:

- Blender background tests: 2 passed, verifying closed manifold edges,
  filled volume between separated timber pieces, unchanged outer bounds,
  instance rotation/scale and exclusion of architectural model names.
- Source BSP regression suite: 20 tests passed.
- Native Lake conversion completed with `SOURCEIMPORT_DONE de_lake`. All
  427 playable props decoded successfully; continuous collision applies to
  one `fallentree_dry01` and three `construction_stack_plywood_01` instances.
- Installed the regenerated local `data/csgopen/de_lake.zip` after ZIP CRC
  verification, checking all 140 mapmodel configurations exist and saved
  `stairheight` remains 5. All 179 existing visual prop files are byte-identical.
  Existing map previews and ancillary map files were retained. The previous
  ZIP and verification report are saved under the Git-ignored
  `.csgopen/map-convert/de_lake-source.BRczCQ/` stage.

Manual walking/climbing on the affected Lake props, especially entering and
leaving the fallen tree from different directions, remains pending. Other
installed converted maps have not been regenerated. No actor dimensions or
movement rules were changed.


## Mine placement on imported collision surfaces (2026-10-05)

The native BIH ellipse collision path increments `collideinside` before
selecting a blocking triangle normal. Projectile impact previously treated
that count as unresolved penetration, removed `STICK_GEOM`, and killed the
mine on a valid surface contact. The TDM mine now retains sticky placement
when a static surface supplies a valid normal. Unresolved overlaps, other
projectiles and the original gameplay profile retain their existing paths.
This changes client projectile physics, with no map or protocol change.

Executed checks:

- Reproduced the original failure against Lake's actual collision triangles:
  `HIT 1 INSIDE 2 NORMAL 0.022 0.026 0.999`, followed by failed sticky placement
  and armed-trigger checks (`MINE_DONE FAILURES 2`).
- With the fix, the same Lake contact passes; native Echo reports `INSIDE 0`
  and also passes. Both logs contain **`MINE_DONE FAILURES 0`**. Checks cover
  sticky placement without destruction, unchanged fuse, unarmed enemy
  exclusion, armed enemy triggering, owner/ally exclusion, ordinary bullet
  impact, the original collision path and unresolved-overlap fallback.
- Rebuilt the normal native client and dedicated server with
  `scripts/csgopen/dev.sh build`; isolated test commands are not linked into
  the normal client. Logs are under `.csgopen/logs/mine-contact-*`.
- Dedicated loopback smoke test passed with **`SMOKE_DONE FAILURES 0`**,
  checking synchronized settings, utility inventories, respawn and map change.
  The first test profile omitted the launcher's TDM `localinit.cfg`, so its
  loadout was parsed under original rules and five inventory/selection checks
  failed. Repeating with the standard TDM initialization passed without
  changing gameplay or the smoke assertions. The initial log is retained.
  The isolated server on `127.0.0.1:28811` was stopped after testing.

The contact tests use synthetic projectiles against loaded map geometry and
call the real collision, impact and proximity paths. Launching from physical
input, wall placement and visual synchronization between two clients remain
manual checks.

Repeat the fixed contact tests with the opt-in binary:

```sh
python3 scripts/csgopen/mine-fixture.py
mine_test_alprefix=$(HOMEBREW_NO_AUTO_UPDATE=1 brew --prefix openal-soft)
PKG_CONFIG_PATH="$mine_test_alprefix/lib/pkgconfig${PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}" make -C src -j4 CSGOPEN_MINE_TEST=1 APPCLIENT=../.csgopen/csgopen-mine-test client
mine_fixture_dir="$PWD/.csgopen/mine-contact-test"
.csgopen/csgopen-mine-test_native "-h$mine_fixture_dir/lake" "-p$PWD/data/csgopen" "-g$PWD/.csgopen/logs/mine-contact-lake.log" -sm -ss0 -dw640 -dh480 -df0 '-xexec "verify.cfg"'
.csgopen/csgopen-mine-test_native "-h$mine_fixture_dir/native" "-p$PWD/data/csgopen" "-g$PWD/.csgopen/logs/mine-contact-echo.log" -sm -ss0 -dw640 -dh480 -df0 '-xexec "verify.cfg"'
```

Lake requires an installed local `data/csgopen/de_lake.zip`. Require
`MINE_DONE FAILURES 0` in each log, not just a successful client exit.


## Slope transitions without terrain subdivision (2026-10-05)

The TDM ledge path prevented the ordinary ramp solver from handling some
contacts while already moving uphill. Grounded players/bots on a walkable
slope now first try a tangent move with two bounded collision/support checks.
If that fails, the ordinary ramp solver and ledge rules remain available.
Original movement, liquids, ladders and enemy actors retain their paths.
Terrain meshes, displacement LOD, actor dimensions and slope limits are
unchanged. No render/collision subdivision or new actor cache was added.

Executed checks:

- Native synthetic fixture covers two connected faceted slopes in both
  directions, a tall obstacle and a low ceiling on a slope, and the existing
  ten step/climb cases and jump test. **`MOVEMENT_DONE FAILURES 0`** in
  `.csgopen/logs/slope-fixed-verify.log`. The unchanged steep uphill case
  previously reached only 198.821 of 240 units within 8 seconds; the fix
  reaches 240.250 in 6.91 seconds, without a climb or jump.
- Twenty repetitions of each of the four open slope routes (80 runs per
  binary) compare the old and fixed physics against identical geometry.
  Median combined CPU time for four routes is 13.8975 ms before and
  13.2150 ms after. This is a local physics microbenchmark, not an FPS
  benchmark; the old steep uphill route is capped before completing.
  Per-route results are saved in
  `.csgopen/movement-fixture/slope-performance.json`.
- Loaded the installed Lake ZIP and checked four real-map routes. The
  94.414-unit slope at Y=446.763 is traversed in both directions without
  climbing. A second candidate at Y=624.453 crosses authored Source
  player-clip brush 577 (`contents=0x8030000`); both directions still block.
  Final **`MOVEMENT_DONE FAILURES 0`** is in
  `.csgopen/logs/slope-lake-verify.log`. Initial tests had assumed this second
  path was open; its two failures are retained in `slope-lake-initial.log`
  and were resolved by inspecting the authored clip volume, not by weakening
  collision.
- Lake's installed ZIP remains byte-identical: SHA-256
  `ddd09885448dfb75aed5212d610d7e17bad7101ccf3be06da271b76689ff66ea`,
  47,712,848 bytes. No installed map package was regenerated or modified.
- Production native client rebuilt with `scripts/csgopen/dev.sh build`;
  dedicated server is up to date. Test commands remain opt-in.
- Dedicated loopback network smoke test passed with **`SMOKE_DONE FAILURES 0`**
  in `.csgopen/logs/slope-network-smoke.log`, including synchronized settings,
  utility inventories, respawn and map change. The isolated server on
  `127.0.0.1:28811` was stopped afterwards.

Repeat the fixture and opt-in build with the movement-test commands above.
The generated `verify/verify.cfg` now includes slope regressions;
`verify/bench.cfg` repeats the four open slope routes twenty times.
Mouse/keyboard feel across all Lake paths and scene-level FPS remain manual
checks. Authored clip barriers and genuinely steep/non-walkable terrain
remain intentionally blocking.

## Bundled construction wood collision (2026-10-05)

A follow-up report identified a snag while climbing onto a timber pile near
Lake's spawn. Inspection found that `construction_wood_2x4_` models were not
covered by the continuous collision selection. These bundles and
`construction_stack_` props now use a closed model-space bounding box (12
triangles per instance), removing individual board slots and bevels without
changing render geometry, instance rotation, or scale. Architecture remains
excluded. Bounds can fill visible recesses; this is intentional for these piles.

Executed checks:

- Blender collision tests: 2 passed, including category selection, closed hull,
  retained bounds, twelve-triangle box, and transformed coordinates.
- Source BSP converter unit tests: 20 passed.
- Lake regenerated successfully (`SOURCEIMPORT_DONE de_lake`), 427 props and
  125 models decoded with no failures. Continuous collision covers 20 instances
  instead of 4. Prop collision triangles decrease from 452,806 to 435,742;
  render triangles remain 299,938 and all 179 render prop files are byte-identical.
- Native movement checks start atop the spawn-side wood bundle and stacked
  plywood, then walk in both X directions without jumping or climbing:
  `MOVEMENT_DONE FAILURES 0`. This verifies four escape routes, rather than
  reproducing the user's exact approach or every possible contact direction.
- Local dedicated-server smoke: `SMOKE_DONE FAILURES 0`; server stopped.
- Regenerated ZIP passed CRC validation and replaced local
  `data/csgopen/de_lake.zip`. A backup and reports are in
  `.csgopen/timber-repair/`. ZIP size decreases from 47,712,848 to 47,083,014 bytes.

Manual verification of the reported approach onto the pile remains pending.
Other converted maps need regeneration to receive this converter rule.

## Lake wall-to-bench movement (2026-10-06)

The reported route was reproduced from the low wall toward the two curved
wooden benches near the other spawn. On the previous package, the centre route
at X=1457.35, Y=534.3125, feet Z=2219.1 stopped after 5.096 of 18 requested
units without climbing. The neighbouring route lanes remained passable.

The converter now gives `models/props/de_inferno/bench_wood.mdl` a composite
collision: flat seat and back boxes with no slot at their joint, plus separate
lower support boxes. The space between supports stays open. The policy applies
to every instance of that model on converted maps; architecture and other bench
models retain their existing policy. Candidates exceeding the current reduced
mesh triangle budget fall back to the existing collision. This intentionally
bridges visible slat gaps and fills small recesses in the support profiles.

The CSGOpen movement solver also retains the native bounded step fallback on
flat support when a traverse probe rejects a shared edge. Climbing is still
attempted first; the fallback uses the existing map stair height. The original
profile follows the same code path as before.

Executed checks:

- Blender collision tests: 6 passed, including closed volumes, retained gaps,
  flat support treads, narrow upper profiles, the complete 60-triangle composite
  bench, and unchanged instance transforms.
- Source BSP tests: 20 passed. `scripts/csgopen/dev.sh check` and `build` passed.
- Native Lake integration: 20 routes passed (`MOVEMENT_DONE FAILURES 0`): six
  wall-to-bench lanes, six reverse lanes, four lateral wall routes and four
  timber-pile escape routes. Logs are in `.csgopen/timber-repair/complete-floor.log`.
- Existing movement fixture passed (`MOVEMENT_DONE FAILURES 0`), including ten
  obstacle/climb cases, both directions on open slopes, wall/ceiling barriers,
  utility cooking restrictions, jumping and the original movement profile.
  Log: `.csgopen/timber-repair/bench-movement-fixture.log`.
- All 179 visible prop files remain byte-identical; render triangles remain
  299,938. Prop collision triangles decrease from 435,742 to 430,430; collision
  tile count remains 35. Four bench instances receive the new profile.
- The generated ZIP passed CRC checks and was installed locally at
  `data/csgopen/de_lake.zip`. Size decreases from 47,083,014 to 46,988,674 bytes;
  SHA-256 is `5a679db3428fe1e2d9cc7a66dbad5a78a5ad9962c8edf57a086ae2ce816e72b1`.
  Backup and report: `.csgopen/timber-repair/de_lake-before-benches.zip` and
  `bench-report-final.json` in the same directory.

The first resumed route runs lacked the map PNG, leaving the match waiting for
map transfer. Their zero-progress results are invalid; the complete package was
retested after the match started. Manual mouse/keyboard verification and a
scene-level FPS benchmark remain pending. The remaining converted packages were
regenerated in the subsequent all-map run recorded below.

The rebuilt production client passed the dedicated loopback smoke test with
`SMOKE_DONE FAILURES 0` in `.csgopen/timber-repair/bench-smoke-final.log`.
The isolated server on port 28811 was stopped afterwards.

## Regeneration of all installed Source maps (2026-10-06)

All eight installed packages were regenerated from the local CS:GO legacy BSPs
and VPK with the current converter: `ar_baggage`, `cs_agency`, `de_bank`,
`de_canals`, `de_dust2`, `de_lake`, `de_safehouse`, and `de_stmarc`.
Scale 0.25, displacement LOD 2, and the existing 300,000 prop simplification
budget were retained. Structural preservation can keep the resulting prop count
above that budget, as before. Each package passed the native
`SOURCEIMPORT_DONE` marker, zero failed prop decodes, ZIP CRC validation, expected
namespace validation, and MPZ/CFG/PNG presence checks before installation.

Actual OBJ face counts, rather than rounded converter metadata, were compared
against the backed-up packages:

| Map | Visible prop triangles | Prop collision before | Prop collision after | World collision triangles |
| --- | ---: | ---: | ---: | ---: |
| ar_baggage | 300,211 | 446,348 | 446,348 | 57,604 |
| cs_agency | 305,760 | 393,864 | 393,864 | 42,184 |
| de_bank | 303,003 | 400,064 | 400,064 | 22,842 |
| de_canals | 325,416 | 586,522 | 586,522 | 130,270 |
| de_dust2 | 352,700 | 366,836 | 366,836 | 80,578 |
| de_lake | 299,938 | 430,430 | 430,430 | 29,290 |
| de_safehouse | 299,722 | 488,178 | 485,142 | 30,340 |
| de_stmarc | 307,378 | 316,216 | 312,846 | 31,142 |

Visible prop and world collision triangle counts remain unchanged on every map.
Safehouse and St. Marc have 3,036 and 3,370 fewer prop collision triangles.
Lake already contained the corrected timber and bench collision package.
All prop texture files remain byte-identical. Dust2 has 15 regenerated prop OBJ
files with small decimation differences at the same triangle count. Canals has
two OBJ configuration changes that move the same spotlight material bindings
after `objload`. Other visible prop files remain byte-identical.

The eight ZIPs total 724,929,013 bytes, down from 729,728,896 bytes. Previous
packages are retained in `.csgopen/regenerate-all-20261006/backups/`;
`results.json` records conversion and package hashes, and `audit.json` records
actual face counts and changed visible files. St. Marc remains excluded from
the small-group rotation; regeneration does not establish that its separate
conversion issues are repaired. Full manual route coverage and scene-level FPS
measurements across all eight maps remain pending.

The installed-package client run in `verify-final.log` loaded all eight maps.
The seven maps permitted in the rotation passed all seven checks each: map
stair height, Alpha team/health/floor support, and Omega team/alive/floor support.
St. Marc passed loading and player state checks but failed floor support at both
sampled team spawns (`REGEN_MAP_DONE FAILURES 2`). The backed-up St. Marc package
reproduced both failures in `baseline-stmarc.log` (`BASELINE_MAP_DONE FAILURES 2`),
confirming the spawn issue predates this regeneration. These checks cover spawn
support, not full movement routes. `native-checks.json` contains the per-map
results. The initial verification script used `(gamestate)` instead of
`$gamestate` and never reached its assertions; it was corrected and restarted
before the recorded final run.

The production client also passed the dedicated loopback multiplayer test with
`SMOKE_DONE FAILURES 0` in `.csgopen/regenerate-all-20261006/smoke-final.log`,
including rules, inventory, respawn, and map change checks. The isolated server
on port 28811 was stopped afterwards. `git diff --check` passed.

## General compact-prop smoothing and bounded seam recovery (2026-10-06)

The converter now applies a geometric rule beyond the named timber and bench
families. Solid props below 10 map units in height, or narrower than 8 units in
both horizontal dimensions, can use a convex collision envelope. Instance
scale and rotated bounds are checked. Door/window frames and architectural
passage families are excluded, and larger props that could contain crouched
passages retain their existing collision. A hull replaces the original only
when it has fewer triangles. Render geometry, world brushes, terrain LOD,
player size and authored playerclip are unchanged.

The TDM engine also tests the immediate horizontal destination across a small
seam when the farther tread probe fails. Rise is bounded to one actor-scaled
map unit and capped by both step settings. The swept body path and a supported
landing on an already walkable surface are required. It preserves horizontal
velocity and does not apply in the original profile, in mid-air, in liquids,
on ladders, on moving platforms, while climbing or against another player.
It is not a teleport or an increase in climb height.

Executed checks:

- Eight Blender collision tests passed, including compact cavities, unchanged
  architectural openings, oversized instances, rotated panels and no extra
  collision faces. Log: `.csgopen/logs/general-smoothing-unit.log`.
- Twenty Source BSP tests passed. Log:
  `.csgopen/logs/general-smoothing-sourcebsp.log`.
- Native build and dependency/content checks passed. Logs:
  `.csgopen/logs/general-smoothing-build.log` and `general-smoothing-check.log`.
- The native movement fixture passed `MOVEMENT_DONE FAILURES 0` in
  `.csgopen/logs/general-smoothing-movement-final.log`. Recovery crossed a
  0.75-unit seam with 0.767 units of rise; a 2-unit barrier, a low ceiling,
  missing landing support and an airborne actor rejected it. Original-profile
  movement, knee steps, waist climbs, weapon restrictions, slope barriers,
  uphill/downhill traversal and jump checks also passed.
- Eighty repeated slope routes passed with no climbs. The sum of the four
  route median CPU times was 12,473.5 microseconds, compared with 13,215.0 in
  the earlier slope-fix benchmark. The uphill routes used fewer physics frames.
  This is a synthetic movement CPU comparison, not a scene FPS measurement.
  Logs and measurements are under `.csgopen/general-smoothing-20261006/` in
  `slope-bench.log` and `slope-performance.json`.

All eight installed packages were regenerated with the final
`compact-world-bounds-v1` rule. The rule smoothed 1,178 prop instances. Actual
visible prop triangle counts and world collision triangle counts remain
unchanged on every map; all visible prop files and world render OBJ files are
byte-identical to the preceding installed packages. Prop collision totals:

| Map | Smoothed instances | Collision triangles before | Collision triangles after |
| --- | ---: | ---: | ---: |
| ar_baggage | 143 | 446,348 | 265,942 |
| cs_agency | 329 | 393,864 | 268,496 |
| de_bank | 219 | 400,064 | 343,134 |
| de_canals | 178 | 586,522 | 566,414 |
| de_dust2 | 99 | 366,836 | 356,306 |
| de_lake | 104 | 430,430 | 377,858 |
| de_safehouse | 30 | 485,142 | 462,290 |
| de_stmarc | 76 | 312,846 | 283,054 |
| Total | 1,178 | 3,422,052 | 2,923,494 |

This removes 498,558 prop collision triangles (14.57%). ZIP size decreases from
724,929,013 to 716,389,014 bytes. Each package passed native compilation, zero
failed prop decodes, ZIP CRC, namespace, and MPZ/CFG/PNG presence checks. Reports,
hashes and previous packages are in `.csgopen/general-smoothing-20261006/`:
`results.json`, `audit.json`, `world-render-audit.json`, and `backups/`.
Dust2's fresh render decimation added a few triangles, so installation was
blocked until its previous visible prop files were restored and the map was
compiled again with the new collision. The first three packages were rebuilt
with the final rotation guard before these counts were recorded.

The updated Lake package and movement engine passed all 20 earlier routes on
the timber piles, wall and benches in both directions, without extra climbs or
jumps: `lake-routes.log` reports `MOVEMENT_DONE FAILURES 0`. Full keyboard/mouse
coverage of every corner and scene FPS measurement remain pending. St. Marc
remains excluded from the rotation because of its separate spawn support issue.

The final installed-package run loaded all eight maps. The seven rotation maps
passed all spawn support, health/team state and map stair-height checks after
Dust2 was corrected. `maps-final.log` first caught Dust2's default stair height
after recompilation against a saved profile configuration; the fresh BSP
configuration was restored into the profile and the map recompiled.
`dust2-final-verify.log` then reported `DUST2_FINAL_DONE FAILURES 0`, including
stair height 5. The two St. Marc floor-support failures reproduce its previously
recorded issue and do not enable it for rotation.

The final production client passed the dedicated loopback multiplayer smoke
test with `SMOKE_DONE FAILURES 0` in `smoke-final.log` under the same report
directory. The test server on port 28811 was stopped afterwards.
`native-checks.json` records the final per-map checks, using the corrected
Dust2 verification. `git diff --check` passed.
# LAN launcher validation (2026-10-07)

- Executed: `bash -n scripts/csgopen/server-lan.sh` passed.
- Code inspection: the launcher uses a separate LAN profile, loads the TDM
  and server-maps configurations before socket setup, enables LAN discovery
  and map-package HTTP on all IPv4 interfaces, and disables master registration.
- Pending manual check: start the launcher and verify discovery and map
  downloads from another LAN client. No LAN server was started during this check.


# Imported stair movement validation (2026-10-07)

The user still reported sticking, predominantly uphill, on internal Dust2
stairs. The correction is in the engine: a grounded actor on a flat tread
now attempts the supported tangent move when its next contact is a walkable
bevel. Previously only actors already following a slope attempted this path,
so a bevel could be misclassified as a ledge. Immediate supported step recovery
also uses the map stair height rather than the previous one-unit cap; body
clearance, swept path and configured step-height limits still apply.

No map package, rendered mesh, collision mesh or polygon count changed in this
iteration. Existing compact-prop smoothing remains in place.

Executed checks (logs and reproducible local profiles are in
`.csgopen/stairs-20261007/`):

- The pre-change test client reproduced two complete stops at the walkable
  bevel in the sampled Dust2 area: progress 23.276 of 36 units, normal
  `(0.371, 0, 0.928)`, with a flat support normal.
- Identical twelve routes at three lateral positions on the real installed
  Dust2 map were compared using the before/after clients: straight uphill,
  downhill, and uphill at 85/95 degrees. The baseline produced seven failures
  (two stalls and five unwanted climbs); the final engine completed all twelve
  without jumps or climbs: `dust-final.log`, `MOVEMENT_DONE FAILURES 0`.
  The baseline log is `dust-baseline-final.log`; both profiles retain `test.cfg`.
  Endpoints remain within the stair/landing height range. Earlier exploratory
  routes whose initial coordinates fell below the map were discarded, and
  are not counted as successful tests.
- The synthetic fixture covers eight closely spaced 4.5-unit risers, both
  directions, a low ceiling and a tall blocking wall. Clean synthetic stairs
  also passed before the fix; the real Dust2 comparison establishes the
  regression. The full fixture also checks low/high obstacles, slope limits,
  jumping, landing support, airborne actors and the original movement profile.
  `fixture-final.log`: `MOVEMENT_DONE FAILURES 0`, including explicit recovery
  across a two-unit step within map stair height and blocked low ceilings.
- All twenty existing Lake routes near the timber piles and wall/benches
  remain successful without climbs: `lake-final.log`,
  `MOVEMENT_DONE FAILURES 0`.
- `scripts/csgopen/dev.sh check` and the production native client/server build
  passed. The separate opt-in movement client built successfully.

Coverage is automated actor movement on the sampled routes, not an exhaustive
manual traversal of every corner of every map. Collision normals, true walls
and ceilings remain authoritative; no unconditional teleport or noclip recovery
was introduced. The existing StMarc rotation exclusion remains unchanged.

The final production client passed the dedicated loopback multiplayer smoke
with `SMOKE_DONE FAILURES 0` in `smoke-final.log`. The dedicated server was
bound only to `127.0.0.1:28811`, with master registration and LAN discovery
disabled, and was stopped after the test. `git diff --check` passed.

The twelve routes above sampled another Dust2 location, not the curved B-tunnel
stairs in the later screenshot: Source X is reflected during conversion. Their
engine comparison remains valid, but does not establish B-stair coverage.

# Curved B-tunnel staircase validation (2026-10-07)

The screenshot identifies the curved Dust2 B-tunnel stairs, from approximately
`(1216, 990, 2132.16)` to `(1270, 944.5, 2168.16)` in engine coordinates.
The original converted world retained internal solid/player-clip faces; small
invisible walking ramps also retained foundation walls. The decimated stair
prop contributed a separate snag near the lower landing.

The converter now discards fully enclosed brush faces, retaining coincident
exterior faces. Small, non-solid player-clip ramps with an authored walkable
incline export walking surfaces rather than foundation walls. Solid brush walls,
vertical player-clip barriers, displacement terrain and openings keep their
existing exterior collision. This policy only removes triangles. The curved
stair prop additionally has a reviewed, model-specific continuous surface in
`scripts/csgopen/collision-overrides/dust_kasbah_stairs002.json`: 87 triangles
replace 159; no convex hull closes the central pillar or passage. Other stair
models keep their geometry. Supported movement recovery also distinguishes
ordinary uphill velocity from an upward jumping impulse.

Executed checks and local artifacts in `.csgopen/b-stairs-20261007/`:

- The same six complete paths sample the center and offsets of two engine units,
  uphill and downhill, with floor-height continuity checks and no jump input.
  `full-b-baseline.log` reproduces four failures with the previous package.
  `full-b-combined.log` completes all six without climbs:
  `MOVEMENT_DONE FAILURES 0`. The installed ZIP repeats the same six successes
  in `full-b-installed.log`, also with `MOVEMENT_DONE FAILURES 0`.
  Intermediate candidates with incomplete face
  removal failed and were not installed.
- Dust2 world collision decreases from 80,578 to 56,902 double-sided triangles;
  total world/prop collision decreases from 436,884 to 413,064 (5.45%). All render
  files, textures, map entities, configuration and compiled MPZ are byte-identical.
  The installed ZIP is 124,947,094 bytes; `final-audit.json` records changed files
  and SHA-256. Only Dust2 was repackaged during this screenshot-specific iteration.
- All 24 Source BSP tests and nine Blender collision tests pass, including
  adjacent volumes, contained brushes, exterior coincidences, player passages,
  solid ramp sides, large clip ramps and the stair override's bounds/budget.
- `fixture-final.log`: `MOVEMENT_DONE FAILURES 0`, covering real barriers, low
  ceilings, risers, slopes, jumping, unsupported/airborne actors and the original
  profile, plus uphill velocity recovery. `lake-final.log` passes all twenty
  prior timber/bench routes with `MOVEMENT_DONE FAILURES 0`.
- Native prerequisite checks and production/test-client builds passed. The
  production dedicated loopback smoke passed `SMOKE_DONE FAILURES 0` in
  `smoke-final.log`; master registration was disabled and the server was stopped.

Coverage is automated movement on these sampled paths, not an exhaustive manual
traversal of every converted map. Restart the game to reload the changed collision
models from the installed package. St. Marc remains excluded from rotation.

# Long A door collision validation (2026-10-07)

The user reported a temporary snag in Dust2's opened Long A doors. The source
`dust_door_long_doors_01.mdl` combines two angled leaves with metalwork and small
wooden details. Its decimated collision retains 729 triangles. The converter now
builds a separate convex surface for each leaf from the full source geometry,
using 306 triangles in total. It never wraps both panels in a single hull and
leaves the architectural doorframe unchanged. The rule is restricted to this
reviewed model, rejects geometry crossing the panel separation and falls back
when its triangle budget would increase. There is no new engine movement rule.

Executed artifacts are in `.csgopen/doors-20261007/`:

- Eighteen straight/slightly oblique attempts at the first door compare identical
  before/after movement: the original mesh stops all eighteen, while the smoother
  candidate completes seven. These probes are not all unobstructed routes;
  continued direct contact with an opened panel is allowed to block movement.
- Twelve guided paths follow the actual gap between the leaves, three approach
  offsets in both directions at each doorway. `guided-final-candidate.log` passes
  all twelve without jumps or climbs: `MOVEMENT_DONE FAILURES 0`. Initial north
  door probes overlapping the real crates in the inner chamber were corrected
  and are excluded from this successful coverage.
- The package audit confirms only the prop collision OBJ for Source tile `0_0_0`
  changed. Both instances use the new leaf geometry. Render meshes, textures,
  doorframes, world collision, the B staircase override, entities, MPZ and map
  configuration are byte-identical. Collision decreases by 1,692 double-sided
  triangles, from 413,064 to 411,372; `audit.json` records the checksum and counts.
- `installed.log` confirms the installed package passes all twelve door paths,
  all six curved B-stair routes and two checks that real side obstacles block
  movement, with `MOVEMENT_DONE FAILURES 0`.
- All ten Blender collision tests and 24 Source BSP tests pass. Panel separation,
  original bounds, unrelated frames, crossing geometry and the triangle budget
  have explicit checks. Native prerequisite checks and the opt-in test build pass.
- The production loopback multiplayer smoke passes `SMOKE_DONE FAILURES 0` in
  `smoke-final.log`; the dedicated server was stopped afterward. `git diff --check`
  passes.

The automated paths sample the openings; manual traversal of every possible
approach remains open. Restart the game to discard cached collision models.


## Dust2 B tunnel entrance: uninterrupted stair running (2026-10-07)

The four shallow exterior steps in the reported screenshot use
`dust_stairs003_256.mdl`, at Source origin `(-1536, 522, 2)`. The BSP already
provides their continuous walking ramp. The extra decimated prop collider causes
long velocity interruptions. Removing only that duplicated collider fixes these
routes with the existing movement implementation; no additional production
engine rule was kept from this investigation.

The converter now identifies low rectangular regular stair flights and checks
world support at the centroid and three interior points of each original tread
triangle after transforming the instance. Every support height must be within
-1 to +8 Source units of the tread. Missing, distant or incomplete support keeps
the prop collider. The test rejects architectural names and tapered geometry.
The actual four instances of this model were evaluated: only the reported B
entrance qualifies; the other three retain their 55-triangle collider.

Artifacts are in `.csgopen/short-stairs-20261007/`:

- `before-running.log` and `after-running.log` use the same native test binary,
  movement settings, starting running velocity and twelve paths: three lanes,
  straight and slightly oblique uphill approaches, plus three downhill routes.
  The original package has seven failed continuity checks, with sustained slow
  periods up to 580 ms. The corrected package passes all twelve, travels the
  routes in 625–755 ms and reaches the expected upper/lower floor elevations.
  Eleven paths have no slow physics tick; one has a single 5 ms step-up correction
  with retained velocity. The regression flags three consecutive slow 5 ms ticks
  (15 ms) rather than treating one discrete vertical correction as a running stop.
- `coverage.log` confirms selection of only the supported instance.
  All eleven Blender collision tests and 24 Source BSP tests pass. Native
  prerequisite checks, test compilation and production client/server build pass.
- `audit.json` confirms only one prop collision OBJ changes. Collision decreases
  from 411,372 to 411,262 double-sided triangles; package size decreases from
  124,900,457 to 124,897,732 bytes. Render geometry, world collision, all other
  props, entities, MPZ and configuration are byte-identical. The installed package
  SHA-256 is `b6a7d1e2ca5c06d93ebac5179bf297fe1318e85ab0d9c6f0343e177cafa0479e`.

The installed package also passes the twelve running routes, twelve guided door
routes, six internal B stair routes and two real-wall blocking checks in
`installed.log`, with `MOVEMENT_DONE FAILURES 0`. The production multiplayer
loopback smoke passes `SMOKE_DONE FAILURES 0` in `smoke-final.log`; its dedicated
server was stopped afterward. `git diff --check` passes.

This is automated coverage of the reported approaches, not a claim that every
map location is verified. Restart the game to reload cached collision models.


## All converted maps refreshed with collision fixes (2026-10-07)

Reprocessed all eight local CS:GO legacy BSP packages at the existing scale 0.25,
displacement LOD 2 and 300,000 prop triangle budget. Artifacts, original package
backups, stages, checksums and exact counts are under
`.csgopen/regenerate-all-20261007/`. Installation uses an atomic ZIP replacement.

| Map | Collision triangles before | Collision triangles after |
| --- | ---: | ---: |
| ar_baggage | 323,546 | 294,634 |
| cs_agency | 310,680 | 291,912 |
| de_bank | 365,976 | 356,996 |
| de_canals | 696,684 | 638,376 |
| de_dust2 | 411,262 | 411,262 |
| de_lake | 407,148 | 395,304 |
| de_safehouse | 492,630 | 479,066 |
| de_stmarc | 314,196 | 302,066 |

The total falls from 3,322,122 to 3,169,616 double-sided collision triangles:
152,506 fewer (4.59%). Visible prop and world render OBJ files are byte-identical
on all eight maps. ZIP CRC, namespaces and MPZ/CFG/PNG presence pass; no package
increases its visible or collision triangle count. The new authored stair
support rule also removes 472 redundant prop collision triangles on Canals.
The remaining reductions come from the previous BSP collision cleanup, now
applied to the other packages. ZIP sizes total 715,004,631 bytes.

Dust2 already included the latest collision fixes. Its fresh Blender decimation
added three visible and two collision triangles, so that candidate was rejected.
Recompiling with the verified prop meshes passed the twelve entrance running
routes and all twelve door routes but failed one internal B stair lane. The
final package therefore retains the exact previously verified world collision
and compiled map/settings as well. This preserves the user-confirmed movement
and prevents fresh simplification or serialization from changing tested seams.
`dust2-movement-final.log` passes all twelve running, twelve door, six internal
stair and two real-wall blocking routes, with `MOVEMENT_DONE FAILURES 0` and
map stair height 5. The discarded recompile is recorded separately.

`lake-movement.log` passes all twenty earlier timber, wall and bench routes with
`MOVEMENT_DONE FAILURES 0`. All 24 BSP and eleven Blender regression tests pass.
The production dedicated-loopback smoke reports `SMOKE_DONE FAILURES 0` in
`smoke-final.log`; its server was stopped afterward. St. Marc was regenerated
but remains excluded from rotation for its previously recorded spawn-support
problem. These checks do not establish movement coverage of every location.

The completed native spawn checks pass all seven rotation maps, including both
teams, health, floor support and map stair height. `native-checks.json` records
each successful check and source log: the first four maps in `maps-final.log`,
Dust2 in `maps-rest-final.log`, and Lake/Safehouse in `maps-last-final.log`.
The second run was interrupted by the user after a Lake floor assertion failed
at the 2.5-second sample. The unchanged final Lake package passes the subsequent
5-second settling checks for both teams. These runs sample selected spawns;
they do not establish support for every randomized spawn. Installed SHA-256
hashes and ZIP CRCs were verified again after completion. `git diff --check`
passes. No commits or pushes were made.


## Agency exterior access: diagonal modular staircase (2026-10-07)

The exterior approach near the CT spawn uses two instances of
`models/props/de_vertigo/step_64x32.mdl` and one
`models/props/de_vertigo/topstep_16x8.mdl`. The original decimated flight collision
blocks the central uphill approach at its first tread; the side approaches
complete with sustained slow periods of 220–230 ms. A first continuous-flight
candidate clears the first blockage but keeps the slowdown at the upper trim.
The final collision replaces both flights and their upper connector.

The converter has a reviewed model-specific rule for these two module types:
each flight uses a closed incline from local height 3 to 35 over its 64-unit run;
the upper connector has a flat height-3 walking surface. Lower support volumes
and instance transforms are retained. The twelve-triangle prisms are accepted
only for the expected nominal footprint and within the original triangle budget.
Later general smoothing cannot replace the reviewed collision. The render meshes
and handrails remain unchanged. The other seven converted maps do not use these
two models, so only Agency needs a package update. There is no engine change.

Artifacts are in `.csgopen/agency-access-20261007/`:

- `baseline.log` reproduces three failed uphill continuity checks, including the
  central blockage. `candidate-raccordo.log` passes all twelve straight routes.
- `export-check.log` runs the complete Blender prop export with the production
  converter: zero failed models, 267,536 prop collision triangles, and only the
  expected collision tile changes. One unrelated freshly decimated render OBJ
  differs and is discarded; all installed render files are retained exactly.
- `installed.log` passes sixteen routes: ten exterior uphill/downhill approaches
  across three lanes, including oblique central routes, and six routes on the
  nearby interior staircase. It reports `MOVEMENT_DONE FAILURES 0`, with no climbs
  and no sustained slow period. Two routes have a single 5 ms discrete correction.
- All twelve Blender collision tests pass, including ramp geometry, connector
  height, unknown models, unexpected footprint and small-budget fallbacks.
  Native prerequisites and `git diff --check` pass.
- `audit.json` confirms only the prop collision OBJ for Source tile `n1_n2_0`
  changes. World collision, visible geometry, other props, entities, MPZ and CFG
  are byte-identical. Total collision decreases from 291,912 to
  290,952 triangles (960 fewer); ZIP size decreases from
  59,103,199 to 59,084,115 bytes. Installed SHA-256:
  `e87d45a0a473376d54412bcb45198dedcd9562ac9629bb999fcfbb0ff3e155f3`. The original package is retained as `cs_agency-before.zip`.

`landing.log` also verifies ten exterior route endpoints after stationary
settling: each rests on `PHYS_FLOOR` within 0.1 map units of the expected upper
or lower landing. This distinguishes short airborne stair transitions during
running from missing support. The production loopback smoke passes
`SMOKE_DONE FAILURES 0` in `smoke-final.log`; its dedicated server was stopped.
The final ZIP hash, CRC and single-file change were verified again. Restart the
game to discard the cached collision model. Manual coverage of every approach
remains open.

## Full conversion rerun after the Agency access fix (2026-10-07)

The production converter was rerun sequentially on all eight existing BSPs:
Baggage, Agency, Bank, Canals, Dust2, Lake, Safehouse and St. Marc. All eight
complete with the native `SOURCEIMPORT_DONE` marker and zero failed prop models.
The scale (0.25), displacement LOD (2) and render prop budget (300,000) are
unchanged. Artifacts, backups and per-map reports are retained in
`.csgopen/regenerate-all-agency-20261007/`.

Installation preserves validated visible prop files and serialized map settings
and entities. Dust2 also retains its validated world and prop collision files:
the Agency module rule does not apply there, and a fresh bake previously
regressed a tested internal stair lane. The new exports for the other seven
maps reproduce the existing collision assets exactly. `audit.json` confirms
all installed package contents are byte-identical to the pre-run assets,
including the corrected Agency staircase. ZIP compression reduces aggregate
archive size from 714,985,547 to 714,161,849 bytes; total collision remains
3,168,656 triangles. Every ZIP passes CRC validation and retains its MPZ,
CFG and preview. No visible geometry or triangle counts increase.

Executed native checks on the installed packages:

- All 49 loading, team, health, stair-height and settled spawn-support checks
  pass across the seven enabled maps (`maps.log`). St. Marc remains excluded
  from the rotation because its previously documented spawn issue is unresolved.
- Agency's sixteen exterior and interior routes pass, including diagonal
  uphill/downhill approaches (`agency-movement.log`).
- Dust2's thirty-two cases pass: shallow entrance steps, Long A doors, internal
  B stairs and true wall barriers (`dust2-movement.log`).
- Lake's twenty cases on log piles and the wall/bench approaches pass
  (`lake-movement.log`). Each movement suite ends with
  `MOVEMENT_DONE FAILURES 0`.
- Native prerequisites and `git diff --check` pass. No gameplay or engine
  code was changed for this rerun. Manual exploration of every map remains open.

The production dedicated-loopback smoke passes `SMOKE_DONE FAILURES 0`
(`smoke.log`); the dedicated server was stopped after the test. Restart the
client to reload the installed packages and discard cached collision models.

## Safehouse ladders and upper-window access (2026-10-08)

Source Safehouse contains three ladder-content brushes covering its two
aluminium ladders. The converter previously exported neither ladder material
nor equivalent traversal behavior. It now extracts playable ladder brush
bounds, adds hull-contact and upper-exit clearance, and emits one-unit-grid
ladder materials. No solid geometry is added. TDM forward input ascends without
jumping or requiring an upward view; backward descends and strafe is retained.
Vertical ascent avoids roof overhangs; forward movement resumes near the upper
material boundary. Pitch-controlled original-profile behavior is preserved.

The reviewed House window frame models (`windowframe_54x76.mdl` and
`windowframe_54x44.mdl`) now use four closed collision volumes around their
openings. Their footprints and height variants are checked, and unexpected
geometry or budgets below 48 triangles retain the original collision. This
prevents trim decimation from obstructing the window hole while keeping its
posts, sill and lintel. Render meshes are unchanged.

The TDM preset reduces player and bot scale from 1 to 0.8. Total standing height
is 17.12 rather than 21.4 world units; radius is 3.4 rather than 4.25. Low crouch
uses 48% eye height in CSGOpen movement (total height 8.634), with the existing
automatic headroom checks. Original movement retains the 70% ratio. Step and
climb settings are adjusted to 8.75/16.25, preserving effective 7/13-unit
clearance after actor scaling. Weight and jump trajectory also change with
scale; actual map routes are tested below.

Artifacts are in `.csgopen/safehouse-access-20261008/`. Executed checks:

- `unit.log`: all 25 BSP tests pass, including ladder triggers and unchanged
  solid collision. `props-unit.log`: all 13 Blender tests pass, including frame
  apertures, triangle budgets and unknown-model fallbacks.
- The full production prop exporter decodes all models successfully and reduces
  prop collision from 462,290 to 458,286 triangles. There are 38 collision
  carriers rather than 40; the map is recompiled with the corresponding model
  registry, original 25 spawns and ladder materials.
- `safehouse-movement-final.log` passes seventeen cases: six full ladder-to-roof
  routes (both ladders at pitches -20, 0 and 20), six standing upper-window
  crossings (three central lanes in both directions), three jump-and-crouch
  approaches from the high part of the shed roof into the upper room, and two
  low-window crouch-clearance crossings. Ladder routes finish supported on the
  roof and outside ladder material. Every test uses actual converted collision;
  the upper sill remains an obstacle requiring the appropriate approach.
- `maps-final.log` passes all 49 loading, team, health, stair-height and settled
  spawn checks on the seven enabled maps. An earlier run caught stairheight
  4.1 when recompiling an existing profile. The converter now explicitly applies
  the intended stairheight after loading map configuration, including when the
  saved profile shadows generated CFG. Safehouse is recompiled and verified at 5.
- `agency-movement-final.log`, `dust2-movement-final.log` and
  `lake-movement-final.log` pass all 16, 32 and 20 existing traversal cases with
  the new dimensions. Each suite reports `MOVEMENT_DONE FAILURES 0`.
- `audit.json` verifies ZIP CRC, unchanged visible assets and world collision,
  and total collision 479,066 → 475,062 (4,004 fewer triangles). ZIP size is
  51,757,978 bytes versus 51,787,390 before. The original package is retained as
  `before.zip`; installed SHA-256 is
  `d42684748e51779ed775cb0c2f5ca4d273534dc262c3aaf4050a4f80abd8aa6d`.

Earlier exploratory failures remain in their logs, including blocked roof
transitions, insufficient frame clearance and an approach from the lower part
of the roof. The installed-package results above are the final checks. St. Marc
remains excluded for its previously documented spawn issue. Manual exploration
of every ladder entry angle and every window remains open.

The production dedicated-loopback smoke passes `SMOKE_DONE FAILURES 0` in
`smoke-verified.log`, including synchronized player/bot scale and effective
step/climb thresholds; the server was stopped after the test. The first fresh
smoke profile omitted the launcher's TDM `localinit.cfg` and failed five initial
utility-inventory checks (`smoke-final.log`). The verified rerun uses the same
TDM initialization as the established production smoke profile and retains every
inventory assertion. Native prerequisites and `git diff --check` pass. Restart
the client and any running dedicated server to load the updated binary, rules
and Safehouse package.

### First-person body visibility (2026-10-08)

The TDM client preset now sets `firstpersonmodel 1` and `firstpersoncamera 0`.
Inspection of `renderavatar()` confirms that this retains weapon/arms rendering
and omits the separate first-person body model that can enter the view on stairs.
World-player and shadow rendering remain separate. No movement, player dimensions,
map geometry or converter settings change in this fix.

The production client/dedicated-loopback smoke in
`.csgopen/firstperson-body-20261008/smoke.log` passes both new view-setting
assertions and reports `SMOKE_DONE FAILURES 0`. The test server was stopped.
Native prerequisites and `git diff --check` pass. This verifies runtime settings
and the renderer path; manual visual confirmation on Safehouse stairs remains
open. Relaunch the TDM client to apply the preset after persisted preferences.
