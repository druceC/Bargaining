import pandas as pd
import argparse
import os
import re
import warnings
from datetime import datetime

warnings.simplefilter(action='ignore', category=FutureWarning)

# Parse argumnet
parser = argparse.ArgumentParser(description="Generate payment, time, game, and survey CSVs from oTree export.")
parser.add_argument("datafile", help="Path to the all_apps_wide CSV file")
parser.add_argument("--fallback_round", type=int, default=3, help="Fallback round if none detected")
args = parser.parse_args()
df = pd.read_csv(args.datafile)
output_dir = os.path.dirname(args.datafile)

# Detect maximum round
completion_cols = [col for col in df.columns if "completion_code" in col.lower()]
round_numbers = [int(m.group(1)) for col in completion_cols if (m := re.search(r'fund_vanishes\.(\d+)\.player\.completion_code', col))]
max_round = max(round_numbers) if round_numbers else args.fallback_round

# ---------------------------
# PAYMENT CSV
# ---------------------------
def generate_payment():

    # Dynamically find the last non-null base_fee, bonus, and survey_fee for each participant
    base_fee_cols = [f"fund_vanishes.{r}.player.base_fee" for r in range(1, max_round + 1)]
    bonus_cols = [f"fund_vanishes.{r}.player.total_bonus" for r in range(1, max_round + 1)]
    survey_cols = [f"fund_vanishes.{r}.player.survey_fee" for r in range(1, max_round + 1)]

    # Select subset of columns to keep
    df_subset = df[[
        "participant.id_in_session",
        "participant.code",
        "participant._current_page_name",
    ] + base_fee_cols + bonus_cols + survey_cols + completion_cols].copy()

    # For each participant, take the last non-null (rightmost non-null) value across rounds
    df_subset["FixedFee"] = df_subset[base_fee_cols].bfill(axis=1).iloc[:, 0].fillna(0)
    df_subset["Bonus"] = df_subset[bonus_cols].bfill(axis=1).iloc[:, 0].fillna(0)
    df_subset["SurveyFee"] = df_subset[survey_cols].bfill(axis=1).iloc[:, 0].fillna(0)

    # Extract completion code
    df_subset["CompletionCode"] = df_subset[completion_cols].bfill(axis=1).iloc[:, 0]

    # Calculate total payment
    df_subset["TotalPayment"] = (
        df_subset["FixedFee"] + df_subset["Bonus"] + df_subset["SurveyFee"]
    )

    # Extract completion code
    df_subset["CompletionCode"] = df_subset[completion_cols].bfill(axis=1).iloc[:, 0]

    # Rename columns for better clarity
    df_subset.rename(columns={
        "participant.id_in_session": "SessionID",
        "participant.code": "ParticipantCode",
        "participant._current_page_name": "FinalPageVisited",
    }, inplace=True)

    # Export the final payment summary to CSV
    df_subset[[
        "SessionID", "ParticipantCode", "FinalPageVisited", "CompletionCode",
        "FixedFee", "Bonus", "SurveyFee", "TotalPayment"
    ]].to_csv(os.path.join(output_dir, "payment.csv"), index=False)
    print(f"✅ payment.csv generated using round {max_round}.")

# ---------------------------
# TIME CSV
# ---------------------------
def generate_time():
    game_start_col = f"fund_vanishes.1.player.game_start_time"
    game_end_col = f"fund_vanishes.{max_round}.player.game_end_time"
    experiment_end_col = f"fund_vanishes.{max_round}.player.experiment_end_time"
    exp_start_col = next((col for col in df.columns if re.match(r'filter_app\.\d+\.player\.experiment_start_time', col)), None)

    base_required_cols = [
        "participant.id_in_session",
        "participant.code",
        "participant._current_page_name"
    ]
    optional_time_cols = {
        exp_start_col: "ExperimentStartTime",
        game_start_col: "GameStartTime",
        game_end_col: "GameEndTime",
        experiment_end_col: "ExperimentEndTime"
    }
    valid_optional_cols = {k: v for k, v in optional_time_cols.items() if k in df.columns}
    df_subset = df[base_required_cols + list(valid_optional_cols.keys())].copy()
    df_subset.rename(columns={
        "participant.id_in_session": "SessionID",
        "participant.code": "ParticipantCode",
        "participant._current_page_name": "FinalPageVisited",
        **valid_optional_cols
    }, inplace=True)

    def safe_float(x):
        try: return float(x)
        except: return None

    def seconds_to_mmss(seconds):
        if seconds is None or pd.isna(seconds): return ""
        minutes = int(seconds) // 60
        secs = int(seconds) % 60
        return f"{minutes:02}:{secs:02}"

    df_subset["GameDuration"] = (df_subset.get("GameEndTime").apply(safe_float) - df_subset.get("GameStartTime").apply(safe_float)).apply(seconds_to_mmss)
    df_subset["ExperimentDuration"] = (df_subset.get("ExperimentEndTime").apply(safe_float) - df_subset.get("ExperimentStartTime").apply(safe_float)).apply(seconds_to_mmss)

    def convert_timestamp(ts):
        try: return datetime.utcfromtimestamp(float(ts)).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        except: return ts

    for col in ["ExperimentStartTime", "GameStartTime", "GameEndTime", "ExperimentEndTime"]:
        if col in df_subset.columns:
            df_subset[col] = df_subset[col].apply(convert_timestamp)

    df_subset.to_csv(os.path.join(output_dir, "time.csv"), index=False)
    print(f"✅ time.csv generated using round {max_round}.")

# ---------------------------
# GAME CSV
# ---------------------------
def generate_game():
    # Intialize list to store all row dictionaries for each player 
    records = []
    for _, row in df.iterrows():

        # Extract and store participant-level metadata
        base_data = {
            "SessionID": row.get("participant.id_in_session"),
            "ParticipantCode": row.get("participant.code"),
            "FinalPageVisited": row.get("participant._current_page_name"),
            "LastRoundPlayed": row.get(f"fund_vanishes.{max_round}.player.last_round_finished"),
            "GroupID": pd.to_numeric(row.get("fund_vanishes.1.player.group_id_9"), errors="coerce"),
            "ID_in_Group": row.get("fund_vanishes.1.player.id_in_group"),
            "Treatment": "Priming" if row.get("fund_vanishes.1.player.is_priming") == 1 else "Baseline",
        }


        for r in range(1, max_round + 1):
            # Extract round-specific variables
            round_data = {
                "Round": r,
                "SubgroupID": row.get(f"fund_vanishes.{r}.player.subgroup_id"),
                "ID_in_Subgroup": row.get(f"fund_vanishes.{r}.player.id_in_subgroup"),
                "S1": row.get(f"fund_vanishes.{r}.player.s1"),
                "S2": row.get(f"fund_vanishes.{r}.player.s2"),
                "S3": row.get(f"fund_vanishes.{r}.player.s3"),
                "Role": row.get(f"fund_vanishes.{r}.player.player_role"),
                "Selected_Proposal": row.get(f"fund_vanishes.{r}.group.selected_proposals_str"),
                "Vote": row.get(f"fund_vanishes.{r}.player.vote"),
                "Approved": row.get(f"fund_vanishes.{r}.group.approved"),
                "Num_of_Approvals": row.get(f"fund_vanishes.{r}.group.total_votes"),
                "Earnings": row.get(f"fund_vanishes.{r}.player.earnings"),
                "CompletionCode": row.get(f"fund_vanishes.{r}.player.completion_code")
            }

             # Overwrite role if proposal is empty
            if round_data["Selected_Proposal"] == '{}':
                round_data["Role"] = "NA"

            # Self proposal
            round_data["SelfProposal"] = max((p for p in [round_data["S1"], round_data["S2"], round_data["S3"]] if pd.notnull(p)), default=None)

            records.append({**base_data, **round_data})

    df_game = pd.DataFrame.from_records(records)
    df_game["GroupID"] = pd.to_numeric(df_game["GroupID"], errors="coerce").astype("Int64")

    # Define the desired column order
    desired_order = [
        "SessionID", "ParticipantCode", "FinalPageVisited", "LastRoundPlayed", "GroupID", "ID_in_Group", "Treatment", "Round", "SubgroupID", "ID_in_Subgroup",
        "S1", "S2", "S3", "SelfProposal", "Role", "Selected_Proposal", 
        "Vote", "Approved", "Num_of_Approvals", "Earnings", "CompletionCode"
    ]

    # Reorder the DataFrame columns
    df_game = df_game.reindex(columns=desired_order)
    df_game.to_csv(os.path.join(output_dir, "game.csv"), index=False)

    print(f"✅ game.csv generated with {len(df_game)} rows using round {max_round}.")

# ---------------------------
# SURVEY CSV
# ---------------------------
def generate_survey():
    form_fields = [
        'cmt_propr', 'cmt_vtr', 'age', 'sex', 'trans_1', 'trans_2',
        'power_q1a', 'power_q1b', 'power_q2', 'power_q3',
        'atq_1', 'atq_2', 'atq_3', 'econ', 'risk',
        'plop_unempl', 'plop_comp', 'plop_incdist', 'plop_priv',
        'plop_luckeffort', 'democracy_obedience', 'rel', 'rel_spec',
        'rel_other', 'gender_q1', 'gender_q2', 'gender_q3', 'gender_q4',
        'mwc', 'mwc_others', 'mwc_bonus', 'mwc_bonus_others',
        'social_power', 'wealth', 'authority', 'humble', 'influential',
        'retaliation', 'retaliation_other', 'bonus', 'enjoy'
    ]
    records = []
    for _, row in df.iterrows():
        record = {
            "SessionID": row.get("participant.id_in_session"),
            "ParticipantCode": row.get("participant.code"),
            "FinalPageVisited": row.get("participant._current_page_name"),
            "Treatment": "Priming" if row.get("fund_vanishes.1.player.is_priming") == 1 else "Baseline",
        }
        for field in form_fields:
            for r in range(1, max_round + 1):
                val = row.get(f"fund_vanishes.{r}.player.{field}")
                if pd.notnull(val):
                    record[field] = val
                    break
        records.append(record)

    df_survey = pd.DataFrame.from_records(records)
    df_survey.to_csv(os.path.join(output_dir, "survey.csv"), index=False)
    print(f"✅ survey.csv generated with {len(df_survey)} rows using round {max_round}.")


# Main calls
generate_payment()
generate_time()
generate_game()
generate_survey()
