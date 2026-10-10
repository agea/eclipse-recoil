# Regole CSGOpen TDM v0.1

Dedicated-server match rotation is configured separately in
`config/csgopen/server-maps.cfg`: the first map comes from `sv_mainmaps`,
matches last 10 minutes without a score limit or overtime, results last
10 seconds, and voting lasts up to 20 seconds. The server chooses a random
map when nobody votes and normally excludes the most recent map. The
native development server distributes complete converted-map ZIPs over
loopback HTTP; the TDM client verifies and caches them before map loading.
This does not change the movement, weapons, or original gameplay profile.

During a match, the Vote Map/Mode panel also offers three random rotation
maps. With `sv_votestyle 3`, choosing a preview votes to end the current match
and load that map immediately. The same destination needs
`floor(connected humans / 2) + 1` votes, including spectators and excluding
bots. For example, two of three or three of four humans must agree. Players
can change or cancel their vote; a departure recalculates the majority.
At intermission, a fresh shortlist clears the earlier votes and the normal
20-second ballot still runs to completion.

Preset: `config/csgopen/tdm.cfg`. I nomi `sv_*` agiscono sull'autorità server;
le corrispondenti variabili senza prefisso sono sincronizzate con i client.
I valori sono un punto di partenza nelle unità di Red Eclipse, non valori CS:GO.

## Modalità e partita

Dichiarazioni: `src/game/vars.h`; selezione in `server::changemode`,
`server::chooseteam`, `server::setupspawns` (`src/game/server.cpp`),
`m_team`, `m_teamspawn` (`src/game/gamemode.h`), squadre in `player.h`.
`G_DEATHMATCH = 2`, senza mutatori (`0`), è già TDM: Alpha e Omega.
Non occorre un mutatore "team". `config/setup.cfg` definisce davvero
`tdm -> teamdm -> start -> mode; map`.

| Variabile server | Originale → prototipo | Significato e limiti |
| --- | --- | --- |
| `defaultmode` | 2 → 2 | indice modalità, G_START..G_MAX-1 |
| `defaultmuts` | 0 → 0 | maschera mutatori, 0..G_M_ALL |
| `rotatemode` | 1 → 0 | booleano: niente cambio casuale di modalità |
| `rotatemuts` | 3 → 0 | 0..VAR_MAX: niente mutatori casuali |
| `modelockfilter` | G_LIMIT → 1<<G_DEATHMATCH (4) | maschera modalità consentite senza privilegi, 0..G_ALL |
| `mutslockfilter` | G_M_FILTER → 0 | maschera mutatori consentiti senza privilegi, 0..G_M_ALL |
| `mutslockforce` | 0 → 0 | nessun mutatore imposto, 0..G_M_ALL |
| `waitforplayers` | 2 → 0 | enum 0..2; non attendere l'uscita degli altri dallo spectator |
| `botbalance` | -1 → 2 | -1..VAR_MAX; minimo totale di partecipanti, umani inclusi, non due bot aggiuntivi |
| `balancemaps` | -1 → 0 | -1..3; disattiva inversioni di squadre delle mappe asimmetriche |
| `defaultmap` (launcher) | stringa vuota → maps/echo | mappa iniziale; nome alternativo accettato dallo script |

La normale assegnazione/bilanciamento delle squadre resta upstream
(`teambalance = 6`). Un umano può iniziare con un bot avversario; per provare
friendly fire usare due client oppure `sv_botbalance 4` (un umano e tre bot,
con un bot alleato). I privilegi amministrativi consentono ancora
cambi intenzionali di modalità: il preset non è un sistema antimanomissione.

## Salute, danno e respawn

Dichiarazioni: `src/game/player.h` tramite macro `APVAR` in `playerdef.h`,
`vars.h` per fattori globali. Usi: `servstate::gethealth`, `sendspawn`,
`dodamage`, `calcdamage` e ramo regen di `server::checkclients` in `server.cpp`;
`clientstate::spawnstate`, `gameent::gethealth` in `game.h`.

| Variabile | Originale → prototipo | Unità e limiti |
| --- | --- | --- |
| `playerhealth`, `bothealth` | 1000 → 100 | punti interni reali; 1..VAR_MAX |
| `healthscale` | 1 → 1 | fattore adimensionale; 0..FVAR_MAX |
| `maxhealth` | 1.5 → 1 | fattore sul valore di spawn; 0..FVAR_MAX, **non** punti assoluti |
| `playerabilities`, `botabilities` | A_A_PLAYER/A_A_BOT (7679) → 7383 | 0..A_A_ALL; rimuove REGEN, MELEE, SECONDARY; conserva MOVE, JUMP, CROUCH, PRIMARY, AMMO e le altre capacità ordinarie |
| `playerteamdamage`, `botteamdamage` | A_T_PLAYER (7), A_T_AI (6) → A_T_PLAYER (7) per entrambi | maschera tipi di bersaglio alleati, 0..A_T_ALL; umani e bot possono danneggiarsi reciprocamente |
| `damageteamscale` | 0.5 → 1 | moltiplicatore, 0..FVAR_MAX; nessuna riduzione del danno tra alleati |
| `playerspawndelay`, `botspawndelay` | 5000 → 3000 | millisecondi; DEATHMILLIS (300)..VAR_MAX |
| `damagescale` | 1 → 0.1 | moltiplicatore, 0..FVAR_MAX; segue riduzione salute 1000→100 |

La regen richiede esplicitamente `A_A_REGEN` sul server, qui assente. Non si usa
un ritardo enorme o una modifica soltanto all'HUD. `regendelay=5000`,
`regentime=1000`, `regenhealth=50` restano originali ma non vengono eseguiti.
`server::isghost` e `physics::isghost` applicano teamdamage a danni e collisioni
con proiettili. Il friendly fire è ora attivo su richiesta dell'utente:
la maschera A_T_PLAYER include umani, bot ed enemy actor, senza A_T_GHOST.
Il fattore globale 1 conserva la scala normale delle armi, inclusi i loro
modificatori specifici `damageteam`. Questo sostituisce il requisito iniziale
di friendly fire disattivato; non richiede modifiche C++.

`m_delay` seleziona spawndelay normale per DM senza mutatori; server e client
usano lo stesso valore. Dopo morte, click primario/salto richiede il respawn;
il server lo concede al termine dei 3 secondi. Non è un respawn automatico
senza input. La protezione originale di spawn (3000 ms, interrotta sparando)
resta presente e deve essere considerata nei test di danno.

L'HUD upstream mostra la salute come percentuale del valore di spawn, quindi
100 iniziali; `damagedivisor` client passa da 10 a 1 per le cifre dell'obituary.
Il limite maxhealth è un tetto nei normali percorsi di danno/cura: non viene
aggiunto un nuovo sistema di armatura o cura.

## Movimento

Dichiarazioni: `vars.h`, capacità actor in `player.h`; usi in
`gameent::canimpulse` (`game.h`), `physics::impulseplayer`, `modifyinput`,
`modifyvelocity`, `movevelocity` (`physics.cpp`).

| Variabile | Originale → prototipo | Unità e limiti |
| --- | --- | --- |
| `playerimpulse` | IM_T_ALL (4095) → 1<<IM_T_JUMP (1) | maschera capacità, 0..IM_T_ALL |
| `botimpulse` | IM_T_MVAI (4095) → 1 | stessa maschera per bot |
| `movespeed` | 1 → 0.55 | fattore della velocità target, FVAR_NONZERO..FVAR_MAX |
| `moverun` | 1.25 → 1 | fattore durante corsa, stessi limiti |
| `movesprint` | 1.5 → 1 | fattore sprint, stessi limiti |
| `movestraight` | 1.2 → 1 | fattore movimento avanti/non strafe, stessi limiti |
| `movestrafe` | 1.1 → 1 | fattore strafe, stessi limiti |
| `moveaccelscale` (nuovo C++) | 1 → 0.75 | moltiplicatore del tasso di risposta a terra; FVAR_NONZERO..FVAR_MAX |
| `movebrakescale` (nuovo C++) | 1 → 1.25 | moltiplicatore del tasso di risposta senza input; stessi limiti; ridotto da 1.5 dopo il primo test manuale |
| `csgopenmovement` | 0 → 1 | abilita il superamento automatico degli ostacoli; booleano |
| `csgopenstepheight` | 7 → 8.75 | actor-scaled threshold; 7 world units with player/bot scale 0.8 |
| `csgopenclimbheight` | 13 → 16.25 | actor-scaled threshold; 13 world units with player/bot scale 0.8 |
| `csgopenclimbtime` | 450 → 450 | durata della salita; 100..2000 millisecondi |
| `movestepup`, `movestepdown` | 0.95, 1.15 → 1, 1 | nessun modificatore di velocità sui gradini |
| `impulsejump` | 1.5 → 1.1 | moltiplicatore del salto a terra |

`canimpulse` controlla la maschera prima dei costi/timer. Il normale salto a
terra richiede proprio IM_T_JUMP: azzerare l'intero sistema lo romperebbe.
Boost (incluso salto extra in aria), dash, slide, launch, melee impulse, kick
(walljump), grab, wallrun, vault e pound non sono consentiti. I bind restano
intatti. Resta la tolleranza originale di 125 ms quando si lascia il terreno;
non è un salto aggiuntivo dopo il primo. Il salto usa `impulsejump=1.1`;
`impulsespeed=75` e `movecrawl=0.6` restano upstream.

`movevelocity` calcola velocità in unità mondo/secondo, non unità Source:
`actor.speed * movescale * movespeed`, più modificatori di posizione/armi.
`playerspeed=100`, SMG portato `modspeed=-5`: normalmente circa 52.25 unità/s
nel preset prima di altri modificatori. Restano riduzioni mentre si spara,
in aria (0.75), acqua, gravità e inerzia originali.

Camminando contro un ostacolo si supera automaticamente la soglia bassa senza
perdere velocità orizzontale. Tra 7 e 13 unità si attiva una salita di 450 ms:
il giocatore alza il corpo, poi avanza sul bordo. Le soglie seguono la scala
dell’attore. La collisione del corpo deve trovare appoggio e spazio libero lungo
il percorso, anche sulle superfici importate invisibili: soffitti bassi e bordi
non raggiungibili restano bloccanti. La salita richiede appoggio a terra;
acqua, scale a pioli, piattaforme mobili e attori enemy conservano il movimento
ordinario. Le rampe e i gradini ravvicinati usano la soglia per ciascun bordo.

Grounded players and bots entering or following a walkable slope first try a
short tangent move with clearance and floor support. If it fails, the normal
ramp/ledge checks still apply. Walkable slope limits, obstacle heights and
collision meshes are unchanged. The check is gated by `csgopenmovement` and
does not apply in liquids, on ladders or to enemy actors. No terrain
subdivision or displacement LOD change is required.

When an immediate collision remains, the TDM profile also checks a supported
destination for the current horizontal displacement within the map stair
height (also capped by the configured actor step height).
This handles seams and nearby treads without relying on the farther ledge probe. The whole
body path must remain clear; player contacts, ceilings, unsupported landings,
liquids, ladders, moving platforms and airborne actors cannot use this recovery.
It preserves horizontal velocity and the existing walkable slope limit, and
adds no collision geometry. The original profile keeps the recovery disabled.

If the traversal probe rejects a small edge while supported by a flat floor,
the CSGOpen profile also tries the native step solver within the map stair
height before sliding to a stop. This handles seams between imported triangle
carriers; taller obstacles still require the normal climb and clearance checks.
The original profile keeps its existing solver path.

Durante l’arrampicata l’arma sparisce, salvo la pistola che resta visibile e
utilizzabile. Le altre armi non possono sparare o ricaricare. Cambio, raccolta e
rilascio di armi sono bloccati fino alla fine della salita e dell’estrazione:
non si può usare uno switch per aggirare il ritardo. Una volta saliti, l’arma
selezionata viene estratta con il proprio `delayswitch`. Con la pistola non si
applica un nuovo ritardo. Una granata già in cook e una ricarica in corso di
un’arma diversa dalla pistola impediscono l’inizio della salita. Morte/respawn
azzerano lo stato. Client e server sincronizzano salita, fine ed estrazione,
compresi gli snapshot per chi entra nella partita. Il protocollo è 283:
client e server devono essere aggiornati insieme.

Queste regole sono attivate dal preset TDM; `csgopenmovement=0` mantiene il
percorso di movimento originale. Il confronto nativo sul terreno piano con
un attore TDM misura l’apice del salto da 18.979 a 11.870 unità e il tempo in
aria da 825 a 680 ms; la sensazione con tastiera e mouse resta da valutare.
`gamespeed=100` è invariato.

La risposta originale usa lo stesso `floorcoast` per accelerazione e frenata:

```
r = pow(max(1 - 1/coast, 0), millis/20)
velocity = target*(1-r) + previous*r
```

L'unica modifica C++ al movimento moltiplica l'esponente per `moveaccelscale`
quando c'è input, oppure `movebrakescale` senza input, per actor a terra fuori
dai liquidi. Coefficienti 1 riproducono la formula precedente. Valori maggiori
convergono più rapidamente. Per coast=5, tempo per raggiungere il 90% della
velocità target: circa 206 ms originale, 275 ms con 0.75; frenata al 10% in
165 ms con 1.25 (prima 137 ms con 1.5). Le superfici possono modificare coast: i tempi non sono costanti
universali. Niente refactoring della collisione o dell'integrazione.

Le due variabili sono `GFVAR(IDF_GAMEMOD,...)`: entrano nel percorso di
sincronizzazione server/client esistente. Il movimento rimane simulato e
predetto dai client, incluso il proprietario dei bot; il dedicato upstream
non diventa autorità fisica né un nuovo anticheat.

## Armi

Dichiarazioni: `src/game/weapons.h` e macro `weapdef.h`; selezione/munizioni in
`clientstate::spawnstate`, `canuseweap`, `canreload` (`game.h`); restrizioni
server in `server::hasitem`, `chkloadweap`, eventi di uso/tiro (`server.cpp`).
La pistola è W_PISTOL=1; SMG W_SMG=4. W_RIFLE=8 è semiautomatico, non il
fucile automatico desiderato. Nessuna sostituzione di modelli o asset.

| Variabile | Originale → prototipo | Unità e limiti |
| --- | --- | --- |
| `playerweaponspawn`, `botweaponspawn` | W_PISTOL → W_PISTOL | indice arma, 0..W_MAX-1 |
| `playermaxcarry`, `botmaxcarry` | 2 → 1 | numero di armi loadout oltre alla pistola, 0..W_LOADOUT |
| `pistoldisabled`, `smgdisabled` | 0 → 0 | booleani 0..1 |
| `{claw,sword,shotgun,flamer,plasma,zapper,rifle,corroder,grenade,mine,rocket,minigun,jetsaw,eclipse,melee}disabled` | 0 → 1 | booleani 0..1, nessun pickup/loadout ammesso per queste armi |
| `{player,bot}spawngrenades`, `{player,bot}spawnmines` | 0 → 0 | enum 0..2, nessun extra alla comparsa |
| `spreeprize`, `spreemaxprize`, `spreebreakprize`, `revengeprize` | -1 → 0 | -1..W_PRIZES; nessun premio arena da serie di uccisioni |
| `janitorlimit` | 8 → 0 | numero AI janitor, 0..MAXAI; evita i loro premi arena |
| `kamikaze` | 1 → 0 | enum 0..3, nessuna esplosione di morte |
| `playerloadweap` (client) | stringa vuota → "4" | elenco di indici, parser `client::setloadweap` (`client.cpp`) |
| `showloadoutmenu` (client) | 0 → 0 | booleano 0..1, niente apertura automatica menu |
| `damagedivisor` (client) | 10 → 1 | divisore dell'obituary, FVAR_NONZERO..FVAR_MAX |

Il server non si fida della scelta del menu: tutte le armi loadout tranne SMG
sono disabilitate. `spawnstate` sostituisce scelte invalide con la sola arma
consentita. `playerloadweap` rende il vettore non vuoto, necessario per
`chkloadweap`; non è l'unica restrizione. Melee e fuoco SECONDARY sono rimossi
dalle capacità per evitare kick/claw e l'attacco alternativo SMG con proiettili adesivi esplosivi. La sola primary resta utilizzabile.

Pistol primary: semiauto, delayattack1=200 ms, proiettile a 2000 unità/s,
damage1=200 prima della scala (20 nel preset). SMG primary: fullauto1=1,
delayattack1=75 ms (~13.3 colpi/s), proiettile a 2500 unità/s, damage1=160
(16 nel preset), caricatore 40, ammospawn 120 (40+80), reload 1250 ms.
La pistola ha 10 colpi e ammostore=-1 (ricarica senza riserva finita).
L'SMG ha riserva finita per vita; la pistola resta disponibile e il respawn
rifornisce entrambe. Pickup SMG/pistola possono rifornire munizioni, ma non
sono necessari per avere l'equipaggiamento. Le altre armi non sono accessibili.

Rimangono dispersione, danni per parte del corpo, push/stun, traiettorie,
ricarica, animazioni, eventuale drill SMG e compensazione di latenza upstream.
Sono proiettili, **non hitscan**. Niente AK/M4, penetrazione Source, armatura
completa, rinculo fedele o nuovo sistema di rete in questa milestone.

### Precisione in movimento e crouch

Primary pistol/SMG: variabili `WPFVARM(IDF_GAMEMOD,...)` in `weapons.h`,
nomi prodotti da `weapdef.h`; tutte con limiti 0..FVAR_MAX e sincronizzazione
server/client. Il preset configura entrambi i tipi di actor tramite le stesse
proprietà delle armi, senza intervenire sul solo mirino.

| Suffisso variabile primary | Originale → preset | Significato |
| --- | --- | --- |
| `pistolspread1`, `smgspread1` | 0, 0 → 1, 2 | dispersione base nelle unità interne di offsetray |
| `{pistol,smg}spreadstill1` | 1 → 1 | moltiplicatore in piedi da fermo |
| `{pistol,smg}spreadrunning1` | 1 → 3 | moltiplicatore in corsa |
| `{pistol,smg}spreadsprinting1` | 1.2 → 3 | stesso valore anche per lo stato sprint upstream |
| `{pistol,smg}spreadmoving1` | 1 → 2 | camminata; in crouch viene moltiplicato anche per spreadcrouch |
| `{pistol,smg}spreadcrouch1` | 1 → 0.5 | crouch fermo; bonus applicato anche al movimento in crouch |
| `{pistol,smg}spreadinair1` | 0 → 2 | incremento additivo del moltiplicatore in aria, escluse scale |

La dispersione effettiva è `base * accmodspread`, limitata da `WSP`:
in piedi 1x, corsa 3x, crouch fermo 0.5x, crouch in movimento 1x. In aria
si aggiunge 2 al moltiplicatore. `spreadmin1=0`, `spreadmax1=0` rimangono
upstream (nessun limite aggiuntivo); `spreadz1` resta 2 per pistol, 1 per SMG.
Non sono gradi Source: `offsetray` usa `distanza * spread / 10000` per scalare
un offset casuale di raggio massimo 50, con ulteriore divisione verticale
per spreadz. Esempio: a distanza 1000 unità, SMG standing ha raggio massimo
10 unità, corsa 30, crouch fermo 5. Sono valori iniziali da collaudare.

Piccola correzione C++ in `weapons::accmodspread` (`weapons.cpp`):
`gameent::running()` (`game.h`) indica lo stile e risulta vero anche da fermo.
Il ramo di corsa ora richiede input move/strafe. Il ramo di movimento applica
inoltre il bonus crouch, invece di ignorarlo. I pesi upstream 1 conservano la
risposta originale di pistol/SMG nel profilo arena (base zero); il test della
funzione verifica anche equivalenza dei modificatori con i pesi originali.

`weapons::shoot` chiama questa funzione e `offsetray` prima di `projs::shootv`:
la traiettoria cambia realmente. L'HUD usa la stessa funzione per il feedback.
Il server sincronizza i parametri, valida stato/munizioni e inoltra le shot
positions ricevute (`N_SHOOT`, `shotevent::process`); non ricalcola il sorteggio
della dispersione. Resta il modello di fiducia upstream, senza nuovo anticheat.
La selezione usa input e stato crouch, non la velocità residua: rilasciare i
tasti ripristina subito la precisione da fermo anche durante la frenata.
Rinculo, danno, rate of fire e munizioni non vengono ritoccati.

### Dispersione progressiva della raffica

Richiesta del 1 ottobre 2026. Non esisteva un accumulo di dispersione basato
sui colpi: `weapshot` indica munizioni del singolo tiro e `weaptime` cambia
anche durante reload/switch. Aggiunto stato separato per arma in `clientstate`
(`game.h`): `weapbloom` e `weapbloomtime`, inizializzati nel costruttore e
azzerati da `weapreset`, inclusi morte e spawn. Nessuna modifica al protocollo.

| Variabile GFVAR/GVAR IDF_GAMEMOD (`vars.h`) | Default → preset | Unità e limiti |
| --- | --- | --- |
| `spreadburstadd` | 0 → 0.35 | incremento adimensionale per colpo primary, 0..FVAR_MAX; 0 disabilita l'accumulo nel profilo originale |
| `spreadburstmax` | 1.5 → 1.5 | limite dell'incremento del moltiplicatore, 0..FVAR_MAX |
| `spreadburstrecovery` | 1200 → 1200 | ms per recuperare dal limite a zero, 1..VAR_MAX |

`getweapbloom` calcola `max(0, valore - limite * tempo_trascorso / recovery)`
senza mutare lo stato durante il disegno dell'HUD. `addweapbloom` applica
prima il recupero, poi l'incremento, con clamp al limite. `accmodspread`
moltiplica il valore di postura/aria per `1 + accumulo`. In `weapons::shoot`,
l'incremento avviene dopo il calcolo della traiettoria del colpo, soltanto
per primary con dispersione base positiva e dopo i controlli canshoot/munizioni.
Primo colpo preciso; tentativi a vuoto o durante reload non accumulano.
Gli alt-fire non accumulano né usano bloom.

Il limite 1.5 consente fino a 2.5x la dispersione della postura corrente;
tra colpi interviene il recupero, perciò la raffica SMG a 75 ms raggiunge
un incremento effettivo pre-colpo di circa 1.406 (2.406x). Il bonus crouch
rimane moltiplicativo. A limite pieno, 600 ms recuperano metà accumulo e
1200 ms lo azzerano. Cambiare arma non cancella il suo storico; il tempo
continua a farlo decadere. La ricarica SMG di 1250 ms normalmente permette
il recupero completo, senza reset immediato quando si preme reload.

Le impostazioni sono sincronizzate e preservate da savevars. Anche i bot
gestiti dal client usano questo percorso di tiro. Lo stato bloom è calcolato
dal client proprietario; come già per spread/shot positions, il server non
ricalcola il cono né introduce nuovi controlli anticheat. Per diagnosi esiste
`getclientweapbloom <client> <indice-arma>` in `client.cpp`, che restituisce
l'accumulo decaduto, non il moltiplicatore finale.

## Applicazione e persistenza

`engine::rehash` (`src/engine/server.cpp`) esegue `localinit.cfg` per client
locale, `servinit.cfg` per dedicato, con EXEC_VERSION. I profili generati
eseguono lì `tdm.cfg`, prima delle configurazioni client e prima dei socket
del dedicato. `autoexec.cfg` applica invece solo `client.cfg` dopo i defaults.
Alla fine del preset `sv_savevars` salva i default server non IDF_MAP.
`cleanup/resetgamevars` ripristinano questi default di sessione, non quelli
arena; nessun cambiamento ai default binari originali.

Le regole del preset sono IDF_GAMEMOD, non IDF_MAP: i file di livello non le
possono sovrascrivere e N_GAMEINFO importa solo variabili IDF_MAP. Salute,
armi, impulse e i nuovi coefficienti restano validi a ogni `spawnstate`.
I parametri ambientali di mappa (gravità, coast, materiali, hurt) restano tali;
su una nuova mappa vanno verificati. Il preset non promette uguali percorsi
su mappe pensate per parkour. Le rotazioni automatiche non aggiungono mutatori.

Profili in `.csgopen/original`, `.csgopen/csgopen-client`, `.csgopen/server`.
Passare al gameplay originale significa uscire e usare `dev.sh original`;
non tentare di ripristinare la sessione TDM con `resetvars`, che mantiene
volutamente i suoi default salvati.

## Mappa e collegamento locale

`bath` non è presente. `echo` è nel submodule maps a
`a77d20d1b03820b4ae6242ec79d4d3fd79e6fba3`; `echo.txt` documenta la derivazione
da Cube 2 e `echo.cfg` descrive il cortile del laboratorio. Sono presenti
spawn per Alpha/Omega oltre ai neutrali, su più quote. Nessun asset modificato.
I percorsi ordinari a terra sono la zona di prova; la percorribilità completa
senza parkour deve ancora essere confermata manualmente.

Il server usa serverip=127.0.0.1, serverlanport=0, servermaster="",
masterserver=0 e httpserver=0 (il dedicato upstream abilita HTTP di default).
`serveroption`/`setupserversockets` in `engine/server.cpp` riconoscono
`-si127.0.0.1`, `-sm`, `-ss1`, `-sp28801`. La porta info è quella di gioco+1.
La configurazione viene letta prima dell'apertura dei socket.

`engine/client.cpp::connectserv` ora esclude solo il nome letterale
`127.0.0.1` dal prompt delle linee guida del master. `doc/guidelines.txt`
esclude già il gioco offline e server scollegati dal master. Non si imposta
`connectguidelines` e gli altri indirizzi conservano il controllo upstream.
Usare il literal indicato anche al posto di `localhost` per questa prova.

## Indicatore di dispersione

`clipspread 1` nel profilo client CSGOpen collega il raggio del cerchio delle
munizioni alla dispersione primaria corrente: stessa `accmodspread` e `WSP`
del tiro, inclusi postura, penalità in aria e accumulo decaduto della raffica.
La scala è `clamp(sqrt(spread / 2), 0.65, 2.5)` rispetto al raggio upstream: la
SMG ferma è il riferimento. È indicativa, non un confine dei punti di impatto.
Il numero di glifi resta quello delle munizioni, con dimensione leggibile e
animazioni upstream; anche le animazioni di ricarica usano il raggio corrente.
Default binario 0 e anteprime invariate.

### Accumulo della pistola

Il preset imposta `sv_pistolspreadburstscale 2`: incremento 0.7 per colpo
contro 0.35 della SMG, con stesso limite 1.5 e recupero 1200 ms. Alla cadenza
minima della pistola (200 ms) il precedente incremento recuperava già 0.25
tra i colpi; a 280 ms tornava completamente a zero. Il nuovo valore permette
accumulo anche a 300–400 ms, preservando primo colpo, crouch e SMG.
Default del moltiplicatore 1; spreadburstadd 0 mantiene disattivata la funzione.

## Riferimento Desert Eagle / PP-Bizon — prima fase

Fonte: foglio gid=0 indicato dall'utente, righe 2 e 23, acquisito il
1 ottobre 2026. Snapshot delle due righe in `config/csgopen/weapon-reference.json`.
Danno motore 530/270 con damagescale 0.1 e damagetorso1=1: 53/27 HP.
Moltiplicatore testa 3.9/4; intervallo arrotondato da 60000/RPM: 225/80 ms.
Caricatori 7/64, riserve finite 21/128 e munizioni totali spawn 28/192.
`ammoadd` riempie un caricatore per ricarica e `ammoitem` assegna un caricatore
al pickup. La pistola resta semiautomatica, la SMG automatica.
Su 100 HP, senza protezione spawn, modificatori o armatura: teoricamente
2/4 colpi torso e 1 colpo testa per entrambe a danno pieno.

Non si copiano le unità Source nei parametri di Red Eclipse: dispersione,
bloom e movimento restano alla taratura precedente. Mancano conversione
inaccuracy/recoil, recupero distinto postura/arma, tagging, mobilità per arma,
falloff esponenziale, armatura e penetrazione. Durata ricarica non presente
nel foglio: resta upstream (pistola 1000 ms, SMG 1250 ms). Moltiplicatori arti
upstream conservati; nessun moltiplicatore CS:GO agli arti inventato dalla fonte.

## Arsenale esteso

`arsenal.cfg` viene eseguito alla fine di tdm.cfg, prima di savevars.
Slot Zapper→AK-47, Rifle→AWP, Plasma→MP9, Shotgun→XM1014, Minigun→M249;
SMG→Bizon e Pistol→Desert Eagle conservati. Fonte salvata in weapon-reference.json.
Danno/cadenza/munizioni/raggi tradotti dal foglio; headshot 4x per le nuove armi.
Scelte del loadout visibili nel menu, una primaria più pistola. Flag server
`csgopenweapons` default 0: estende parser/loadout casuale alla Minigun e limita
il secondario a Rifle tramite canshoot condiviso client/server. Anche i pickup
Minigun non devono introdurre una primaria non assegnata nel TDM.

AWP usa cooked2=ZOOM|KEEP e cooktime2=1 ms per evitare la divisione per zero
del percorso zoom upstream senza carica percepibile. Sparo scoped allineato
a danno, cadenza e ammo dello sparo primario. Collisione primaria 241:
TRACE|OWNER|IMPACT_GEOM|IMPACT_PLAYER|IMPACT_SHOTS. Niente rimbalzi, splash,
status residui o frammenti sulle nuove armi. Projectile speed 10000 è un
valore di prototipo, non hitscan. Spread provvisorio; recoil, durata ricarica
e rappresentazione grafica originali. XM1014 ha 6 pellet da 20 HP ma nessun
falloff CS:GO ancora: bilanciamento a distanza da completare.

Test arsenale separato esamina ogni scelta al respawn e le autorizzazioni
primaria/secondaria, poi esegue il ciclo smoke esistente. Menu e mira/zoom
con input fisico richiedono la verifica manuale.

### Salvataggio loadout CSGOpen

La scelta della primaria nel menu viene applicata subito a playerloadweap e
vale al prossimo spawn. La validazione considera solo la primaria; lo slot
secondario nascosto non deve invalidare un loadout con pistola fissa.
I callback delle opzioni sono literal per evitare dipendenza da variabili
del loop durante la compilazione delle macro UI. client.cfg conserva la scelta
anziché reimpostare SMG a ogni riavvio. Il test arsenale usa ora gli stessi
setter/validator/Save del menu con filtro casuale vuoto, non solo playerloadweap.

## Proiettili convenzionali senza rimbalzo

Tutte le sette armi abilitate impostano collide1=241 (TRACE|OWNER|IMPACT_GEOM|
IMPACT_PLAYER|IMPACT_SHOTS), senza BOUNCE, DRILL o STICK. Vale anche per
riflecollide2 scoped. Anche SMG e pistola sono configurate esplicitamente.
Effetti uniformi: fxtype=3 (MUZZLE4/Bizon), fxtypeproj=0 (BULLET), power=-1;
colore/scala uguali alla SMG. Scie, impatti e lampi energetici eliminati anche
per AWP scoped. In projs.cpp solo con csgopenweapons, Plasma/Zapper/Rifle
usano il suono primario SMG; Zapper non aggiunge il transit energetico o il
loop audio originale. Modelli delle armi e asset non modificati.
Gli effetti originali restano attivi nel profilo originale (flag 0).
I bossoli possono ancora rimbalzare: sono oggetti decorativi, non colpi.

Su richiesta dell'utente, Shotgun e Minigun conservano nuovamente i loro
effetti convenzionali originali: Shotgun MUZZLE2/PELLET, colore 0xF0F020;
Minigun MUZZLE4/BULLET, colore 0xFF4C10. Scala 1 per entrambe. Collisione
241 senza rimbalzo conservata, così come taratura XM1014/M249 e suoni originali.

## HE con cook

`he.cfg` dopo arsenal.cfg prima di savevars: una HE separata per umano/bot
a ogni respawn, clip 1 e riserva 0; mine ora separate. Bind client G: weapon
W_GRENADE 1 (indice diretto, non slot numerico). Tasto primario innesca,
rilascio lancia; cooktime1=time1=3000 e cooked1=LIFEN (8) mantengono la
miccia residua upstream. Nessuna scalatura di danno o velocità col cook.

A scale=1, shootv crea un proiettile con vita 1 ms al centro del proprietario,
velocità/inertia/falling zero e escaped=true, per esplodere lì attraverso
il percorso normale e registrare consumo/danni. Non viene lanciato avanti.
Guardia cookinghe condivisa vieta cambio, drop e pickup durante W_S_POWER.
Se ucciso con la HE innescata, dropitems lascia cadere una granata fisica
con la miccia residua calcolata dal server. La morte non anticipa la detonazione
e non riavvia il timer. Il profilo originale non applica queste modifiche.

Collisione 920: BOUNCE_GEOM|BOUNCE_PLAYER|COLLIDE_OWNER|COLLIDE_PROJ|IMPACT_SHOTS.
La HE è colpibile: un proiettile la fa detonare subito, in volo o a terra.
Rimbalza su geometria/player; niente stick o detonazione al contatto con essi. Radial 72 unità motore, danno1800
con scala .1, moltiplicatori torso/testa/arti/self/team1; attenuazione con
la distanza upstream. Residual0, fragweap-1: niente burn o schegge.
Timer 3 secondi e danno base180 sono valori iniziali di prototipo, non
conversioni dal foglio delle armi. HE non inclusa nel loadout casuale primario.


## Smoke fumogena

Slot W_CORRODER riutilizzato, he.cfg invariata; smoke-grenade.cfg viene eseguito
prima di savevars. Una smoke 1+0 per umano/bot, H per selezione. Cook 8,
fuse/time 3000 ms, bounce 784, velocità 250, niente stick/proximity.
Danno/radial/residual 0, fragweap -1, fxtypeproj -1: niente esplosione energetica.
A miccia completa la smoke si apre in mano senza danno. Switch/drop/pickup
bloccati durante cook, indipendentemente dalla HE. La morte durante cook
lascia cadere la smoke innescata: la nube si apre alla scadenza della miccia
residua. Una nube già emessa sopravvive al proprietario.

projs::destroy sul proiettile Mine del preset crea una smokecloud su ogni
client usando il percorso nativo dei proiettili e la notifica N_DESTROY.
Nube a raggio 68, durata sincronizzata 18000 ms, crescita 1000 ms e fade
finale 2000 ms. Reset mappa cancella le nubi. Particelle grigie senza asset
nuovi e overlay HUD opaco dall'interno (transizione 8 unità dal bordo).
AI cansee verifica l'intersezione segmento-sfera solo quando densità >= .5;
memoria bersaglio upstream preservata. Non blocca proiettili né movimento.
Prototipo sferico, senza clipping ai muri/volume stanza; visibilità esterna
basata su particelle, da valutare manualmente. Profilo originale invariato.

Resa esterna: PART_SMOKE_LERP al posto del fumo additivo, 48 particelle
su tre strati più un centro, emissione ogni 100 ms e vita 600 ms.
L’alpha blending copre le sagome invece di schiarire lo sfondo.

Visibilità: niente halo dei player nel preset, anche fuori dal fumo.
Render modello/attachment ed effetti player saltato se segmento camera-centro
attraversa smoke densa, senza distinzione di squadra. Label/UI e radar richiedono
anche raycubelos (nessun muro). Profilo originale invariato. La soglia .5
segue l’AI; ai bordi il modello intero appare/scompare, limite del prototipo.

Etichette: entityitemui/entityprojui -1 nascondono pickup e loot a terra.
Player e playeroverlay nel preset ammessi solo per compagni (squadra non
neutrale), sempre con visibilità attraverso muri/smoke verificata.


## Mina circolare e migrazione smoke

Smoke spostata da W_MINE a W_CORRODER, spawn condiviso CSGOpen separato
per umani/bot, esclusa dal loadout primario. Modelli/animazioni Grenade tramite
weaponvisual, fisica primaria copiata dalla granata, tinta grigia contro HE
arancione. H resta smoke, J seleziona Mine, Rocket disabilitato e riservato.

proximity-mine.cfg: una mina 1+0 a spawn, lancio corto speed80, senza cook,
collide16568 (STICK_GEOM|IMPACT_GEOM|IMPACT_SHOTS|COLLIDE_PROJ|COLLIDE_OWNER).
Attacca a geometria, non ai player. Rilevamento sferico 32 unità, armamento
1500 ms da stick e detonazione 100 ms dopo innesco. minetrigger verifica
alive, proprietario escluso, stessa squadra esclusa, distanza, timer e
raycubelos. Protezione spawn/ghost resta nel percorso physics::issolid.
Danno1800 con scala.1, radial64, self/team1; residual0, frag-1; FX Grenade
su modello Mine. Durata60000 ms, scadenza esplosiva upstream, reset mappa.
Il proprietario può morire senza cancellare le mine già piazzate.


## Lanciagranate HE

Rocket abilitato e selezionabile come arma primaria, senza assegnazione automatica. K seleziona,
clip1/store6/ammospawn7, reload1800 ms. Cook di 3 secondi senza guidance, proiettile
Grenade arancione ma arma Rocket. Speed650 contro HE250, fisica da Grenade;
fuse3000, damage1800, radial72, collide920, residual0/frag-1 come HE.
Le munizioni del lanciagranate sono separate dai quattro slot delle utility. Config grenade-launcher.cfg prima di savevars.

Il lanciagranate ora usa cook LIFEN come la HE, con esplosione in mano al
termine e blocco cambio/drop/pickup. Impatto diretto: 25 HP per bersaglio
una sola volta per granata, separato dal danno esplosivo; friendly fire
applicato normalmente. Rinculo verticale 0.1–0.2, orizzontale zero, kickpush5 anziché300.


## Loadout con accessorio esclusivo

Menu (,): una primaria tra Shotgun, SMG, Plasma, Zapper, Rifle, Rocket e
Minigun; Deagle fissa. Secondaria facoltativa Bizon/MP9 oppure quattro slot
HE/Corroder smoke/Mine, inclusi slot vuoti e duplicati. La stessa SMG non può
occupare primaria e secondaria. Slot salvati subito, assegnati al respawn.

playerloadweap e loadweap mantengono sei posizioni: primaria, secondaria,
quattro utility. Usano il messaggio player-info esistente, senza nuovi campi
wire. Nel preset il parser conserva zeri e duplicati e limita la richiesta a
sei voci. spawnstate condiviso convalida tipi, disabilitazioni e priorità:
una secondaria SMG valida esclude tutte le utility, anche se richieste dal
client. Primaria non valida torna a Bizon; utility non valide/oltre i quattro
slot sono ignorate. Profili legacy e bot senza selezione ricevono una HE,
una smoke e una mina. Original Red Eclipse conserva il vecchio parser/spawn.

Quantità utility in clip (cap4, store0), un consumo per lancio, senza ricarica.
Il conteggio del tipo selezionato è già mostrato dall'HUD munizioni. Pickup
utility e armi nuove bloccati nel preset per non aggirare la scelta esclusiva;
restano ammessi i rifornimenti di munizioni delle armi già possedute. Il menu
usa callback per slot, salva playerloadweap e svuota le utility scegliendo SMG;
un tipo granata svuota la secondaria. Rocket conserva 1+6 colpi come primaria.

Supported step recovery accepts the vertical velocity induced by walking up the
current floor slope. Upward impulses above that component still disable recovery,
so jumping does not acquire extra supported steps.


### Converted-map player dimensions and ladders (2026-10-08)

The TDM preset sets both player and bot scale to 0.8. Standing total collision
height is 17.12 world units (eye height 16.32), with radius 3.4. Low crouch uses
48% of eye height in CSGOpen movement, giving total height 8.634; the original
profile retains its 70% low-crouch ratio and default actor scale. Automatic
crouch still uses the existing clearance checks. Step and climb settings are
compensated for actor scale, preserving the previously tested effective heights
of 7 and 13 world units. Actor scale also affects weight and jump trajectory;
the movement suite verifies actual converted-map routes after the change.

Source ladder brushes are converted into localized ladder materials. Holding
forward climbs even with a downward view; backward descends and strafe remains
available. Most of the ascent is vertical to avoid roof overhangs; horizontal
forward motion resumes near the upper material boundary. Original movement
retains pitch-controlled ladder behavior. Safehouse's upper room can be entered
from the high part of the shed roof with a jump and crouch; the sill remains a
real obstacle. The converter retains the visible windows and uses four simple
collision volumes for the reviewed House frame models to preserve their holes.

### First-person presentation on stairs (2026-10-08)

The TDM client preset uses `firstpersonmodel 1` and `firstpersoncamera 0`:
weapon/arms remain visible, while the separate first-person body is omitted.
This prevents leg animations from obscuring the view on stairs after the
converted-map dimension changes. The option affects local rendering only;
actor dimensions, movement, collision, third-person player models and world
shadows remain unchanged. The original gameplay profile retains its defaults.

### Fast projectile trail visibility (2026-10-09)

The TDM client enables `csgopenbulletfx`, a local effect-definition switch that
reloads effects and remains active when effect detail is changed. Bullet and
shotgun pellet trails have no initial opacity ramp in this profile: the upstream
50/100 ms ramps can outlast nearby shots travelling at 10,000 units/second.
Bullet particles last 50 ms with width 0.15 and blend 0.85; pellet particles
last 20 ms with width 0.1 and blend 0.5. The initial wider revision was too
prominent, while the subsequent 20/8 ms revision was too faint. This changes existing
particles, without adding emitters. Original
profiles retain upstream effect values. The converted AK-47 (Plasma slot) also
sets its visual trail length to 12 instead of its inherited zero, preventing
the flare endpoints from collapsing. Other conventional shots, including scoped
AWP, also use length 12 instead of inherited energy-beam lengths. Projectile
speed, collision, damage and
the first-person weapon-only view are unchanged.

Effect definitions have a revision counter. Projectile and muzzle caches refresh
when this counter changes, including after `reloadfx` and effect-detail changes.
Previously they retained numeric indices into the old definition table, so a
valid-looking handle could identify an unrelated effect and lose bullet trails
or impact stains. Cache refresh runs once per revision, rather than looking up
names on every shot.

Dedicated configuration uses explicit `fxscale 1` and bullet colour `0xFF9C10`.
The former `$smgcolour` and `$smgfxscale1` lookups only existed in the client;
a standalone server interpreted them as zero and synchronized zero scale to
players. Both particle size and impact stain radius were therefore zero. This
also explains why local firing verification could succeed while LAN firing
remained invisible. Explicit values repair profiles previously saved with zero
scale. The multiplayer smoke asserts all eight scales and six shared colours.

### Bot opt-in (2026-10-09)

The TDM preset sets `sv_botbalance 0` and `sv_botoffset 0`: offline and dedicated
matches do not automatically add bots. Both dedicated launchers load this
preset. An administrator may explicitly set `sv_botbalance 2` after loading it
to fill to two participants, or use `/botbalance 2` from an authorized client.
The bot limit and existing bot behavior remain available. Preset initialization
reapplies the default on restart; persistent bot-enabled deployments should
place their override after the preset in their server startup configuration.

Offline Match adds a persistent **Number of bots** slider (0–32) to the TDM
settings. Pressing Begin applies `csgopenbotcount` as an exact AI count,
excluding the human player and capped by `botlimit`. This bypasses automatic
participant/team rounding, so four bots plus one human remain five players.
Teams still use the existing assignment logic. Zero removes bots. The override
defaults to -1, preserving normal balancing, and is ignored with remote
clients, original rules, co-op or duel/survivor mutators. Other modes reset it
to -1 when starting through the menu. Existing Bot skill controls set difficulty.


### Fall damage

The CSGOpen TDM preset enables `sv_csgopenfalldamage 1` for humans and bots.
The original profile defaults to zero. The server synchronizes the enable flag,
`sv_csgopenfallspeed` (160 world units/second in TDM) and `sv_csgopenfallscale` (1 health
point per excess world unit/second). These are prototype values, not a claim
of matching Counter-Strike's damage curve.

On transition from falling/sliding to a supported floor or walkable slope, the
actor's owning client reports its downward vertical speed before collision,
rounded up to the network's integer velocity unit. Horizontal speed is ignored.
The server queues a timed event, checks ownership, live state, actor type,
spawn time, duplicate timestamps, climb state and speed bounds, then applies
`ceil(max(speed - safe_speed, 0) * scale)` health damage through the normal
damage/death messages. Weapon `damagescale` and `damageself` do not reduce or
disable environmental fall damage. Impact speed remains client reported, as
with the existing client physics events; this is not server-side collision
reconstruction or an anti-cheat system.

At the TDM settings, speed 160 is harmless, 210 costs 50 health and 260
costs 100 health. The safe threshold was raised from 100 after a low-wall drop
cost 15 health; that impact is now harmless. Natural movement may increase a
seeded speed during its final physics step. Ground jumps and small steps stay
below the threshold. Water or
lava at at least half submersion suppresses this impact damage; existing lava
and material damage remain active. Ladder attachment, floating, prediction of
remote actors and automatic climbing do not send impact events. Each landing
transition reports at most once, including walkable slopes. Fatal impacts use
a fall obituary and the ordinary death/respawn path. Crossing the map's death
plane retains its existing immediate death behavior.

Protocol 284 adds `SPHY_FALL` and `HIT_FALL`. Rebuild and restart clients and
servers together; no map regeneration is required.


### Armed grenades dropped on death

In CSGOpen, `dropitems` releases a held, armed HE (`W_GRENADE`), smoke
(`W_CORRODER`) or launcher round (`W_ROCKET`) before clearing the inventory.
The same release applies when an alive holder is sent to waiting/spectator
through an inventory-drop/reset path. Unarmed inventory does not activate.

The server derives the remaining projectile lifetime from the weapon's cook
start and existing LIFEN rule, clamps an expired fuse to one millisecond,
consumes exactly one round and registers its projectile for ordinary explosion
damage. A server-only `SPHY_PRIMEDDROP` message creates the projectile on every
client before the death message. Each release has a separate negative ID,
retained across respawn, to distinguish overlapping death drops from normal
positive shot IDs. Late cook/shot events cannot duplicate the released round.

The projectile starts at the holder's center with their current movement
velocity and no forward throw. It retains normal gravity, bounce, collision,
blast damage or smoke deployment. The owning client keeps simulating it after
death. The timer is neither restarted nor shortened by death. Existing HE
bullet-triggered detonation remains active. A grenade held through the full
fuse while alive retains the existing in-hand detonation. Ordinary upstream
kamikaze behavior remains available in the original profile.

Protocol 285 adds the server-only drop event; update and restart clients and
servers together. No converted-map packages need regeneration.


### No map or player loot

`sv_csgopennoloot 1` is enabled by the TDM preset and synchronized to clients.
The original profile defaults to zero. The server's item eligibility check
rejects every map weapon/ammunition pickup and despawns previously active map
items during its next entity update. Shared use/drop checks and the server
pickup handler reject map/dropped-item use and manual equipment drops.
Inventory and prize drops cannot create loot on death or inventory reset.
This applies to humans and bots on both native and converted maps.

Client item eligibility hides map pickups in gameplay while retaining editor
access. Any existing dropped-inventory model is hidden when the rule is enabled.
Respawn loadouts, reserve ammunition and normal reloads are unchanged. The armed
grenade release runs independently before ordinary inventory-drop suppression:
HE, smoke and launcher rounds already in cook still fall and complete their fuse.
They are live projectiles, never collectible equipment.

Rebuild/update and restart clients and servers to use the rule; no map editing
or conversion is necessary. The variable uses existing synchronization and does
not change protocol 285.

### Optional TDM soldier appearance (2026-10-09)

`csgopensoldiers` is a local, non-persistent client setting, defaulting to zero.
The TDM client enables it when the locally generated Urban Terror soldier ZIP
is installed. With `csgopenweapons` active, humans and bots use Orion/Athena
according to their body choice, blue SWAT for Alpha and sand uniforms for
Omega. Neutral player previews use the Alpha uniform. Other actor types and
the original gameplay profile retain their upstream models.

The adapter preserves vertex animations, supplies complete helmets and faces,
and retains the animated weapon attachment basis. Both source and native
third-person weapons point along local +X; the MD3 loader's Y reflection and
the body's yaw offset handle the actor orientation without another tag rotation.
Each body has two reduced distance
LODs. Authored texture colors are retained without player tint or mixer
patterns. Cosmetic attachments designed for the upstream skeleton are omitted;
soldiers use an authored MD3 death animation instead of an IQM ragdoll.
Strafing reuses the source forward walk/run clips. First-person arms and
weapon models remain upstream assets.

This is a client presentation option. Actor dimensions, equipment, movement
rules, damage values, map assets and protocol 285 are unchanged. Missing or
disabled soldier models fall back to upstream characters. The ZIP is local
and excluded from releases; see the import and attribution instructions in
the development README.
