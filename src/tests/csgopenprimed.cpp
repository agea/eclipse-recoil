// Opt-in native integration client, replacing game/projs.o.
#include "../game/projs.cpp"

namespace primedtest
{
    int failures = 0, started = 0;
    float startz = 0;

    ICOMMAND(0, lootcheck, "", (),
    {
        int total = 0;
        int visible = 0;
        int spawned = 0;
        int dropped = 0;
        loopv(entities::ents)
        {
            extentity &e = *entities::ents[i];
            if(e.type != WEAPON) continue;
            total++;
            if(entities::isallowed(e)) visible++;
            if(e.spawned()) spawned++;
        }
        loopv(projs::projs) if(projs::projs[i]->projtype == PROJ_ENTITY) dropped++;
        conoutf(colourwhite, "LOOT_CHECK %s MAP_ITEMS %d ALLOWED %d SPAWNED %d DROPPED %d",
            csgopennoloot && total > 0 && !visible && !spawned && !dropped ? "PASS" : "FAIL", total, visible, spawned, dropped);
    });

    void check(bool ok, const char *name)
    {
        if(!ok) failures++;
        conoutf(colourwhite, "PRIMED_%s %s", ok ? "PASS" : "FAIL", name);
    }

    ICOMMAND(0, primedarm, "i", (int *weap),
    {
        gameent *d = game::player1;
        if(d->state != CS_ALIVE) return;
        failures = 0;
        d->o = vec(100, 80, 512+d->height+0.05f);
        d->vel = d->falling = vec(0, 0, 0);
        d->move = d->strafe = 0;
        d->resetinterp();
        weapons::weapselect(d, *weap, W_S_INTERRUPT);
        d->action[AC_PRIMARY] = true;
        d->actiontime[AC_PRIMARY] = lastmillis;
        started = lastmillis;
        startz = d->center().z;
    });

    ICOMMAND(0, primedcheck, "ii", (int *weap, int *phase),
    {
        gameent *d = game::player1;
        projent *found = NULL;
        int count = 0;
        loopv(projs::projs)
        {
            projent *p = projs::projs[i];
            if(p->owner == d && p->weap == *weap && p->projtype == PROJ_SHOT && p->id < 0)
            {
                found = p;
                count++;
            }
        }
        if(*phase == 0)
        {
            int loot = 0;
            loopv(projs::projs) if(projs::projs[i]->projtype == PROJ_ENTITY) loot++;
            check(loot == 0, "death_releases_no_loot");
            check(count == 1 && found->state != CS_DEAD, "one_live_grenade_after_death");
            if(found)
            {
                conoutf(colourwhite, "PRIMED_LIFETIME %d AGE %d POSITION %.2f START %.2f", found->lifetime, lastmillis-started, found->o.z, startz);
                check(found->lifetime > 200 && found->lifetime < 2300, "death_retains_remaining_fuse");
                check(found->o.z < startz, "grenade_falls_from_holder");
                check(found->vel.x*found->vel.x+found->vel.y*found->vel.y < 100, "no_forward_throw_on_death");
            }
        }
        else
        {
            check(count == 0, "grenade_expires_on_original_countdown");
            if(*weap == W_CORRODER) check(!projs::smokeclouds.empty(), "dead_owner_smoke_emits_cloud");
            conoutf(colourwhite, "PRIMED_NETWORK_DONE WEAPON %d FAILURES %d", *weap, failures);
        }
    });
}
