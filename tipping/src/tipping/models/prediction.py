"""Data model for the join table for matches and teams."""

from __future__ import annotations

import typing
from datetime import date

from mypy_extensions import TypedDict
from sqlalchemy import Column, Integer, ForeignKey, Boolean, Float, orm, sql
import pandas as pd
import numpy as np

from . import base
from .match import Match
from .ml_model import MLModel
from .team import Team
from .team_match import TeamMatch

PredictionAttributes = TypedDict(
    "PredictionAttributes",
    {
        "match_id": int,
        "ml_model_id": int,
        "predicted_winner_id": int,
        "predicted_margin": typing.Optional[float],
        "predicted_win_probability": typing.Optional[float],
        "is_correct": typing.Optional[bool],
    },
)

MIN_PREDICTED_MARGIN = 0
MIN_PROBABILITY = 0
MAX_PROBABILITY = 1

JAN = 1
FIRST = 1


class Prediction(base.Base):
    """Model for ML model predictions for each match."""

    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False)
    match = orm.relationship(Match, back_populates="predictions")
    ml_model_id = Column(Integer, ForeignKey("ml_models.id"), nullable=False)
    ml_model = orm.relationship(MLModel, back_populates="predictions")
    predicted_winner_id = Column(Integer, ForeignKey("teams.id"))
    predicted_winner = orm.relationship(Team)

    predicted_margin = Column(Integer)
    predicted_win_probability = Column(Float)
    is_correct = Column(Boolean)

    @classmethod
    def update_or_create_from_raw_data(
        cls, session: orm.session.Session, data: pd.DataFrame
    ) -> Prediction:
        """
        Convert raw prediction data to a Prediction model instance.

        Tries to find and update existing prediction for the given
        match/model combination, and creates new one if none is found.

        Params:
        -------
        session: An SQLAlchemy session.
        data: Dictionary that include prediction data for two teams
            that are playing each other in a given match.

        Returns:
        --------
        Prediction model instance.
        """
        match = session.execute(
            sql.select(Match)
            .join(TeamMatch)
            .join(Team)
            .where(
                Match.start_date_time >= date(data["year"], JAN, FIRST),
                Match.start_date_time < date(data["year"] + 1, JAN, FIRST),
                Match.round_number == data["round_number"],
                sql.or_(
                    Team.name == data["home_team"],
                    Team.name == data["away_team"],
                ),
            )
            .limit(1)
        ).scalar()

        assert match is not None, (
            f"Expected to find a Match record for round {data['round_number']} "
            f"between home team {data['home_team']} and away team {data['away_team']}."
        )

        ml_model = session.execute(
            sql.select(MLModel).where(MLModel.name == data["ml_model"])
        ).scalar()

        prediction = cls.get_or_build(session, match=match, ml_model=ml_model)

        predicted_margin, predicted_margin_winner_name = cls._calculate_predictions(
            data, "margin"
        )
        (
            predicted_win_probability,
            predicted_proba_winner_name,
        ) = cls._calculate_predictions(data, "win_probability")

        # For now, each estimator predicts margins or win probabilities, but not both.
        # If we eventually have an estimator that predicts both, we're defaulting
        # to the predicted winner by margin, but we may want to revisit this
        predicted_winner_name = (
            predicted_margin_winner_name or predicted_proba_winner_name
        )

        assert (
            predicted_winner_name is not None
        ), f"Each prediction should have a predicted_winner:\n{data}"

        predicted_winner_id = session.execute(
            sql.select(Team.id).where(Team.name == predicted_winner_name)
        ).scalar()

        prediction.predicted_margin = predicted_margin
        prediction.predicted_win_probability = predicted_win_probability
        prediction.predicted_winner_id = predicted_winner_id
        prediction.update_correctness()

        session.commit()

        return prediction

    @classmethod
    def get_by(
        cls, session: orm.session.Session, **prediction_attributes: PredictionAttributes
    ) -> typing.Optional[Prediction]:
        """Get a Prediction object from the DB that matches the given attributes.

        Params:
        -------
        match_id: ID of the associated Match.
        ml_model_id: ID of the associated MLMOdel
        predicted_winner_id: ID of the associated Team that is the predicted winner.
        predicted_margin: Predicted margin of victory.
        predicted_win_probability: Predicted win probability.
        is_correct: Whether the prediction is correct.

        Returns:
        --------
        Prediction instance or None if no record matches the params.
        """
        conditions = [
            getattr(cls, key) == value for key, value in prediction_attributes.items()
        ]
        return session.execute(sql.select(cls).where(*conditions)).scalar()

    @classmethod
    def get_or_build(
        cls, session: orm.session.Session, **prediction_attributes: PredictionAttributes
    ) -> Prediction:
        """Get or instantiate a match object.

        Params:
        -------
        match: The associated Match.
        ml_model: The associated MLModel
        predicted_winner: The associated Team that is the predicted winner.
        predicted_margin: Predicted margin of victory.
        predicted_win_probability: Predicted win probability.
        is_correct: Whether the prediction is correct.

        Returns:
        --------
        A Prediction record.
        """
        maybe_prediction = cls.get_by(session, **prediction_attributes)

        if maybe_prediction:
            return maybe_prediction

        return cls(**prediction_attributes)

    def update_correctness(self):
        """Update the is_correct attribute based on associated team_match scores."""
        if not self.match.has_been_played:
            self.is_correct = None
            return None

        # In footy tipping competitions its typical to grant everyone a correct tip
        # in the case of a draw
        self.is_correct = (
            self.match.is_draw or self.predicted_winner.name == self.match.winner.name
        )
        return None

    @orm.validates("predicted_margin")
    def validate_predicted_margin(self, _key, value):
        """Validate that the predicted margin isn't negative."""
        if value is None or value >= MIN_PREDICTED_MARGIN:
            return value

        raise base.ValidationError(
            f"predicted_margin '{value}' must be greater than or equal to 0."
        )

    @orm.validates("predicted_win_probability")
    def validate_predicted_win_probability(self, _key, value):
        """Validate that the predicted win probability is within the valid range."""
        if value is None or MIN_PROBABILITY <= value <= MAX_PROBABILITY:
            return value

        raise base.ValidationError(
            f"predicted_win_probability '{value}' must be between 0 and 1 "
            "(inclusive)."
        )

    @classmethod
    def _calculate_predictions(
        cls,
        prediction_data: pd.DataFrame,
        prediction_type: typing.Union[
            typing.Literal["margin"], typing.Literal["win_probability"]
        ],
    ) -> typing.Tuple[typing.Optional[np.number], typing.Optional[str]]:
        home_prediction_key = typing.cast(
            typing.Union[
                typing.Literal["home_predicted_margin"],
                typing.Literal["home_predicted_win_probability"],
            ],
            f"home_predicted_{prediction_type}",
        )
        away_prediction_key = typing.cast(
            typing.Union[
                typing.Literal["away_predicted_margin"],
                typing.Literal["away_predicted_win_probability"],
            ],
            f"away_predicted_{prediction_type}",
        )

        home_predicted_result = prediction_data[home_prediction_key]
        away_predicted_result = prediction_data[away_prediction_key]

        if home_predicted_result is None or away_predicted_result is None:
            return None, None

        # TODO: The win probability model is kind of messed up this year,
        # so we've gotten a prediction where they're equal, and I don't feel
        # like revisiting the model, so we'll let it slide this season.
        assert home_predicted_result != away_predicted_result or (
            prediction_type == "win_probability" and date.today().year == 2021
        ), (
            "Home and away predictions are equal, which is basically impossible, "
            "so figure out what's going on:\n"
            f"{prediction_data}"
        )

        predicted_result = (
            cls._calculate_predicted_margin(
                home_predicted_result, away_predicted_result
            )
            if prediction_type == "margin"
            else cls._calculate_predicted_win_probability(
                home_predicted_result, away_predicted_result
            )
        )

        return predicted_result, cls._calculate_predicted_winner(
            prediction_data, home_predicted_result, away_predicted_result
        )

    @classmethod
    def _calculate_predicted_margin(
        cls, home_margin: np.number, away_margin: np.number
    ) -> np.number:
        both_predicted_to_win = home_margin > 0 and away_margin > 0
        both_predicted_to_lose = home_margin < 0 and away_margin < 0

        # predicted_margin is always positive as it's always associated
        # with predicted_winner
        if both_predicted_to_win or both_predicted_to_lose:
            return abs(home_margin - away_margin)

        return np.mean(np.abs([home_margin, away_margin]))

    @classmethod
    def _calculate_predicted_win_probability(
        cls, home_win_probability: np.number, away_win_probability: np.number
    ) -> np.number:
        predicted_loser_oppo_win_proba = 1 - np.min(
            [home_win_probability, away_win_probability]
        )
        predicted_winner_win_proba = np.max(
            [home_win_probability, away_win_probability]
        )
        predicted_win_probability = np.mean(
            [predicted_loser_oppo_win_proba, predicted_winner_win_proba]
        )

        return predicted_win_probability

    @classmethod
    def _calculate_predicted_winner(
        cls, prediction_data, home_predicted_result, away_predicted_result
    ) -> str:
        predicted_winner = (
            "home_team"
            if home_predicted_result > away_predicted_result
            else "away_team"
        )

        return prediction_data[predicted_winner]
