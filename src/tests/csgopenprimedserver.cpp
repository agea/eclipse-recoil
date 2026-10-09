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
        int loot = sv_csgopennoloot, mapped = attrmap[W_SMG], ents = sents.length();
        srventity &item = sents.add();
        item.type = WEAPON;
        loopj(8) item.attrs.add(0);
        item.attrs[0] = W_SMG;
        attrmap[W_SMG] = W_SMG;
        clientinfo holder;
        holder.state = CS_ALIVE;
        holder.actortype = A_PLAYER;
        holder.weapselect = W_SMG;
        holder.weapammo[W_SMG][W_A_CLIP] = 10;
        holder.weapammo[W_SMG][W_A_STORE] = 0;
        holder.weapent[W_SMG] = ents;
        vector<droplist> drops;
        sv_csgopennoloot = 0;
        check(hasitem(ents), "original_rule_allows_valid_map_item");
        check(dropweapon(&holder, DROP_DEATH, W_SMG, drops), "original_rule_drops_valid_inventory");
        drops.shrink(0);
        holder.dropped.reset();
        sv_csgopennoloot = 1;
        check(!hasitem(ents), "no_loot_rejects_map_item");
        sents[ents].spawned = true;
        checkents();
        check(!sents[ents].spawned, "no_loot_despawns_existing_map_item");
        check(!dropweapon(&holder, DROP_DEATH, W_SMG, drops) && drops.empty(), "no_loot_blocks_inventory_drop");
        dropitems(&holder, DROP_DEATH);
        check(holder.dropped.projs.empty(), "no_loot_death_leaves_no_pickup");
        check(!holder.candrop(W_SMG, W_PISTOL, gamemillis, true), "no_loot_blocks_manual_drop");
        check(!holder.canuseweap(gamemode, mutators, W_SMG, W_PISTOL, gamemillis), "no_loot_blocks_ammunition_pickup");
        srventity &prize = sents.add();
        prize.type = WEAPON;
        prize.isvirtual = true;
        loopj(8) prize.attrs.add(0);
        prize.attrs[0] = W_PRIZE;
        holder.hasprize = 1;
        dropitems(&holder, DROP_PRIZE);
        check(holder.dropped.projs.empty(), "no_loot_blocks_prize_drop");
        sv_csgopennoloot = 0;
        dropitems(&holder, DROP_PRIZE);
        check(!holder.dropped.projs.empty(), "original_rule_retains_prize_drop");
        sents.setsize(ents);
        attrmap[W_SMG] = mapped;
        sv_csgopennoloot = loot;
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
