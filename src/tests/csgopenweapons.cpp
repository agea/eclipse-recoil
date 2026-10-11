// Opt-in native integration client: replace game/game.o, never link both.
#include "../game/game.cpp"

namespace weapontest
{
    int failures = 0;
    void check(bool ok, const char *label)
    {
        if(!ok) failures++;
        conoutf(colourwhite, "WEAPON_CHECK_%s %s", ok ? "PASS" : "FAIL", label);
    }

    void run()
    {
        check(game::csgopenweaponmodels == 1, "local_pack_enabled");
        int weapons[] = { W_PISTOL, W_SMG, W_PLASMA, W_ZAPPER, W_RIFLE, W_FLAMER, W_SHOTGUN, W_MINIGUN, W_GRENADE, W_CORRODER, W_ROCKET };
        loopi(int(sizeof(weapons)/sizeof(weapons[0]))) loopj(2) loopk(2) loopl(4)
        {
            gameent d;
            int weap = weapons[i];
            d.actortype = A_PLAYER;
            d.model = j;
            d.team = j ? T_OMEGA : T_ALPHA;
            d.state = CS_ALIVE;
            d.physstate = PHYS_FLOOR;
            d.weapselect = weap;
            d.weapammo[weap][W_A_CLIP] = 1;
            d.configure(lastmillis, game::gamemode, game::mutators);
            d.yaw = l*90.f;
            d.pitch = d.roll = 0;
            loopm(TAG_MAX) d.tag[m] = vec(-1);
            modelstate mdl;
            modelattach links[VANITYMAX + ATTACHMENTMAX];
            const char *name = game::getplayerstate(&d, mdl, k, d.curscale, MDL_NORENDER|MDL_NOBATCH, links, false);
            check(name && (k ? strstr(name, "actors/soldier/") : strstr(name, "weapons/urbanterror/")), "player_model");
            if(k) check(links[0].name && strstr(links[0].name, "weapons/urbanterror/"), "world_attachment");
            else check(name && strstr(name, j ? "/hwep/omega" : "/hwep/alpha") && !links[0].name, "one_set_of_team_hands");
            if(name) rendermodel(name, mdl, &d);
            check(d.tag[TAG_MUZZLE1] != vec(-1) && d.tag[TAG_ORIGIN] != vec(-1), "muzzle_and_origin_resolve");
            if(weap != W_GRENADE && weap != W_CORRODER)
            {
                vec barrel = vec(d.tag[TAG_MUZZLE1]).sub(d.tag[TAG_ORIGIN]);
                vec forward(-sinf(d.yaw*RAD), cosf(d.yaw*RAD), 0);
                barrel.z = 0;
                if(barrel.squaredlen() <= 0 || barrel.safenormalize().dot(forward) <= 0.9f)
                    conoutf(colourwhite, "WEAPON_BAD_HEADING %s view %d team %d yaw %g", weaptype[weap].name, k, j, d.yaw);
                check(barrel.squaredlen() > 0 && barrel.dot(forward) > 0.9f, "barrel_faces_actor_aim");
            }
        }
        check(game::csgopenweaponmodel(W_GRENADE, 2) && game::csgopenweaponmodel(W_CORRODER, 2)
            && strcmp(game::csgopenweaponmodel(W_GRENADE, 2), game::csgopenweaponmodel(W_CORRODER, 2)), "distinct_grenade_projectiles");
        check(game::csgopenweaponmodel(W_MINE) == NULL && game::csgopenweaponmodel(W_CLAW) == NULL, "unmapped_weapons_preserved");
        gameent switcher;
        switcher.actortype = A_PLAYER;
        switcher.model = 0;
        switcher.state = CS_ALIVE;
        switcher.physstate = PHYS_FLOOR;
        switcher.weapammo[W_SMG][W_A_CLIP] = switcher.weapammo[W_MINE][W_A_CLIP] = 1;
        switcher.configure(lastmillis, game::gamemode, game::mutators);
        loopi(2)
        {
            switcher.weapselect = i ? W_MINE : W_SMG;
            switcher.lastweap.shrink(0);
            switcher.addlastweap(i ? W_SMG : W_MINE);
            switcher.weapstate[switcher.weapselect] = W_S_SWITCH;
            switcher.weaptime[switcher.weapselect] = lastmillis-10;
            switcher.weapwait[switcher.weapselect] = 400;
            modelstate mdl;
            modelattach links[VANITYMAX + ATTACHMENTMAX];
            const char *name = game::getplayerstate(&switcher, mdl, 0, switcher.curscale, 0, links, false);
            conoutf(colourwhite, "WEAPON_SWITCH_MODEL direction %d %s", i, name ? name : "none");
            check(name && (i ? strstr(name, "weapons/urbanterror/smg/") != NULL : !strcmp(name, playertypes[0][0])), "mixed_pack_weapon_switch");
            check(i ? !links[0].name : links[0].name && !strcmp(links[0].name, weaptype[W_MINE].hwep), "no_duplicate_hands_during_switch");
        }
        switcher.weapselect = W_SMG;
        switcher.weapstate[W_SMG] = W_S_RELOAD;
        switcher.weapwait[W_SMG] = 1800;
        modelstate reload;
        modelattach links[VANITYMAX + ATTACHMENTMAX];
        game::getplayerstate(&switcher, reload, 0, switcher.curscale, 0, links, false);
        check(game::weaponanimtimes[W_SMG][1] > 0 && fabsf(reload.speed*game::weaponanimtimes[W_SMG][1]-1800) < 0.01f, "reload_fits_server_timer");
        game::csgopenweaponmodels = 0;
        check(game::csgopenweaponmodel(W_SMG) == NULL, "disabled_pack_fallback");
        game::csgopenweaponmodels = 1;
        int enabled = csgopenweapons;
        csgopenweapons = 0;
        check(game::csgopenweaponmodel(W_SMG) == NULL, "original_profile_fallback");
        csgopenweapons = enabled;
        conoutf(colourwhite, "WEAPON_DONE FAILURES %d", failures);
    }
    ICOMMAND(0, weaponmodeltest, "", (), weapontest::run());

    void zoomtest()
    {
        failures = 0;
        gameent d;
        d.actortype = A_PLAYER;
        d.state = CS_ALIVE;
        d.configure(lastmillis, game::gamemode, game::mutators);
        loopi(6) loopj(3)
        {
            d.move = i == 2 || i == 3 || i == 5 ? 1 : 0;
            d.action[AC_WALK] = i == 2;
            d.action[AC_CROUCH] = i == 1 || i == 5;
            d.airmillis = i == 4 ? lastmillis : 0;
            d.weapbloom[W_ZAPPER] = j*0.5f;
            d.weapbloomtime[W_ZAPPER] = lastmillis;
            float plain = WSP(W_ZAPPER, false, game::gamemode, game::mutators, weapons::accmodspread(&d, W_ZAPPER, false, false));
            float scoped = WSP(W_ZAPPER, true, game::gamemode, game::mutators, weapons::accmodspread(&d, W_ZAPPER, true, true));
            check(fabsf(plain-scoped) < 0.00001f, "ak_zoom_preserves_posture_and_bloom_spread");
        }
        int oldweap = game::player1->weapselect, oldlevel = game::zoomlevel, oldlast = game::lastzoom;
        bool oldzoom = game::zooming;
        const int weapons[] = { W_FLAMER, W_ZAPPER, W_RIFLE };
        loopi(3)
        {
            game::player1->weapselect = weapons[i];
            game::lastzoom = lastmillis;
            game::zooming = true;
            game::zoomlevel = 2;
            game::setzoomlevel(1);
            check(game::zoomlevel == (i == 2 ? 3 : 2), "wheel_respects_fixed_and_variable_zoom");
        }
        game::player1->weapselect = oldweap;
        game::zoomlevel = oldlevel;
        game::lastzoom = oldlast;
        game::zooming = oldzoom;
        conoutf(colourwhite, "ZOOM_DONE FAILURES %d", failures);
    }
    ICOMMAND(0, weaponzoomtest, "", (), weapontest::zoomtest());

    // Drive the same action state as native input, without requiring a key
    // release binding in a scheduled CubeScript test.
    ICOMMAND(0, weaponmodelinput, "ii", (int *action, int *down),
    {
        if(*action >= 0 && *action < AC_MAX && game::allowmove(game::player1))
        {
            game::player1->action[*action] = *down != 0;
            if(*down) game::player1->actiontime[*action] = lastmillis;
        }
    });
    ICOMMAND(0, weaponmodelammo, "i", (int *weap), intret(isweap(*weap) ? game::player1->weapammo[*weap][W_A_CLIP] : -1));
    ICOMMAND(0, weaponmodelstate, "i", (int *weap), intret(isweap(*weap) ? game::player1->weapstate[*weap] : -1));

    // Screenshots of the actual avatar renderer and its animated hold parts.
    ICOMMAND(0, weaponmodelpose, "iii", (int *weap, int *state, int *elapsed),
    {
        if(isweap(*weap))
        {
            gameent *d = game::player1;
            d->weapselect = *weap;
            d->weapammo[*weap][W_A_CLIP] = W(*weap, ammoclip);
            d->weapstate[*weap] = clamp(*state, 0, W_S_MAX-1);
            d->weaptime[*weap] = lastmillis-*elapsed;
            d->weapwait[*weap] = *state == W_S_RELOAD ? W(*weap, delayreload) :
                (*state == W_S_PRIMARY || *state == W_S_SECONDARY ? W2(*weap, delayattack, *state == W_S_SECONDARY) : 10000);
            d->cleartags();
            loopi(MAXANIMPARTS) d->animinterp[i].reset();
        }
    });
}
