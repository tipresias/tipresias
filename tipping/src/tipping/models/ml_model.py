"""Data model for AFL ml_models."""

from __future__ import annotations
from typing import Optional, Dict, Any, Sequence

import numpy as np

from .base_model import BaseModel, ValidationError


class _MLModelRecordCollection:
    """Collection of MLModel objects associated with records in FaunaDB."""

    def __init__(self, records: Sequence[Optional[MLModel]]):
        """
        Params:
        -------
        records: List of MLModel objects created from FaunaDB ML model records.
        """
        self.records = records

    def count(self) -> int:
        """Get the number of model objects in the collection.

        Returns:
        --------
        Count of records.
        """
        return len(self.records)

    def filter(self, **kwargs) -> _MLModelRecordCollection:
        """Filter collection objects by attribute values.

        Params:
        -------
        Attribute key/value pairs.

        Returns:
        --------
        The filtered collection.
        """
        filtered_records = [
            record
            for record in self.records
            if self._attributes_match(record, **kwargs)
        ]

        return self.__class__(records=filtered_records)

    @staticmethod
    def _attributes_match(record, **kwargs) -> bool:
        return all([getattr(record, key) == val for key, val in kwargs.items()])

    def __len__(self):
        return len(self.records)

    def __iter__(self):
        return (record for record in self.records)

    def __array__(self):
        return np.array(list(self.records))

    def __getitem__(self, key):
        return self.records[key]


class MLModel(BaseModel):
    """Data model for ML models."""

    PREDICTION_TYPES = ("margin", "win_probability")

    def __init__(
        self,
        name: Optional[str] = None,
        is_principal: Optional[bool] = None,
        used_in_competitions: Optional[bool] = None,
        prediction_type: Optional[str] = None,
    ):  # pylint: disable=redefined-builtin
        """
        Params:
        -------
        name: Name of the ML model.
        is_principal: Whether it's the principal model for determining predicted winners.
        used_in_competitions: Whether it's used for predictions submitted
            to tipping competitions.
        prediction_type: Label for type of prediction: margin or win_probability
        """
        super().__init__()

        self.name = name
        self.is_principal = is_principal
        self.used_in_competitions = used_in_competitions
        self.prediction_type = prediction_type

    @classmethod
    def from_db_response(cls, record: Dict[str, Any]) -> MLModel:
        """Convert a DB record object into an instance of MLModel.

        Params:
        -------
        record: GraphQL response dictionary that represents the ml_model record.

        Returns:
        --------
        A MLModel with the attributes of the ml_model record.
        """
        ml_model = MLModel(
            name=record["name"],
            is_principal=record["isPrincipal"],
            used_in_competitions=record["usedInCompetitions"],
            prediction_type=record["predictionType"],
        )
        ml_model.id = record["_id"]

        return ml_model

    @classmethod
    def all(cls) -> _MLModelRecordCollection:
        """Fetch all MLModel records from the DB."""
        query = """
            query {
                allMLModels {
                    data {
                        _id
                        name
                        isPrincipal
                        usedInCompetitions
                        predictionType
                    }
                }
            }
        """

        result = cls.db_client().graphql(query)
        records = [
            cls.from_db_response(ml_model_record)
            for ml_model_record in result["allMLModels"]["data"]
        ]

        return _MLModelRecordCollection(records=records)

    @classmethod
    def find_by_name(cls, name: Optional[str] = None) -> Optional[MLModel]:
        """Fetch an ML model from the DB by name.

        Params:
        -------
        name: Name of the ML model to be fetched.

        Returns:
        --------
        An MLModel with the given name.
        """
        query = """
            query($name: String) {
                findMLModelByName(name: $name) {
                    _id
                    name
                    isPrincipal
                    predictionType
                    usedInCompetitions
                }
            }
        """
        variables = {"name": name}

        result = cls.db_client().graphql(query, variables)

        return cls.from_db_response(result["findMLModelByName"])

    def create(self) -> MLModel:
        """Create the ml_model in the DB."""
        self.validate()
        self._validate_one_principal_model()
        self._validate_unique_competition_prediction_types()

        query = """
            mutation(
                $name: String!
                $isPrincipal: Boolean!
                $usedInCompetitions: Boolean!
                $predictionType: String!
            ) {
                createMLModel(data: {
                    name: $name,
                    isPrincipal: $isPrincipal,
                    usedInCompetitions: $usedInCompetitions,
                    predictionType: $predictionType
                }) {
                    _id
                }
            }
        """
        variables = {
            "name": self.name,
            "isPrincipal": self.is_principal,
            "usedInCompetitions": self.used_in_competitions,
            "predictionType": self.prediction_type,
        }

        result = self.db_client().graphql(query, variables)
        self.id = result["createMLModel"]["_id"]

        return self

    def _validate_one_principal_model(self):
        if not self.is_principal:
            return

        query = """
            query {
                findMLModelByIsPrincipal(isPrincipal: true) { _id }
            }
        """

        result = self.db_client().graphql(query)
        principal_model = result["findMLModelByIsPrincipal"]

        if principal_model is None or principal_model["_id"] == self.id:
            return None

        raise ValidationError("duplicate principal ML models not allowed")

    def _validate_unique_competition_prediction_types(self):
        if not self.used_in_competitions:
            return

        query = """
            query {
                filterMLModelsBy(usedInCompetitions: true) {
                    data { _id }
                }
            }
        """

        result = self.db_client().graphql(query)
        competition_models = result["filterMLModelsBy"]["data"]

        if not any(competition_models) or {"_id": self.id} in competition_models:
            return None

        raise ValidationError("duplicate prediction types not allowed for competitions")

    @property
    def _schema(self):
        return {
            "name": {
                "type": "string",
                "empty": False,
            },
            "is_principal": {
                "type": "boolean",
            },
            "used_in_competitions": {
                "type": "boolean",
            },
            "prediction_type": {"type": "string", "allowed": self.PREDICTION_TYPES},
        }
