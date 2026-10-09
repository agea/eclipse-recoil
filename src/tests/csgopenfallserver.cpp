// Opt-in dedicated integration server; production binaries never expose this command.
#include "../game/server.cpp"

namespace falltest
{
    int failures = 0;

    void check(bool ok, const char *name)
    {
        if(!ok) failures++;
        logoutf("FALL_CHECK_%s %s", ok ? "PASS" : "FAIL", name);
    }

    void run()
    {
        using namespace server;
        failures = 0;
        int selfdamage = sv_damageself;
        sv_damageself = 0;
        clientinfo ci;
        ci.state = CS_ALIVE;
        ci.actortype = A_PLAYER;
        ci.health = 100;
        ci.lastspawn = 10;
        ci.lastfall = -1;
        ci.inmaterial = MAT_AIR;
        ci.submerged = 0;
        fallevent ev;
        ev.millis = 20;
        ev.speed = 115;
        ev.process(&ci);
        check(ci.health == 100, "formerly_fifteen_damage_wall_drop_is_safe");
        ev.millis++;
        ev.speed = 160;
        ev.process(&ci);
        check(ci.health == 100, "threshold_is_safe");
        ev.millis++;
        ev.speed = 210;
        ev.process(&ci);
        check(ci.health == 50, "server_applies_fifty_health_without_weapon_scale");
        ev.process(&ci);
        check(ci.health == 50, "duplicate_landing_is_ignored");
        ev.millis = 9;
        ev.process(&ci);
        check(ci.health == 50, "old_life_event_is_ignored");
        ev.millis = 30;
        ci.state = CS_SPECTATOR;
        ev.process(&ci);
        check(ci.health == 50, "spectators_are_ignored");
        ci.state = CS_ALIVE;
        ci.climbing = true;
        ev.process(&ci);
        check(ci.health == 50, "climbing_is_ignored");
        ci.climbing = false;
        ci.inmaterial = MAT_WATER;
        ci.submerged = 0.5f;
        ev.process(&ci);
        check(ci.health == 50, "water_cushions_landing");
        ci.inmaterial = MAT_AIR;
        ci.submerged = 0;
        ev.millis++;
        ev.speed = -1;
        ev.process(&ci);
        ev.speed = 1001;
        ev.process(&ci);
        check(ci.health == 50, "invalid_speed_is_ignored");
        int enabled = sv_csgopenfalldamage;
        sv_csgopenfalldamage = 0;
        ev.speed = 210;
        ev.process(&ci);
        check(ci.health == 50, "original_profile_is_safe");
        sv_csgopenfalldamage = enabled;
        ci.actortype = A_BOT;
        ev.speed = 170;
        ev.process(&ci);
        check(ci.health == 40, "bots_take_same_damage");
        ci.actortype = A_PLAYER;
        ev.millis++;
        ev.speed = 260;
        ev.process(&ci);
        check(ci.state == CS_DEAD && ci.deaths == 1, "lethal_fall_uses_normal_death_path");
        ev.millis++;
        ev.process(&ci);
        check(ci.deaths == 1, "dead_actor_is_not_killed_twice");
        sv_damageself = selfdamage;
        logoutf("FALL_DONE FAILURES %d", failures);
    }

    ICOMMAND(0, fallservertest, "", (), falltest::run());
}
