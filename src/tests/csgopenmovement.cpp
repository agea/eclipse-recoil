// Opt-in native integration client: replace game/physics.o, never link both.
#include "../game/physics.cpp"

namespace movementtest
{
    int failures = 0, flattime = 0;

    void check(bool ok, const char *name)
    {
        if(!ok) failures++;
        conoutf(colourwhite, "MOVEMENT_CHECK_%s %s", ok ? "PASS" : "FAIL", name);
    }

    void actor(gameent &d, float y, int weapon)
    {
        cleardynentcache();
        d.state = CS_ALIVE;
        d.weapselect = weapon;
        d.weapammo[W_PISTOL][W_A_CLIP] = 7;
        d.weapammo[W_PISTOL][W_A_STORE] = 21;
        d.weapammo[W_SMG][W_A_CLIP] = 64;
        d.weapammo[W_SMG][W_A_STORE] = 128;
        d.weapammo[W_GRENADE][W_A_CLIP] = 1;
        d.configure(lastmillis, game::gamemode, game::mutators);
        d.o = vec(100, y, 512+d.height+0.05f);
        d.yaw = 270;
        d.move = d.strafe = 0;
        loopi(100) physics::moveplayer(&d, 10, false, 5);
    }

    ICOMMAND(0, movementcase, "i", (int *which),
    {
        int index = *which;
        int savedclock = lastmillis;
        int enabled = csgopenmovement;
        if(index < 0 || index > 9) return;
        gameent d;
        actor(d, 80+40*index, index == 6 ? W_PISTOL : W_SMG);
        conoutf(colourwhite, "MOVEMENT_SETTINGS ENABLED %d STEP %.3f CLIMB %.3f SCALE %.3f HEIGHT %.3f WEIGHT %.3f IMPULSE %.3f", csgopenmovement, csgopenstepheight, csgopenclimbheight, d.curscale, d.height, d.weight, d.impulsespeed);
        if(index == 7)
        {
            d.weapselect = W_GRENADE;
            d.setweapstate(W_GRENADE, W_S_POWER, 3000, lastmillis);
        }
        if(index == 9) csgopenmovement = 0;
        d.move = 1;
        int time = 0;
        int climbs = 0;
        bool wasclimbing = false;
        bool hiddenok = true;
        bool lockedok = true;
        bool drawok = true;
        float minimumspeed = 1e9f;
        loopi(1000)
        {
            lastmillis = savedclock+i*5;
            physics::moveplayer(&d, 10, true, 5);
            if(d.climbing && !wasclimbing) climbs++;
            if(d.climbing)
            {
                bool pistol = d.weapselect == W_PISTOL;
                hiddenok = hiddenok && d.climbweaponhidden() == !pistol;
                lockedok = lockedok && d.canshoot(d.weapselect, 0, W_PISTOL, lastmillis) == pistol;
                lockedok = lockedok && !d.canswitch(pistol ? W_SMG : W_PISTOL, W_PISTOL, lastmillis, ~0);
            }
            if(wasclimbing && !d.climbing && index != 6)
            {
                int until = lastmillis+W(d.weapselect, delayswitch);
                drawok = d.climbdrawuntil == until && d.weapstate[d.weapselect] == W_S_SWITCH &&
                    !d.canshoot(d.weapselect, 0, W_PISTOL, until-1, ~0) &&
                    d.canshoot(d.weapselect, 0, W_PISTOL, until);
            }
            wasclimbing = d.climbing;
            if(index == 1 && d.o.x >= 150 && d.o.x <= 190) minimumspeed = min(minimumspeed, d.vel.x);
            if(d.o.x >= 200) { time = (i+1)*5; break; }
        }
        conoutf(colourwhite, "MOVEMENT_CASE %d TIME %d XYZ %.3f %.3f %.3f CLIMBS %d MINSPEED %.3f", index, time, d.o.x, d.o.y, d.feetpos().z, climbs, minimumspeed);
        bool blocked = index == 4 || index == 5 || index == 7 || index == 8 || index == 9;
        check(blocked ? !time && !climbs : time > 0, "obstacle_outcome");
        if(index == 0) flattime = time;
        if(index == 1)
        {
            check(flattime > 0 && time <= flattime+25 && !climbs, "knee_no_slowdown");
            check(minimumspeed >= physics::movevelocity(&d)*0.98f, "knee_horizontal_velocity");
        }
        if(index == 2 || index == 3 || index == 6)
        {
            check(climbs == 1 && !d.climbing, "single_completed_climb");
            check(hiddenok && lockedok && drawok, "weapon_holster_and_draw");
            if(index == 6) check(d.climbdrawuntil == 0, "pistol_has_no_draw_penalty");
        }
        csgopenmovement = enabled;
        lastmillis = savedclock;
        cleardynentcache();
    });

    ICOMMAND(0, movementroute, "fffff", (float *x, float *y, float *z, float *dx, float *distance),
    {
        int clock = lastmillis;
        gameent d;
        actor(d, *y, W_SMG);
        d.o = vec(*x, *y, *z+d.height+0.1f);
        d.yaw = *dx > 0 ? 270 : 90;
        loopi(150) physics::moveplayer(&d, 10, false, 5);
        float start = d.o.x;
        d.move = 1;
        int climbs = 0;
        bool previous = false;
        loopi(1600)
        {
            lastmillis = clock+i*5;
            physics::moveplayer(&d, 10, true, 5);
            if(d.climbing && !previous) climbs++;
            previous = d.climbing;
            if((d.o.x-start)*(*dx) >= *distance) break;
        }
        conoutf(colourwhite, "MOVEMENT_ROUTE Y %.3f DIRECTION %.0f PROGRESS %.3f CLIMBS %d", *y, *dx, (d.o.x-start)*(*dx), climbs);
        check((d.o.x-start)*(*dx) >= *distance && !climbs, "canals_stairs_without_climb_or_jump");
        lastmillis = clock;
        cleardynentcache();
    });

    bool sawclimb = false, sawdraw = false;

    ICOMMAND(0, movementnetworkstart, "", (),
    {
        gameent *d = game::player1;
        check(d->state == CS_ALIVE && d->weapselect == W_SMG, "network_actor_ready");
        d->o = vec(155, 200, 512+d->height+0.02f);
        d->vel = d->falling = vec(0, 0, 0);
        d->physstate = PHYS_FLOOR;
        d->floor = vec(0, 0, 1);
        d->yaw = 270;
        d->move = 1;
        d->resetinterp();
        cleardynentcache();
    });

    ICOMMAND(0, movementnetworkobserve, "", (),
    {
        loopv(game::players)
        {
            gameent *d = game::players[i];
            if(!d || d == game::player1 || d->actortype != A_PLAYER) continue;
            if(d->climbing) sawclimb = true;
            if(sawclimb && !d->climbing && lastmillis < d->climbdrawuntil) sawdraw = true;
        }
    });

    ICOMMAND(0, movementnetworkdone, "", (),
    {
        check(sawclimb && sawdraw, "remote_climb_and_weapon_draw_events");
        conoutf(colourwhite, "MOVEMENT_NETWORK_DONE FAILURES %d", failures);
    });

    float jump(float modifier, int &airtime)
    {
        int savedclock = lastmillis;
        gameent d;
        actor(d, 500, W_SMG);
        impulsejump = modifier;
        float floor = d.feetpos().z, apex = 0;
        d.action[AC_JUMP] = true;
        loopi(1000)
        {
            lastmillis = savedclock+i*5;
            physics::moveplayer(&d, 10, true, 5);
            d.action[AC_JUMP] = false;
            apex = max(apex, d.feetpos().z-floor);
            if(i > 20 && d.physstate >= PHYS_SLOPE && d.feetpos().z <= floor+0.1f)
            {
                airtime = (i+1)*5;
                break;
            }
        }
        lastmillis = savedclock;
        cleardynentcache();
        return apex;
    }

    ICOMMAND(0, movementjump, "", (),
    {
        float setting = impulsejump;
        int beforetime = 0;
        int aftertime = 0;
        float before = jump(1.5f, beforetime);
        float after = jump(setting, aftertime);
        impulsejump = setting;
        conoutf(colourwhite, "MOVEMENT_JUMP BEFORE %.3f %d AFTER %.3f %d", before, beforetime, after, aftertime);
        check(before > 0 && after > csgopenstepheight && after < before*0.65f, "lower_jump_apex");
        check(aftertime > 0 && aftertime < beforetime*0.85f, "shorter_jump_airtime");
    });

    ICOMMAND(0, movementdone, "", (),
    {
        clientstate state;
        state.beginclimb(lastmillis);
        state.endclimb(lastmillis);
        state.weapreset(true);
        check(!state.climbing && !state.climbdrawuntil, "spawn_clears_climb_state");
        conoutf(colourwhite, "MOVEMENT_DONE FAILURES %d", failures);
        intret(failures);
    });
}
