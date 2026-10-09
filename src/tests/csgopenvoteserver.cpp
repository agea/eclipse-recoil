// Opt-in dedicated integration server; production binaries expose no test command.
#include "../game/server.cpp"

namespace votetest
{
    int failures = 0;

    void check(bool ok, const char *name)
    {
        if(!ok) failures++;
        logoutf("VOTE_CHECK_%s %s", ok ? "PASS" : "FAIL", name);
    }

    void run()
    {
        using namespace server;
        failures = 0;
        if(!clients.empty())
        {
            check(false, "requires_empty_test_server");
            return;
        }
        sv_votestyle = 3;
        sv_votefilter = 1;
        sv_votechoices = 0;
        loopi(6)
        {
            int present = i+1;
            loopj(present)
            {
                clientinfo *ci = new clientinfo;
                ci->clientnum = j;
                ci->actortype = A_PLAYER;
                ci->state = j%2 ? CS_SPECTATOR : CS_ALIVE;
                clients.add(ci);
            }
            setphase(G_S_PLAYING);
            gamemode = G_DEATHMATCH;
            mutators = 0;
            loopj(present/2)
            {
                copystring(clients[j]->mapvote, "echo");
                clients[j]->modevote = gamemode;
                clients[j]->mutsvote = mutators;
            }
            check(!checkvotes(), "half_or_less_does_not_pass_including_spectators");
            clientinfo *next = clients[present/2];
            copystring(next->mapvote, "echo");
            next->modevote = gamemode;
            next->mutsvote = mutators;
            check(checkvotes(), "strict_majority_passes_for_one_to_six_humans");
            check(!strcmp(smapname, "echo") && gamestate == G_S_WAITING, "immediate_change_to_selected_map");
            clients.deletecontents();
        }

        // Conflicting destinations do not combine into a majority.
        loopi(4)
        {
            clientinfo *ci = new clientinfo;
            ci->clientnum = i;
            ci->actortype = i == 3 ? A_BOT : A_PLAYER;
            ci->state = CS_SPECTATOR;
            copystring(ci->mapvote, i == 1 ? "park" : "echo");
            ci->modevote = G_DEATHMATCH;
            ci->mutsvote = 0;
            clients.add(ci);
        }
        setphase(G_S_OVERTIME);
        clients[2]->mapvote[0] = '\0';
        check(!checkvotes(), "split_votes_and_bot_vote_do_not_pass");
        delete clients.remove(3);
        copystring(clients[2]->mapvote, "echo");
        check(checkvotes(), "two_of_three_pass_in_overtime");
        clients.deletecontents();

        // Existing intermission styles retain their separate semantics.
        clientinfo *ci = new clientinfo;
        ci->clientnum = 0;
        ci->actortype = A_PLAYER;
        copystring(ci->mapvote, "echo");
        ci->modevote = G_DEATHMATCH;
        ci->mutsvote = 0;
        clients.add(ci);
        sv_voteinterm = 0;
        setphase(G_S_VOTING);
        check(!checkvotes(), "intermission_style_zero_waits");
        sv_voteinterm = 3;
        check(!checkvotes(), "intermission_random_style_waits");
        check(checkvotes(true), "intermission_random_style_passes_when_forced");
        clients.deletecontents();
        logoutf("VOTE_DONE FAILURES %d", failures);
    }

    ICOMMAND(0, voteservertest, "", (), votetest::run());
}
