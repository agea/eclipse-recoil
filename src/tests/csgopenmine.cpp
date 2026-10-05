// Opt-in native integration client: replace game/projs.o, never link both.
#include "../game/projs.cpp"

namespace minetest
{
    int failures = 0;

    void check(bool ok, const char *name)
    {
        if(!ok) failures++;
        conoutf(colourwhite, "MINE_CHECK_%s %s", ok ? "PASS" : "FAIL", name);
    }

    void projectile(projent &p, int weapon, const vec &pos, const vec &dir)
    {
        p.weap = p.fromweap = weapon;
        p.flags = p.fromflags = 0;
        p.id = 100000;
        p.owner = game::player1;
        p.local = true;
        p.child = false;
        p.escaped = true;
        p.projcollide = W2(weapon, collide, false);
        p.o = p.from = p.trailpos = pos;
        p.dest = vec(pos).add(dir);
        p.vel = vec(dir).mul(80);
        p.falling = vec(0, 0, 0);
        p.radius = p.xradius = p.yradius = p.height = p.aboveeye = p.zradius = 1;
        p.lifetime = p.lifemillis = 60000;
        p.spawntime = lastmillis;
        p.collidetype = COLLIDE_ELLIPSE;
    }

    ICOMMAND(0, minecontacttest, "", (),
    {
        failures = 0;
        check(csgopenweapons != 0, "tdm_enabled");
        vec pos = game::player1->o;
        // Use a map spawn, independent of spectator/loadout UI state.
        loopv(entities::ents) if(entities::ents[i]->type == PLAYERSTART)
        {
            pos = vec(entities::ents[i]->o).add(vec(0, 0, 16));
            break;
        }
        projent mine;
        projectile(mine, W_MINE, pos, vec(0, 0, -1));
        bool hit = false;
        // Sweep against the actual collision carriers; invisible model
        // surfaces need not participate in the render ray-floor query.
        loopi(512)
        {
            mine.o = vec(pos).sub(vec(0, 0, i*0.5f));
            if(collide(&mine, vec(0, 0, -1), 0.f, false, true, GUARDRADIUS) && !collidewall.iszero())
            {
                hit = true;
                break;
            }
        }
        check(hit, "support_found");
        if(hit)
        {
            vec contact = mine.o;
            int inside = collideinside;
            vec normal = collidewall;
            conoutf(colourwhite, "MINE_CONTACT HIT %d INSIDE %d NORMAL %.3f %.3f %.3f", hit, inside, normal.x, normal.y, normal.z);
            check(hit && !normal.iszero(), "surface_contact");
            int result = projs::impact(mine, vec(0, 0, -1), NULL, 0, normal, inside);
            check(result == 1 && mine.stuck != 0, "contact_sticks_without_explosion");
            check(mine.lifetime == 60000 && !mine.beenused, "contact_preserves_fuse");
            gameent enemy;
            enemy.state = CS_ALIVE;
            enemy.team = game::player1->team == T_ALPHA ? T_OMEGA : T_ALPHA;
            enemy.height = enemy.aboveeye = enemy.zradius = 1;
            enemy.o = vec(mine.o).add(vec(0, 0, 4));
            int clock = lastmillis;
            check(!projs::minetrigger(mine, &enemy), "unarmed_enemy_ignored");
            lastmillis += W2(W_MINE, proxdelay, false);
            check(!projs::minetrigger(mine, game::player1), "owner_ignored");
            enemy.team = game::player1->team;
            check(!projs::minetrigger(mine, &enemy), "ally_ignored");
            enemy.team = game::player1->team == T_ALPHA ? T_OMEGA : T_ALPHA;
            check(projs::minetrigger(mine, &enemy), "armed_enemy_triggers");
            lastmillis = clock;

            projent bullet;
            projectile(bullet, W_PISTOL, contact, vec(0, 0, -1));
            check(projs::impact(bullet, vec(0, 0, -1), NULL, 0, normal, inside) == 0, "bullet_still_impacts");
            bullet.owner = NULL;

            projent original;
            projectile(original, W_MINE, contact, vec(0, 0, -1));
            int enabled = csgopenweapons;
            csgopenweapons = 0;
            int upstream = projs::impact(original, vec(0, 0, -1), NULL, 0, normal, inside);
            csgopenweapons = enabled;
            check(inside ? upstream == 0 && !original.stuck : upstream == 1 && original.stuck, "original_collision_preserved");
            original.owner = NULL;

            projent overlap;
            projectile(overlap, W_MINE, contact, vec(0, 0, -1));
            check(projs::impact(overlap, vec(0, 0, -1), NULL, 0, vec(0, 0, 0), 1) == 0 && !overlap.stuck,
                "unresolved_overlap_preserves_fallback");
            overlap.owner = NULL;
        }
        mine.owner = NULL; // Stack test projectile is not in the owner chain.
        conoutf(colourwhite, "MINE_DONE FAILURES %d", failures);
    });
}
