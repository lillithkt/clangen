import random

from scripts.cat.cats import Cat, INJURIES
from scripts.cat.history import History
from scripts.events_module.generate_events import GenerateEvents
from scripts.utility import event_text_adjust, change_clan_relations, change_relationship_values, get_alive_kits
from scripts.game_structure.game_essentials import game
from scripts.event_class import Single_Event


# ---------------------------------------------------------------------------- #
#                               Death Event Class                              #
# ---------------------------------------------------------------------------- #

class Death_Events():
    """All events with a connection to conditions."""

    def __init__(self) -> None:
        self.event_sums = 0
        self.had_one_event = False
        self.generate_events = GenerateEvents()
        self.history = History()
        pass

    def handle_deaths(self, cat, other_cat, war, enemy_clan, alive_kits, murder=False):
        """ 
        This function handles the deaths
        """
        involved_cats = [cat.ID]
        other_clan = random.choice(game.clan.all_clans)
        other_clan_name = f'{other_clan.name}Clan'
        current_lives = int(game.clan.leader_lives)

        if other_clan_name == 'None':
            other_clan = game.clan.all_clans[0]
            other_clan_name = f'{other_clan.name}Clan'

        possible_short_events = self.generate_events.possible_short_events(cat.status, cat.age, "death")
        final_events = self.generate_events.filter_possible_short_events(possible_short_events, cat, other_cat, war,
                                                                         enemy_clan,
                                                                         other_clan, alive_kits, murder=murder)

        # ---------------------------------------------------------------------------- #
        #                                  kill cats                                   #
        # ---------------------------------------------------------------------------- #
        try:
            death_cause = (random.choice(final_events))
        except IndexError:
            print('WARNING: no death events found for', cat.name)
            return

        if murder:
            if "kit_manipulated" in death_cause.tags:
                kit = Cat.fetch_cat(random.choice(get_alive_kits(Cat)))
                print(get_alive_kits(Cat))
                print(kit)
                involved_cats.append(kit.ID)
                change_relationship_values([other_cat.ID],
                                           [kit],
                                           platonic_like=-20,
                                           dislike=40,
                                           admiration=-30,
                                           comfortable=-30,
                                           jealousy=0,
                                           trust=-30)
            if "revealed" in death_cause.tags:
                revealed = True
            else:
                revealed = False

            self.history.add_murders(cat, other_cat, revealed)

        # check if the cat's body was retrievable
        if "no_body" in death_cause.tags:
            body = False
        else:
            body = True

        if "war" in death_cause.tags and other_clan is not None and enemy_clan is not None:
            other_clan = enemy_clan
            other_clan_name = other_clan.name + "Clan"

        if "other_cat" and other_cat:
            involved_cats.append(other_cat.ID)

        # let's change some relationship values \o/ check if another cat is mentioned and if they live
        if "other_cat" in death_cause.tags and "multi_death" not in death_cause.tags:
            self.handle_relationship_changes(cat, death_cause, other_cat)

        death_text = event_text_adjust(Cat, death_cause.event_text, cat, other_cat, other_clan_name)
        history_text = 'this should not show up - history text'
        other_history_text = 'this should not show up - other_history text'

        # give history to cat if they die
        if "other_cat_death" not in death_cause.tags:
            if cat.status != "leader" \
                    and death_cause.history_text[0] is not None:
                history_text = event_text_adjust(Cat, death_cause.history_text[0], cat, other_cat, other_clan_name, keep_m_c=True)
            elif cat.status == "leader" \
                    and death_cause.history_text[1] is not None:
                history_text = event_text_adjust(Cat, death_cause.history_text[1], cat, other_cat, other_clan_name, keep_m_c=True)

            self.history.add_death_or_scars(cat, other_cat, history_text, death=True)

        # give death history to other cat if they die
        if "other_cat_death" in death_cause.tags or "multi_death" in death_cause.tags:
            if other_cat.status != "leader" and death_cause.history_text[0] is not None:
                other_history_text = event_text_adjust(Cat, death_cause.history_text[0], other_cat, cat,
                                                       other_clan_name, keep_m_c=True)
            elif other_cat.status == "leader" and death_cause.history_text[1] is not None:
                other_history_text = event_text_adjust(Cat, death_cause.history_text[1], other_cat, cat,
                                                       other_clan_name, keep_m_c=True)
            self.history.add_death_or_scars(other_cat, cat, other_history_text, death=True)

        # give injuries to other cat if tagged as such
        if "other_cat_injured" in death_cause.tags:
            for tag in death_cause.tags:
                if tag in INJURIES:
                    other_cat.get_injured(tag)
                    # TODO: consider how best to handle history for this (aka fix it later cus i don't wanna rn ;-;)

        # handle leader lives
        additional_event_text = ""
        if cat.status == "leader" and "other_cat_death" not in death_cause.tags:
            if "all_lives" in death_cause.tags:
                game.clan.leader_lives -= 10
                additional_event_text += cat.die(body)
            elif "some_lives" in death_cause.tags:
                game.clan.leader_lives -= random.randrange(2, current_lives - 1)
                additional_event_text += cat.die(body)
            else:
                game.clan.leader_lives -= 1
                additional_event_text += cat.die(body)
        else:
            if ("multi_death" in death_cause.tags or "other_cat_death" in death_cause.tags) \
                    and other_cat.status != 'leader':
                additional_event_text += other_cat.die(body)
            elif ("multi_death" in death_cause.tags or "other_cat_death" in death_cause.tags) \
                    and other_cat.status == 'leader':
                game.clan.leader_lives -= 1
                additional_event_text += other_cat.die(body)
            if "other_cat_death" not in death_cause.tags:
                additional_event_text += cat.die(body)

        if "rel_down" in death_cause.tags:
            difference = -5
            change_clan_relations(other_clan, difference=difference)

        elif "rel_up" in death_cause.tags:
            difference = 5
            change_clan_relations(other_clan, difference=difference)

        types = ["birth_death"]
        if "other_clan" in death_cause.tags:
            types.append("other_clans")
        game.cur_events_list.append(Single_Event(death_text + " " + additional_event_text, types, involved_cats))

    def handle_witness(self, cat, other_cat):
        """
        on hold until personality rework because i'd rather not have to figure this out a second time
        tentative plan is to have capability for a cat to witness the murder and then have a reaction based off trait
        """
        witness = None
        # choose the witness
        possible_witness = list(
            filter(
                lambda c: not c.dead and not c.exiled and not c.outside and
                (c.ID != cat.ID) and (c.ID != other_cat.ID), Cat.all_cats.values()))
        # If there are possible other cats...
        if possible_witness:
            witness = random.choice(possible_witness)
        if witness:
            # first, affect relationship
            change_relationship_values([other_cat],
                                       [witness.ID],
                                       romantic_love=-40,
                                       platonic_like=-40,
                                       dislike=50,
                                       admiration=-40,
                                       comfortable=-40,
                                       trust=-50
                                       )

    def handle_relationship_changes(self, cat, death_cause, other_cat):
        cat_to = None
        cat_from = None
        n = 20
        romantic = 0
        platonic = 0
        dislike = 0
        admiration = 0
        comfortable = 0
        jealousy = 0
        trust = 0
        if "rc_to_mc" in death_cause.tags:
            cat_to = [cat.ID]
            cat_from = [other_cat]
        elif "mc_to_rc" in death_cause.tags:
            cat_to = [other_cat.ID]
            cat_from = [cat]
        elif "to_both" in death_cause.tags:
            cat_to = [cat.ID, other_cat.ID]
            cat_from = [other_cat, cat]
        else:
            return
        if "romantic" in death_cause.tags:
            romantic = n
        elif "neg_romantic" in death_cause.tags:
            romantic = -n
        if "platonic" in death_cause.tags:
            platonic = n
        elif "neg_platonic" in death_cause.tags:
            platonic = -n
        if "dislike" in death_cause.tags:
            dislike = n
        elif "neg_dislike" in death_cause.tags:
            dislike = -n
        if "respect" in death_cause.tags:
            admiration = n
        elif "neg_respect" in death_cause.tags:
            admiration = -n
        if "comfort" in death_cause.tags:
            comfortable = n
        elif "neg_comfort" in death_cause.tags:
            comfortable = -n
        if "jealousy" in death_cause.tags:
            jealousy = n
        elif "neg_jealousy" in death_cause.tags:
            jealousy = -n
        if "trust" in death_cause.tags:
            trust = n
        elif "neg_trust" in death_cause.tags:
            trust = -n
        change_relationship_values(
            cat_to,
            cat_from,
            romantic,
            platonic,
            dislike,
            admiration,
            comfortable,
            jealousy,
            trust)
