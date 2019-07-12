from unittest import TestCase
from faker import Faker
import numpy as np

from machine_learning.data_processors.feature_functions import (
    add_result,
    add_margin,
    add_cum_percent,
    add_cum_win_points,
    add_ladder_position,
    add_win_streak,
    add_out_of_state,
    add_travel_distance,
    add_last_year_brownlow_votes,
    add_rolling_player_stats,
    add_cum_matches_played,
    add_elo_rating,
    add_betting_pred_win,
    add_elo_pred_win,
    add_shifted_team_features,
)
from machine_learning.data_config import VENUES
from tests.fixtures.data_factories import fake_cleaned_match_data

FAKE = Faker()
MATCH_COUNT_PER_YEAR = 10
YEAR_RANGE = (2015, 2016)
# Need to multiply by two, because we add team & oppo_team row per match
TOTAL_ROWS = MATCH_COUNT_PER_YEAR * len(range(*YEAR_RANGE)) * 2


def assert_column_added(
    test_case, column_names=[], valid_data_frame=None, feature_function=None, col_diff=1
):

    for column_name in column_names:
        with test_case.subTest(data_frame=valid_data_frame):
            data_frame = valid_data_frame
            transformed_data_frame = feature_function(data_frame)

            test_case.assertEqual(
                len(data_frame.columns) + col_diff, len(transformed_data_frame.columns)
            )
            test_case.assertIn(column_name, transformed_data_frame.columns)


def assert_required_columns(
    test_case, req_cols=[], valid_data_frame=None, feature_function=None
):
    for req_col in req_cols:
        with test_case.subTest(data_frame=valid_data_frame.drop(req_col, axis=1)):
            data_frame = valid_data_frame.drop(req_col, axis=1)
            with test_case.assertRaises(ValueError):
                feature_function(data_frame)


def make_column_assertions(
    test_case,
    column_names=[],
    req_cols=[],
    valid_data_frame=None,
    feature_function=None,
    col_diff=1,
):
    assert_column_added(
        test_case,
        column_names=column_names,
        valid_data_frame=valid_data_frame,
        feature_function=feature_function,
        col_diff=col_diff,
    )

    assert_required_columns(
        test_case,
        req_cols=req_cols,
        valid_data_frame=valid_data_frame,
        feature_function=feature_function,
    )


class TestFeatureFunctions(TestCase):
    def setUp(self):
        self.data_frame = fake_cleaned_match_data(MATCH_COUNT_PER_YEAR, YEAR_RANGE)

    def test_add_result(self):
        feature_function = add_result
        valid_data_frame = self.data_frame

        make_column_assertions(
            self,
            column_names=["result"],
            req_cols=("score", "oppo_score"),
            valid_data_frame=valid_data_frame,
            feature_function=feature_function,
        )

    def test_add_margin(self):
        feature_function = add_margin
        valid_data_frame = self.data_frame

        make_column_assertions(
            self,
            column_names=["margin"],
            req_cols=("score", "oppo_score"),
            valid_data_frame=valid_data_frame,
            feature_function=feature_function,
        )

    def test_add_cum_percent(self):
        feature_function = add_cum_percent
        valid_data_frame = self.data_frame.assign(
            prev_match_score=np.random.randint(50, 150, TOTAL_ROWS),
            prev_match_oppo_score=np.random.randint(50, 150, TOTAL_ROWS),
        )

        make_column_assertions(
            self,
            column_names=["cum_percent"],
            req_cols=("prev_match_score", "prev_match_oppo_score"),
            valid_data_frame=valid_data_frame,
            feature_function=feature_function,
        )

    def test_add_cum_win_points(self):
        feature_function = add_cum_win_points
        valid_data_frame = self.data_frame.assign(
            prev_match_result=np.random.randint(0, 2, TOTAL_ROWS)
        )

        make_column_assertions(
            self,
            column_names=["cum_win_points"],
            req_cols=("prev_match_result",),
            valid_data_frame=valid_data_frame,
            feature_function=feature_function,
        )

    def test_add_betting_pred_win(self):
        feature_function = add_betting_pred_win
        valid_data_frame = self.data_frame.assign(
            win_odds=np.random.randint(0, 2, TOTAL_ROWS),
            oppo_win_odds=np.random.randint(0, 2, TOTAL_ROWS),
            line_odds=np.random.randint(-50, 50, TOTAL_ROWS),
            oppo_line_odds=np.random.randint(-50, 50, TOTAL_ROWS),
        )

        make_column_assertions(
            self,
            column_names=["betting_pred_win"],
            req_cols=("win_odds", "oppo_win_odds", "line_odds", "oppo_line_odds"),
            valid_data_frame=valid_data_frame,
            feature_function=feature_function,
        )

    def test_add_elo_pred_win(self):
        feature_function = add_elo_pred_win
        valid_data_frame = self.data_frame.assign(
            elo_rating=np.random.randint(900, 1100, TOTAL_ROWS),
            oppo_elo_rating=np.random.randint(900, 1100, TOTAL_ROWS),
        )

        make_column_assertions(
            self,
            column_names=["elo_pred_win"],
            req_cols=("elo_rating", "oppo_elo_rating"),
            valid_data_frame=valid_data_frame,
            feature_function=feature_function,
        )

    def test_add_ladder_position(self):
        feature_function = add_ladder_position
        valid_data_frame = self.data_frame.assign(
            # Float from 0.5 to 2.0 covers most percentages
            cum_percent=(2.5 * np.random.ranf(TOTAL_ROWS)) - 0.5,
            cum_win_points=np.random.randint(0, 60, TOTAL_ROWS),
        )

        make_column_assertions(
            self,
            column_names=["ladder_position"],
            req_cols=("cum_percent", "cum_win_points", "team", "year", "round_number"),
            valid_data_frame=valid_data_frame,
            feature_function=feature_function,
        )

    def test_add_win_streak(self):
        feature_function = add_win_streak
        valid_data_frame = self.data_frame.assign(
            prev_match_result=np.random.randint(0, 2, TOTAL_ROWS)
        )

        make_column_assertions(
            self,
            column_names=["win_streak"],
            req_cols=("prev_match_result",),
            valid_data_frame=valid_data_frame,
            feature_function=feature_function,
        )

    def test_add_out_of_state(self):
        feature_function = add_out_of_state
        valid_data_frame = self.data_frame.assign(
            venue=[VENUES[idx % len(VENUES)] for idx in range(TOTAL_ROWS)]
        )

        make_column_assertions(
            self,
            column_names=["out_of_state"],
            req_cols=("venue", "team"),
            valid_data_frame=valid_data_frame,
            feature_function=feature_function,
        )

    def test_add_travel_distance(self):
        feature_function = add_travel_distance
        valid_data_frame = self.data_frame.assign(
            venue=[VENUES[idx % len(VENUES)] for idx in range(TOTAL_ROWS)]
        )

        make_column_assertions(
            self,
            column_names=["travel_distance"],
            req_cols=("venue", "team"),
            valid_data_frame=valid_data_frame,
            feature_function=feature_function,
        )

    def test_add_last_year_brownlow_votes(self):
        feature_function = add_last_year_brownlow_votes
        valid_data_frame = self.data_frame.assign(
            player_id=np.random.randint(100, 1000, TOTAL_ROWS),
            brownlow_votes=np.random.randint(0, 20, TOTAL_ROWS),
        )

        make_column_assertions(
            self,
            column_names=["last_year_brownlow_votes"],
            req_cols=("player_id", "year", "brownlow_votes"),
            valid_data_frame=valid_data_frame,
            feature_function=feature_function,
            col_diff=0,
        )

    def test_add_rolling_player_stats(self):
        STATS_COLS = [
            "player_id",
            "kicks",
            "marks",
            "handballs",
            "goals",
            "behinds",
            "hit_outs",
            "tackles",
            "rebounds",
            "inside_50s",
            "clearances",
            "clangers",
            "frees_for",
            "frees_against",
            "contested_possessions",
            "uncontested_possessions",
            "contested_marks",
            "marks_inside_50",
            "one_percenters",
            "bounces",
            "goal_assists",
            "time_on_ground",
        ]

        feature_function = add_rolling_player_stats
        valid_data_frame = self.data_frame.assign(
            **{
                stats_col: np.random.randint(0, 20, TOTAL_ROWS)
                for stats_col in STATS_COLS
            }
        )

        make_column_assertions(
            self,
            column_names=[
                f"rolling_prev_match_{stats_col}"
                for stats_col in STATS_COLS
                if stats_col != "player_id"
            ],
            req_cols=STATS_COLS,
            valid_data_frame=valid_data_frame,
            feature_function=feature_function,
            col_diff=0,
        )

    def test_add_cum_matches_played(self):
        feature_function = add_cum_matches_played
        valid_data_frame = self.data_frame.assign(
            player_id=np.random.randint(100, 1000, TOTAL_ROWS)
        )

        make_column_assertions(
            self,
            column_names=["cum_matches_played"],
            req_cols=("player_id",),
            valid_data_frame=valid_data_frame,
            feature_function=feature_function,
        )

    def test_add_elo_rating(self):
        feature_function = add_elo_rating
        valid_data_frame = self.data_frame.rename(
            columns={
                "team": "home_team",
                "oppo_team": "away_team",
                "score": "home_score",
                "oppo_score": "away_score",
            }
        )

        make_column_assertions(
            self,
            column_names=["home_elo_rating", "away_elo_rating"],
            req_cols=(
                "home_score",
                "away_score",
                "home_team",
                "away_team",
                "year",
                "date",
            ),
            valid_data_frame=valid_data_frame,
            feature_function=feature_function,
            col_diff=2,
        )

    def test_add_shifted_team_features(self):
        feature_function = add_shifted_team_features(shift_columns=["score"])
        valid_data_frame = self.data_frame.assign(team=FAKE.company())

        make_column_assertions(
            self,
            column_names=["prev_match_score"],
            req_cols=("score",),
            valid_data_frame=valid_data_frame,
            feature_function=feature_function,
        )

        shifted_data_frame = feature_function(valid_data_frame)
        self.assertEqual(shifted_data_frame["prev_match_score"].iloc[0], 0)
        self.assertEqual(
            shifted_data_frame["prev_match_score"].iloc[1],
            shifted_data_frame["score"].iloc[0],
        )

        with self.subTest("using keep_columns argument"):
            keep_columns = [col for col in self.data_frame if col != "score"]
            feature_function = add_shifted_team_features(keep_columns=keep_columns)
            valid_data_frame = self.data_frame.assign(team=FAKE.company())

            assert_column_added(
                self,
                column_names=["prev_match_score"],
                valid_data_frame=valid_data_frame,
                feature_function=feature_function,
            )

            shifted_data_frame = feature_function(valid_data_frame)
            self.assertEqual(shifted_data_frame["prev_match_score"].iloc[0], 0)
            self.assertEqual(
                shifted_data_frame["prev_match_score"].iloc[1],
                shifted_data_frame["score"].iloc[0],
            )
            prev_match_columns = [
                col for col in shifted_data_frame.columns if "prev_match" in col
            ]
            self.assertEqual(len(prev_match_columns), 1)
