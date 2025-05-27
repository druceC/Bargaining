# Builds the fixed 9-player block in round 1
class SyncTop(BaseWaitPage):
    # Wait only for players in the current (forming) group
    wait_for_all_groups = False
    # Use arrival‑time grouping so we can grab exactly nine as they come
    group_by_arrival_time = True
    body_text = "Waiting for other participants to join..."

    # Show this page only in round 1
    def is_displayed(self):
        return self.round_number == 1

    @staticmethod
    def group_by_arrival_time_method(subsession, waiting_players):
        # Exclude any participants already flagged as drop‑outs
        eligible = [p for p in waiting_players
                    if not p.participant.vars.get("dropout", False)]

        group_size = 6
    
        # Proceed only when nine eligible players are present
        if len(eligible) >= group_size:
            # Randomly pick nine (shuffle gives unbiased order)
            selected = random.sample(eligible, group_size)

            # Create a shared identifier for this 9‑player “super‑group”
            group_id_9 = f"g9_{selected[0].id_in_subsession}"

            # Write group metadata into each participant’s vars for later rounds
            for p in selected:
                p.participant.vars["group_id_9"] = group_id_9
                p.participant.vars["group_members"] = [q.id_in_subsession for q in selected]

            # Server‑side debug log
            print(f"[DEBUG] round 1 – formed 9‑block {group_id_9}")

            # Returning the list lets oTree create this group and move on
            return selected

        # Fewer than nine → keep waiting
        return None

    # Handles actions before moving to the next page, including timeout handling. 
    @staticmethod
    def before_next_page(player, timeout_happened):
        # Access participant data
        participant = player.participant

        # If a player times out, mark them as a dropout
        if self.timeout_happened:
            participant.is_dropout = True   # Mark participant as dropped out
            player.dropout = True           # Mark player as dropped out