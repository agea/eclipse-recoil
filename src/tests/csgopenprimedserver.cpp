// Opt-in dedicated integration server, replacing game/server-standalone.o.
#include "../game/server.cpp"

namespace primedtest
{
    int failures = 0;

    void check(bool ok, const char *name)
    {
        if(!ok) failures++;
        logoutf("PRIMED_CHECK_%s %s", ok ? "PASS" : "FAIL", name);
    }

    void runchecks()
    {
        using namespace server;
        failures = 0;
        int clock = gamemillis;
        gamemillis = 2000;
        const int weapons[] = { W_GRENADE, W_CORRODER, W_ROCKET };
        loopi(3)
        {
            clientinfo ci;
            ci.actortype = i == 1 ? A_BOT : A_PLAYER;
            ci.state = CS_ALIVE;
            ci.weapselect = weapons[i];
            ci.weapammo[ci.weapselect][W_A_CLIP] = 4;
            ci.setweapstate(ci.weapselect, W_S_POWER, 3000, 1000);
            check(ci.primedfuse(gamemillis) == 2000, "fuse_excludes_time_already_held");
            dropitems(&ci, DROP_DEATH);
            check(ci.weapshots[weapons[i]][0].find(-1), "death_authorizes_original_weapon_projectile");
            check(!ci.weapshots[W_GRENADE][0].find(1), "death_has_no_instant_kamikaze_explosion");
            check(ci.weapammo[weapons[i]][W_A_CLIP] == 3, "death_consumes_one_armed_round");
            check(!dropprimed(&ci) && ci.weapshots[weapons[i]][0].projs.length() == 1, "armed_round_drops_once");
            ci.state = CS_DEAD;
            shotevent shot;
            shot.weap = weapons[i];
            shot.process(&ci);
            cookevent cook;
            cook.weap = weapons[i];
            cook.process(&ci);
            check(ci.weapammo[weapons[i]][W_A_CLIP] == 3 && ci.weapstate[weapons[i]] == W_S_IDLE,
                "late_shot_and_cook_cannot_duplicate_death_drop");
            ci.respawn(gamemillis);
            check(ci.weapshots[weapons[i]][0].find(-1), "death_projectile_survives_owner_respawn");
            ci.state = CS_ALIVE;
            ci.weapselect = weapons[i];
            ci.weapammo[weapons[i]][W_A_CLIP] = 4;
            ci.setweapstate(weapons[i], W_S_POWER, 3000, 1000);
            check(dropprimed(&ci) && ci.weapshots[weapons[i]][0].find(-2), "overlapping_death_drops_have_unique_ids");
        }
        clientinfo ci;
        ci.actortype = A_PLAYER;
        ci.state = CS_ALIVE;
        ci.weapselect = W_GRENADE;
        ci.weapammo[W_GRENADE][W_A_CLIP] = 1;
        check(!dropprimed(&ci), "unarmed_grenade_is_not_activated");
        ci.setweapstate(W_GRENADE, W_S_POWER, 3000, 1000);
        gamemillis = 4000;
        check(ci.primedfuse(gamemillis) == 1, "expired_fuse_explodes_immediately_without_reset");
        int enabled = sv_csgopenweapons;
        sv_csgopenweapons = 0;
        check(!dropprimed(&ci), "original_profile_is_unchanged");
        sv_csgopenweapons = enabled;
        gamemillis = clock;
        logoutf("PRIMED_SERVER_DONE FAILURES %d", failures);
    }

    ICOMMAND(0, primedservertest, "", (), primedtest::runchecks());
}
