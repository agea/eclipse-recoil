// Opt-in native integration client: replace game/physics.o, never link both.
#include "../game/physics.cpp"

namespace movementtest
{
    int failures = 0, flattime = 0;

    ICOMMAND(0, falljump, "i", (int *pressed),
    {
        game::player1->action[AC_JUMP] = *pressed != 0;
        game::player1->actiontime[AC_JUMP] = lastmillis;
    });

    ICOMMAND(0, falldrop, "i", (int *speed),
    {
        gameent *d = game::player1;
        if(d->state != CS_ALIVE) return;
        cleardynentcache();
        d->o = vec(100, 80, 512+d->height+0.1f);
        d->vel = vec(0, 0, 0);
        d->falling = vec(0, 0, -float(*speed));
        d->physstate = PHYS_FALL;
        d->airmillis = max(lastmillis-100, 1);
        d->move = d->strafe = 0;
        d->resetinterp();
        conoutf(colourwhite, "FALL_DROP SPEED %d HEALTH %d", *speed, d->health);
    });

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

    ICOMMAND(0, movementspawns, "f", (float *alphafloor),
    {
        int clock = lastmillis;
        int count = 0;
        const vector<extentity *> &ents = entities::getents();
        loopv(ents) if(ents[i]->type == PLAYERSTART)
        {
            extentity &e = *ents[i];
            loopj(8)
            {
                gameent d;
                actor(d, 80, W_SMG);
                d.team = e.attrs[0];
                entities::spawnplayer(&d, i, false);
                vec start(d.feetpos());
                loopk(1000)
                {
                    lastmillis = clock+k*5;
                    physics::moveplayer(&d, 10, false, 5);
                }
                bool supported = d.physstate >= PHYS_SLOPE && d.feetpos().z >= e.o.z-24 &&
                    (d.team != T_ALPHA || d.feetpos().z >= *alphafloor-1);
                conoutf(colourwhite, "MOVEMENT_SPAWN ENT %d TEAM %d RUN %d AUTHORED %.3f %.3f %.3f START %.3f %.3f %.3f END %.3f %.3f %.3f STATE %d", i, e.attrs[0], j, e.o.x, e.o.y, e.o.z, start.x, start.y, start.z, d.o.x, d.o.y, d.feetpos().z, d.physstate);
                check(supported, "spawn_settles_on_authored_level");
                lastmillis = clock;
                cleardynentcache();
                count++;
            }
        }
        conoutf(colourwhite, "MOVEMENT_SPAWNS_DONE CASES %d FAILURES %d", count, failures);
    });

    ICOMMAND(0, movementseam, "i", (int *which),
    {
        gameent d;
        actor(d, 940+30*(*which), W_SMG);
        d.o.x = 155.5f;
        d.move = 1;
        vec before(d.o);
        vec delta(5, 0, 0);
        bool crossed = physics::tryseamstep(&d, delta);
        conoutf(colourwhite, "MOVEMENT_SEAM %d CROSSED %d RISE %.3f", *which, crossed ? 1 : 0, d.o.z-before.z);
        check(*which == 0 ? crossed && d.o.z-before.z <= 1.05f : !crossed && d.o == before,
            *which == 0 ? "small_seam_supported_and_bounded" : "seam_recovery_preserves_barrier_and_ceiling");
        d.o = before;
        bool stepped = physics::tryseamstep(&d, delta, physics::stairheight);
        check(*which < 2 ? stepped && d.o.z-before.z <= physics::stairheight+0.05f : !stepped && d.o == before,
            *which < 2 ? "local_step_uses_map_stair_height" : "local_step_preserves_low_ceiling");
        d.o = before;
        vec savedfloor(d.floor);
        vec savedvel(d.vel);
        d.floor = vec(-1, 0, 1).normalize();
        d.vel = vec(3, 0, 3);
        bool uphill = physics::tryseamstep(&d, delta);
        check(*which == 0 ? uphill : !uphill, "uphill_velocity_is_not_a_jump");
        d.o = before;
        d.floor = vec(0, 0, 1);
        d.vel = vec(0, 0, 3);
        check(!physics::tryseamstep(&d, delta) && d.o == before, "upward_jump_has_no_step_recovery");
        d.floor = savedfloor;
        d.vel = savedvel;
        d.o = before;
        int enabled = csgopenmovement;
        csgopenmovement = 0;
        check(!physics::tryseamstep(&d, delta) && d.o == before, "original_profile_has_no_seam_recovery");
        csgopenmovement = enabled;
        d.o = before;
        d.o.z += 10;
        vec unsupported(d.o);
        check(!physics::tryseamstep(&d, delta) && d.o == unsupported, "seam_recovery_requires_landing_support");
        d.o = before;
        d.physstate = PHYS_FALL;
        d.o.z += 2;
        before = d.o;
        check(!physics::tryseamstep(&d, delta) && d.o == before, "seam_recovery_requires_grounded_actor");
        cleardynentcache();
    });

    // Full curved B-tunnel staircase, including both landings (Source X is reflected).
    ICOMMAND(0, movementbstairs, "iii", (int *direction, int *lane, int *blocked),
    {
        if((*direction != 1 && *direction != -1) || *lane < -3 || *lane > 3) return;
        int clock = lastmillis;
        vector<vec> path;
        path.add(vec(1216.00000f, 990.00000f, 2132.16000f));
        path.add(vec(1215.95877f, 982.20272f, 2134.31500f));
        path.add(vec(1215.96104f, 978.37224f, 2136.31500f));
        path.add(vec(1216.11854f, 973.11844f, 2138.31500f));
        path.add(vec(1216.57355f, 969.01145f, 2140.31500f));
        path.add(vec(1217.47232f, 965.01894f, 2142.31500f));
        path.add(vec(1219.02974f, 961.21465f, 2144.31500f));
        path.add(vec(1221.04180f, 957.72696f, 2146.31500f));
        path.add(vec(1223.47919f, 954.46145f, 2148.31500f));
        path.add(vec(1226.45275f, 951.63234f, 2150.31500f));
        path.add(vec(1229.67876f, 949.27630f, 2152.31500f));
        path.add(vec(1233.16339f, 947.31469f, 2154.31500f));
        path.add(vec(1237.03104f, 945.85465f, 2156.31500f));
        path.add(vec(1240.97411f, 944.96095f, 2158.31500f));
        path.add(vec(1245.11517f, 944.60328f, 2160.31500f));
        path.add(vec(1250.12004f, 944.52106f, 2162.31500f));
        path.add(vec(1254.24757f, 944.51420f, 2164.31500f));
        path.add(vec(1258.26661f, 944.49315f, 2166.31500f));
        path.add(vec(1262.00000f, 944.50000f, 2168.16000f));
        path.add(vec(1270.00000f, 944.50000f, 2168.16000f));
        vector<vec> guide;
        loopv(path) guide.add(path[i]);
        loopv(path)
        {
            vec tangent(guide[min(i+1, path.length()-1)]);
            tangent.sub(guide[max(i-1, 0)]);
            tangent.z = 0;
            tangent.normalize();
            path[i].add(vec(-tangent.y, tangent.x, 0).mul(*lane*2));
        }
        if(*direction < 0) path.reverse();
        gameent d;
        actor(d, path[0].y, W_SMG);
        d.o = vec(path[0]).addz(d.height+1);
        loopi(150) physics::moveplayer(&d, 10, false, 5);
        bool supportedstart = fabsf(d.feetpos().z-path[0].z) < 4;
        bool continuous = supportedstart;
        int target = 1;
        int climbs = 0;
        bool previous = false;
        d.move = 1;
        loopi(6000)
        {
            if(d.feetpos().z < path[target].z-4) continuous = false;
            vec delta(path[target]);
            delta.sub(d.feetpos());
            delta.z = 0;
            vec along(path[target]);
            along.sub(path[target-1]);
            along.z = 0;
            along.normalize();
            vec passed(d.feetpos());
            passed.sub(path[target]);
            if(delta.magnitude() < 1.25f || (target < path.length()-1 && passed.dot(along) >= 0))
            {
                if(++target == path.length()) break;
                delta = vec(path[target]).sub(d.feetpos());
                delta.z = 0;
            }
            d.yaw = atan2f(-delta.x, delta.y)/RAD;
            lastmillis = clock+i*5;
            physics::moveplayer(&d, 10, true, 5);
            if(d.climbing && !previous) climbs++;
            previous = d.climbing;
        }
        conoutf(colourwhite, "MOVEMENT_B_STAIRS DIR %d LANE %d TARGET %d/%d STARTSUPPORT %d CLIMBS %d END %.3f %.3f %.3f", *direction, *lane, target, path.length(), supportedstart, climbs, d.o.x, d.o.y, d.feetpos().z);
        check(supportedstart && continuous && !climbs && (*blocked ? target < path.length() : target == path.length() && fabsf(d.feetpos().z-path.last().z) < 4),
            *blocked ? "b_staircase_pillar_blocks" : "full_b_staircase_without_jump_or_climb");
        lastmillis = clock;
        cleardynentcache();
    });

    // Long A doors: keep the intended S-shaped gap between the opened leaves.
    ICOMMAND(0, movementdoor, "iii", (int *door, int *direction, int *lane),
    {
        if(*door < 0 || *door > 1 || (*direction != 1 && *direction != -1) || abs(*lane) > 1) return;
        int clock = lastmillis;
        float x = *door ? 784 : 783.75f;
        float y = *door ? 859 : 747;
        vector<vec> path;
        // The inner chamber has a real crate beside the north doorway.
        // Start outside its footprint rather than testing from inside it.
        path.add(vec(x+(*door ? 10+*lane : *lane*3), y-25, 2160.16f));
        path.add(vec(x+(*door ? 10 : 4)+*lane, y-12, 2160.16f));
        path.add(vec(x+3+*lane, y-5, 2160.16f));
        path.add(vec(x+*lane, y, 2160.16f));
        path.add(vec(x-3+*lane, y+5, 2160.16f));
        path.add(vec(x-4+*lane, y+12, 2160.16f));
        path.add(vec(x+*lane*3, y+25, 2160.16f));
        if(*direction < 0) path.reverse();
        gameent d;
        actor(d, path[0].y, W_SMG);
        d.o = vec(path[0]).addz(d.height+1);
        loopi(150) physics::moveplayer(&d, 10, false, 5);
        bool supported = fabsf(d.feetpos().z-path[0].z) < 4;
        int target = 1;
        int climbs = 0;
        bool previous = false;
        d.move = 1;
        loopi(6000)
        {
            if(fabsf(d.feetpos().z-2160.16f) > 4) supported = false;
            vec delta(path[target]);
            delta.sub(d.feetpos());
            delta.z = 0;
            vec along(path[target]);
            along.sub(path[target-1]);
            along.z = 0;
            along.normalize();
            vec passed(d.feetpos());
            passed.sub(path[target]);
            if(delta.magnitude() < 1.25f || (target < path.length()-1 && passed.dot(along) >= 0))
            {
                if(++target == path.length()) break;
                delta = vec(path[target]).sub(d.feetpos());
                delta.z = 0;
            }
            d.yaw = atan2f(-delta.x, delta.y)/RAD;
            lastmillis = clock+i*5;
            physics::moveplayer(&d, 10, true, 5);
            if(d.climbing && !previous) climbs++;
            previous = d.climbing;
        }
        conoutf(colourwhite, "MOVEMENT_DOOR %d DIR %d LANE %d TARGET %d/%d SUPPORT %d CLIMBS %d END %.3f %.3f %.3f", *door, *direction, *lane, target, path.length(), supported, climbs, d.o.x, d.o.y, d.feetpos().z);
        check(target == path.length() && supported && !climbs, "open_door_without_jump_or_climb");
        lastmillis = clock;
        cleardynentcache();
    });

    ICOMMAND(0, movementstairs, "ii", (int *which, int *direction),
    {
        int clock = lastmillis;
        gameent d;
        actor(d, 500+30*(*which), W_SMG);
        d.o = vec(*direction > 0 ? 130 : 255, 500+30*(*which), (*direction > 0 ? 512 : 548)+d.height+0.1f);
        d.yaw = *direction > 0 ? 270 : 90;
        loopi(150) physics::moveplayer(&d, 10, false, 5);
        float start = d.o.x;
        d.move = 1;
        int climbs = 0;
        bool previous = false;
        loopi(2000)
        {
            lastmillis = clock+i*5;
            physics::moveplayer(&d, 10, true, 5);
            if(d.climbing && !previous) climbs++;
            previous = d.climbing;
            if((d.o.x-start)*(*direction) >= 110) break;
        }
        float progress = (d.o.x-start)*(*direction);
        conoutf(colourwhite, "MOVEMENT_STAIRS %d DIR %d PROGRESS %.3f CLIMBS %d Z %.3f", *which, *direction, progress, climbs, d.feetpos().z);
        check(*which == 0 ? progress >= 110 && !climbs : progress < 110 && !climbs,
            *which == 0 ? "close_stairs_walk_without_climb" : "stair_ceiling_and_wall_block");
        lastmillis = clock;
        cleardynentcache();
    });

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

    ICOMMAND(0, movementjumpwindow, "fffff", (float *x, float *y, float *z, float *yaw, float *distance),
    {
        int clock = lastmillis;
        gameent d;
        actor(d, *y, W_SMG);
        d.o = vec(*x, *y, *z+d.height+0.1f);
        d.yaw = *yaw;
        loopi(100) physics::moveplayer(&d, 10, false, 5);
        vec start(d.feetpos());
        vec direction(-sinf(*yaw*RAD), cosf(*yaw*RAD), 0);
        d.move = 1;
        d.action[AC_JUMP] = true;
        float progress = 0;
        loopi(1000)
        {
            lastmillis = clock+i*5;
            physics::moveplayer(&d, 10, true, 5);
            d.action[AC_JUMP] = false;
            if(i >= 10 && i < 30) d.height = max(d.zradius*0.48f, d.height-d.zradius*0.52f/20);
            progress = vec(d.feetpos()).sub(start).dot(direction);
            if(progress >= *distance) break;
        }
        d.move = 0;
        loopi(200) physics::moveplayer(&d, 10, false, 5);
        conoutf(colourwhite, "MOVEMENT_JUMP_WINDOW PROGRESS %.3f END %.3f %.3f %.3f STATE %d", progress, d.o.x, d.o.y, d.feetpos().z, d.physstate);
        check(progress >= *distance && d.physstate >= PHYS_SLOPE, "roof_window_jump_crouch_reaches_room");
        lastmillis = clock;
        cleardynentcache();
    });

    ICOMMAND(0, movementwindow, "fffffi", (float *x, float *y, float *z, float *yaw, float *distance, int *duck),
    {
        gameent d;
        actor(d, *y, W_SMG);
        if(*duck) d.height = d.zradius*(csgopenmovement ? 0.48f : CROUCHLOW);
        d.o = vec(*x, *y, *z+d.height+0.1f);
        d.yaw = *yaw;
        vec dir;
        vecfromyawpitch(d.yaw, 0, 1, 0, dir);
        float progress = 0;
        while(progress < *distance)
        {
            d.o.add(vec(dir).mul(0.1f));
            if(collide(&d, vec(dir), 0.f, false))
            {
                conoutf(colourwhite, "MOVEMENT_WINDOW_CONTACT XYZ %.3f %.3f %.3f NORMAL %.3f %.3f %.3f", d.o.x, d.o.y, d.feetpos().z, collidewall.x, collidewall.y, collidewall.z);
                break;
            }
            progress += 0.1f;
        }
        conoutf(colourwhite, "MOVEMENT_WINDOW DUCK %d HEIGHT %.3f PROGRESS %.3f", *duck, d.height+d.aboveeye, progress);
        check(progress >= *distance, "source_window_has_body_clearance");
        cleardynentcache();
    });

    ICOMMAND(0, movementladder, "ffffff", (float *x, float *y, float *z, float *yaw, float *pitch, float *rise),
    {
        int clock = lastmillis;
        gameent d;
        actor(d, *y, W_SMG);
        d.o = vec(*x, *y, *z+d.height+0.1f);
        d.yaw = *yaw;
        d.pitch = *pitch;
        loopi(100) physics::moveplayer(&d, 10, false, 5);
        float start = d.feetpos().z;
        float highest = start;
        int contacts = 0;
        d.move = 1;
        loopi(1000)
        {
            lastmillis = clock+i*5;
            physics::moveplayer(&d, 10, true, 5);
            if(physics::laddercheck(&d)) contacts++;
            highest = max(highest, d.feetpos().z);
            if(highest-start >= *rise && !physics::laddercheck(&d) && d.physstate >= PHYS_SLOPE) break;
        }
        d.move = 0;
        loopi(200) physics::moveplayer(&d, 10, false, 5);
        conoutf(colourwhite, "MOVEMENT_LADDER CONTACTS %d RISE %.3f END %.3f %.3f %.3f STATE %d HEIGHT %.3f", contacts, highest-start, d.o.x, d.o.y, d.feetpos().z, d.physstate, d.height+d.aboveeye);
        check(contacts > 0 && highest-start >= *rise, "ladder_forward_without_jump");
        check(d.physstate >= PHYS_SLOPE && !physics::laddercheck(&d) && d.feetpos().z >= start+*rise-2, "ladder_reaches_supported_roof");
        lastmillis = clock;
        cleardynentcache();
    });

    ICOMMAND(0, movementroute, "fffffi", (float *x, float *y, float *z, float *dx, float *distance, int *blocked),
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
        if(*blocked) check((d.o.x-start)*(*dx) < *distance && !climbs, "authored_playerclip_blocks_route");
        else check((d.o.x-start)*(*dx) >= *distance && !climbs, "supported_route_without_climb_or_jump");
        lastmillis = clock;
        cleardynentcache();
    });

    ICOMMAND(0, movementpath, "fffffi", (float *x, float *y, float *z, float *yaw, float *distance, int *blocked),
    {
        int clock = lastmillis;
        gameent d;
        actor(d, *y, W_SMG);
        d.o = vec(*x, *y, *z+d.height+0.1f);
        d.yaw = *yaw;
        loopi(150) physics::moveplayer(&d, 10, false, 5);
        vec start(d.feetpos());
        vec direction(-sinf(*yaw*RAD), cosf(*yaw*RAD), 0);
        d.move = 1;
        int climbs = 0;
        bool previous = false;
        loopi(1600)
        {
            lastmillis = clock+i*5;
            physics::moveplayer(&d, 10, true, 5);
            if(d.climbing && !previous) climbs++;
            previous = d.climbing;
            if(vec(d.o).sub(start).dot(direction) >= *distance) break;
        }
        float progress = vec(d.o).sub(start).dot(direction);
        if(progress < *distance)
        {
            vec old(d.o);
            vec probe(direction);
            probe.projectxy(d.floor).mul(0.2f);
            d.o.add(probe);
            bool hit = collide(&d, probe);
            conoutf(colourwhite, "MOVEMENT_PATH_CONTACT HIT %d INSIDE %d NORMAL %.3f %.3f %.3f DIR %.3f %.3f %.3f", hit, collideinside, collidewall.x, collidewall.y, collidewall.z, probe.x, probe.y, probe.z);
            d.o = old;
        }
        conoutf(colourwhite, "MOVEMENT_PATH START %.3f %.3f %.3f YAW %.1f PROGRESS %.3f END %.3f %.3f %.3f FLOOR %.3f %.3f %.3f STATE %d CLIMBS %d", start.x, start.y, start.z, *yaw, progress, d.o.x, d.o.y, d.feetpos().z, d.floor.x, d.floor.y, d.floor.z, d.physstate, climbs);
        check((*blocked ? progress < *distance : progress >= *distance) && !climbs, *blocked ? "path_obstacle_blocks" : "path_without_climb_or_jump");
        lastmillis = clock;
        cleardynentcache();
    });

    ICOMMAND(0, movementflow, "fffffi", (float *x, float *y, float *z, float *yaw, float *distance, int *blocked),
    {
        int clock = lastmillis;
        gameent d;
        actor(d, *y, W_SMG);
        d.o = vec(*x, *y, *z+d.height+0.1f);
        d.yaw = *yaw;
        loopi(150) physics::moveplayer(&d, 10, false, 5);
        vec start(d.feetpos());
        vec direction(-sinf(*yaw*RAD), cosf(*yaw*RAD), 0);
        d.move = 1;
        d.vel = vec(direction).mul(physics::movevelocity(&d, false));
        int climbs = 0;
        int slowframes = 0;
        int slowrun = 0;
        int maxslowrun = 0;
        float minadvance = 1e10f;
        int elapsed = 0;
        bool previous = false;
        loopi(1600)
        {
            lastmillis = clock+i*5;
            vec before(d.o);
            physics::moveplayer(&d, 10, true, 5);
            float advance = vec(d.o).sub(before).dot(direction);
            elapsed = (i+1)*5;
            {
                minadvance = min(minadvance, advance);
                if(advance < 0.1f)
                {
                    if(!slowframes) conoutf(colourwhite, "MOVEMENT_FLOW_FIRST_SLOW XYZ %.3f %.3f %.3f FLOOR %.3f %.3f %.3f VEL %.3f %.3f %.3f STATE %d CLIMB %d", d.o.x, d.o.y, d.feetpos().z, d.floor.x, d.floor.y, d.floor.z, d.vel.x, d.vel.y, d.vel.z, d.physstate, d.climbing);
                    slowframes++;
                    maxslowrun = max(maxslowrun, ++slowrun);
                }
                else slowrun = 0;
            }
            if(d.climbing && !previous) climbs++;
            previous = d.climbing;
            if(vec(d.o).sub(start).dot(direction) >= *distance) break;
        }
        conoutf(colourwhite, "MOVEMENT_FLOW MS %d SLOW %d MAXPAUSE_MS %d MINADVANCE %.4f", elapsed, slowframes, maxslowrun*5, minadvance);
        float progress = vec(d.o).sub(start).dot(direction);
        if(progress < *distance)
        {
            vec old(d.o);
            vec probe(direction);
            probe.projectxy(d.floor).mul(0.2f);
            d.o.add(probe);
            bool hit = collide(&d, probe);
            conoutf(colourwhite, "MOVEMENT_PATH_CONTACT HIT %d INSIDE %d NORMAL %.3f %.3f %.3f DIR %.3f %.3f %.3f", hit, collideinside, collidewall.x, collidewall.y, collidewall.z, probe.x, probe.y, probe.z);
            d.o = old;
        }
        conoutf(colourwhite, "MOVEMENT_PATH START %.3f %.3f %.3f YAW %.1f PROGRESS %.3f END %.3f %.3f %.3f FLOOR %.3f %.3f %.3f STATE %d CLIMBS %d", start.x, start.y, start.z, *yaw, progress, d.o.x, d.o.y, d.feetpos().z, d.floor.x, d.floor.y, d.floor.z, d.physstate, climbs);
        check((*blocked ? progress < *distance : progress >= *distance) && !climbs && (*blocked || maxslowrun < 3), *blocked ? "path_obstacle_blocks" : "path_without_climb_or_jump");
        lastmillis = clock;
        cleardynentcache();
    });

    ICOMMAND(0, movementslope, "ii", (int *which, int *direction),
    {
        if(*which < 0 || *which > 3 || (*direction != 1 && *direction != -1)) return;
        int clock = lastmillis;
        gameent d;
        actor(d, 600+80*(*which), W_SMG);
        float height = *which ? 124 : 58;
        d.o = vec(*direction > 0 ? 100 : 350, 600+80*(*which), 512+d.height+(*direction > 0 ? 0 : height)+0.05f);
        d.vel = d.falling = vec(0, 0, 0);
        d.yaw = *direction > 0 ? 270 : 90;
        loopi(100) physics::moveplayer(&d, 10, false, 5);
        float start = d.o.x;
        d.move = 1;
        int climbs = 0;
        int frames = 0;
        bool previous = false;
        Uint64 begin = SDL_GetPerformanceCounter();
        loopi(1600)
        {
            lastmillis = clock+i*5;
            physics::moveplayer(&d, 10, true, 5);
            if(d.climbing && !previous) climbs++;
            previous = d.climbing;
            frames++;
            if((d.o.x-start)*(*direction) >= 240) break;
        }
        Uint64 micros = (SDL_GetPerformanceCounter()-begin)*1000000/SDL_GetPerformanceFrequency();
        conoutf(colourwhite, "MOVEMENT_SLOPE %d DIR %d PROGRESS %.3f Z %.3f CLIMBS %d FRAMES %d CPU_US %lld", *which, *direction, (d.o.x-start)*(*direction), d.feetpos().z, climbs, frames, (long long)micros);
        if(*which < 2) check((d.o.x-start)*(*direction) >= 240 && !climbs, "continuous_slope_without_climb_or_jump");
        else check((d.o.x-start)*(*direction) < 240 && !climbs, "slope_obstacle_still_blocks");
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
