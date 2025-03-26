    # Determine if the selected proposal is approved by majority vote
    def before_next_page(self):
        # if (voted_ctr == 3):
        votes = [p.vote for p in self.group.get_players() if p.vote is not None]      # Collect votes
        # votes = [self.player.vote if self.player.vote is not None else 0]
        self.group.approved = votes.count(True) >= 2            # Majority vote required

        # Print debug information in the terminal
        print(f"\n[DEBUG] Votes collected: {votes}")
        print(f"[DEBUG] Proposal Approved: {self.group.approved}\n")

        if self.group.approved:
            for p in self.group.get_players():
                p.earnings = self.group.selected_proposal  # Assign earnings if approved
        else:
            for p in self.group.get_players():
                p.earnings = 0                             # No earnings if rejected