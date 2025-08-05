# Fund Vanishes: oTree Experiment

This repo contains the code for an experimental economics game on group decision-making and resource division.

## Overview

The experiment explores how people negotiate over a shared pool of resources.

- **Participants**: Groups of 3 (randomly assigned)
- **Task**: Propose and vote on how to split 30 tokens  
  `4 tokens = 1 USD`
- **Two Stages Each Round**:
  1. **Proposal** – Each person submits a division of 30 tokens.
  2. **Voting** – A random proposal is picked. You can accept/reject. Majority vote (2/3) is needed. The proposer’s vote is auto-yes.
- **Outcomes**:
  - If approved: Tokens are divided and paid out.
  - If rejected: Tokens vanish. Everyone earns 0.
- **Rounds**: 3 rounds total, with reshuffling between each.
- **Payment**: Only 1 round is randomly selected to count for your actual earnings.
- **Ethics**: No deception — participants are fully informed. IRB-approved.

---

## Codebase

This is an oTree app built in Python with HTML templates. It includes two main apps: `fund_vanishes` and `filter_app`.

---

## ⚙Setup Instructions

1. Clone the repo  
   ```bash
   git clone https://github.com/druceC/Bargaining.git
   cd Bargaining

2. Create a virtual environment
    ```bash
    python -m venv venv
    source venv/bin/activate  # or venv\Scripts\activate on Windows

3. Install requirements
   ```bash
   pip install -r requirements.txt

4. Run the oTree server
   ```bash
   otree devserver

   
