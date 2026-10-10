// Opt-in native integration client: replace game/game.o, never link both.
#include "../game/game.cpp"

namespace soldiertest
{
    int failures = 0;

    void check(bool ok, const char *label)
    {
        if(!ok) failures++;
        conoutf(colourwhite, "SOLDIER_CHECK_%s %s", ok ? "PASS" : "FAIL", label);
    }

    ICOMMAND(0, soldierstest, "", (),
    {
        int enabled = game::csgopensoldiers;
        check(enabled == 1, "local_pack_enabled");
        loopi(PLAYERTYPES) loopj(2)
        {
            gameent d;
            d.actortype = A_PLAYER;
            d.model = i;
            d.team = j ? T_OMEGA : T_ALPHA;
            d.state = CS_ALIVE;
            d.physstate = PHYS_FLOOR;
            d.weapselect = W_SMG;
            d.weapammo[W_SMG][W_A_CLIP] = 64;
            d.configure(lastmillis, game::gamemode, game::mutators);
            modelstate mdl;
            modelattach attachments[VANITYMAX + ATTACHMENTMAX];
            const char *name = game::getplayerstate(&d, mdl, 1, d.curscale, 0, attachments, false);
            check(name && strstr(name, "actors/soldier/"), "third_person_soldier");
            check(name && strstr(name, j ? "/omega" : "/alpha"), "team_uniform");
            check(name && strstr(name, i ? "/athena/" : "/orion/"), "selected_body");
            check(attachments[0].tag && !strcmp(attachments[0].tag, "tag_weapon"), "weapon_attachment");
            // Resolve the real model/tag transforms, including MD3 Y reflection
            // and the soldier's yaw offset. Checking the tag name alone misses
            // a sideways weapon attachment.
            int weapons[3];
            weapons[0] = W_PISTOL;
            weapons[1] = W_SMG;
            weapons[2] = W_RIFLE;
            loopk(int(sizeof(weapons)/sizeof(weapons[0]))) loopl(4)
            {
                d.weapselect = weapons[k];
                d.weapammo[weapons[k]][W_A_CLIP] = 1;
                d.yaw = l*90.f;
                d.pitch = d.roll = 0;
                loopm(TAG_MAX) d.tag[m] = vec(-1);
                loopm(MAXANIMPARTS) d.animinterp[m].reset();
                modelstate pose;
                modelattach links[VANITYMAX + ATTACHMENTMAX];
                const char *body = game::getplayerstate(&d, pose, 1, d.curscale, MDL_NORENDER|MDL_NOBATCH, links, false);
                pose.attached = links;
                rendermodel(body, pose, &d);
                vec barrel = vec(d.tag[TAG_MUZZLE1]).sub(d.tag[TAG_ORIGIN]);
                vec forward(-sinf(d.yaw*RAD), cosf(d.yaw*RAD), 0);
                // The grip is below the barrel. Compare horizontal heading,
                // rather than treating that muzzle height as weapon pitch.
                barrel.z = 0;
                check(d.tag[TAG_MUZZLE1] != vec(-1) && d.tag[TAG_ORIGIN] != vec(-1)
                    && barrel.squaredlen() > 0 && barrel.safenormalize().dot(forward) > 0.95f, "barrel_faces_actor_aim");
            }
            bool hasvanity = false;
            loopk(VANITYMAX + ATTACHMENTMAX) if(attachments[k].name && strstr(attachments[k].name, "vanities/")) hasvanity = true;
            check(!hasvanity, "no_incompatible_cosmetics");
            const char *first = game::getplayerstate(&d, mdl, 0, d.curscale, 0, NULL, false);
            check(first && !strcmp(first, playertypes[i][0]), "first_person_arms_preserved");
            d.actortype = A_BOT;
            check(game::soldiermodel(&d) != NULL, "bot_soldier");
            d.state = CS_DEAD;
            game::getplayerstate(&d, mdl, 1, d.curscale, 0, NULL, false);
            check(!(mdl.anim&ANIM_RAGDOLL), "vertex_animated_death");
            game::csgopensoldiers = 0;
            name = game::getplayerstate(&d, mdl, 1, d.curscale, 0, NULL, false);
            check(name && !strcmp(name, playertypes[i][1]), "disabled_pack_fallback");
            game::csgopensoldiers = enabled;
        }
        gameent other;
        other.actortype = A_GRUNT;
        check(game::soldiermodel(&other) == NULL, "non_player_actor_preserved");
        int weapons = csgopenweapons;
        csgopenweapons = 0;
        other.actortype = A_PLAYER;
        check(game::soldiermodel(&other) == NULL, "original_rules_fallback");
        csgopenweapons = weapons;
        conoutf(colourwhite, "SOLDIER_DONE FAILURES %d", failures);
    });
}
