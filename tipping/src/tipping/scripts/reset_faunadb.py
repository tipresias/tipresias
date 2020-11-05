# pylint: disable=wrong-import-position
"""One-off script to load existing data from Postgres DB dump to FaunaDB."""

from typing import Dict, List, Any
import os
import sys
import json

PROJECT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))

if PROJECT_PATH not in sys.path:
    sys.path.append(PROJECT_PATH)

from tipping.db.faunadb import FaunadbClient
from tipping import settings

RECORD_IDS: Dict[str, Dict[str, str]] = {
    "team": {},
    "teammatch": {},
    "match": {},
    "mlmodel": {},
    "prediction": {},
}


def _create_predictions(prediction_data, client):
    query = """
        mutation(
            $matchId: ID,
            $mlModelId: ID,
            $predictedWinnerId: ID,
            $predictedMargin: Float,
            $predictedWinProbability: Float,
            $isCorrect: Boolean
        ) {
            createPrediction(data: {
                match: { connect: $matchId },
                mlModel: { connect: $mlModelId },
                predictedWinner: { connect: $predictedWinnerId },
                predictedMargin: $predictedMargin,
                predictedWinProbability: $predictedWinProbability,
                isCorrect: $isCorrect
            }) { _id }
        }
    """

    for prediction in prediction_data:
        old_id = str(prediction["pk"])
        fields = prediction["fields"]
        match_id = RECORD_IDS["match"][str(fields["match"])]
        ml_model_id = RECORD_IDS["mlmodel"][str(fields["ml_model"])]
        predicted_winner_id = RECORD_IDS["team"][str(fields["predicted_winner"])]

        variables = {
            "matchId": match_id,
            "mlModelId": ml_model_id,
            "predictedWinnerId": predicted_winner_id,
            "predictedMargin": fields["predicted_margin"],
            "predictedWinProbability": fields["predicted_win_probability"],
            "isCorrect": fields["is_correct"],
        }

        result = client.graphql(query, variables=variables)
        new_id = result["createPrediction"]["_id"]

        RECORD_IDS["prediction"][old_id] = new_id


def _create_ml_models(ml_model_data, client):
    query = """
        mutation(
            $name: String!
            $description: String
            $isPrincipal: Boolean!
            $usedInCompetitions: Boolean!
            $predictionType: String!
        ) {
            createMlModel(data: {
                name: $name,
                description: $description,
                isPrincipal: $isPrincipal,
                usedInCompetitions: $usedInCompetitions,
                predictionType: $predictionType
            }) { _id }
        }
    """

    for ml_model in ml_model_data:
        old_id = str(ml_model["pk"])
        fields = ml_model["fields"]

        variables = {
            "name": fields["name"],
            "description": fields["description"],
            "isPrincipal": fields["is_principal"],
            "usedInCompetitions": fields["used_in_competitions"],
            "predictionType": fields["prediction_type"],
        }

        result = client.graphql(query, variables=variables)
        new_id = result["createMlModel"]["_id"]

        RECORD_IDS["mlmodel"][old_id] = new_id


def _create_team_matches(team_match_data, client):
    query = """
        mutation(
            $teamId: ID,
            $matchId: ID,
            $atHome: Boolean!,
            $score: Int!
        ) {
            createTeamMatch(data: {
                team: { connect: $teamId },
                match: { connect: $matchId },
                atHome: $atHome,
                score: $score
            }) { _id }
        }
    """

    for team_match in team_match_data:
        old_id = str(team_match["pk"])
        fields = team_match["fields"]
        team_id = RECORD_IDS["team"][str(fields["team"])]
        match_id = RECORD_IDS["match"][str(fields["match"])]

        variables = {
            "teamId": team_id,
            "matchId": match_id,
            "atHome": fields["at_home"],
            "score": fields["score"],
        }

        result = client.graphql(query, variables=variables)
        new_id = result["createTeamMatch"]["_id"]

        RECORD_IDS["teammatch"][old_id] = new_id


def _create_matches(match_data, client):
    query = """
        mutation(
            $startDateTime: Time!,
            $roundNumber: Int!,
            $venue: String!,
            $winnerId: ID,
            $margin: Int
        ) {
            createMatch(data: {
                startDateTime: $startDateTime,
                roundNumber: $roundNumber,
                venue: $venue,
                winner: { connect: $winnerId },
                margin: $margin
            }) { _id }
        }
    """

    for match in match_data:
        old_id = str(match["pk"])
        fields = match["fields"]

        variables = {
            "startDateTime": fields["start_date_time"],
            "roundNumber": fields["round_number"],
            "venue": fields["venue"],
            "margin": fields["margin"],
        }

        if fields["winner"] is None:
            query = """
                mutation(
                    $startDateTime: Time!,
                    $roundNumber: Int!,
                    $venue: String!,
                    $margin: Int
                ) {
                    createMatch(data: {
                        startDateTime: $startDateTime,
                        roundNumber: $roundNumber,
                        venue: $venue,
                        margin: $margin
                    }) { _id }
                }
            """
        else:
            query = """
                mutation(
                    $startDateTime: Time!,
                    $roundNumber: Int!,
                    $venue: String!,
                    $winnerId: ID,
                    $margin: Int
                ) {
                    createMatch(data: {
                        startDateTime: $startDateTime,
                        roundNumber: $roundNumber,
                        venue: $venue,
                        winner: { connect: $winnerId },
                        margin: $margin
                    }) { _id }
                }
            """
            winner_id = RECORD_IDS["team"][str(fields["winner"])]
            variables["winnerId"] = winner_id

        result = client.graphql(query, variables=variables)
        new_id = result["createMatch"]["_id"]

        RECORD_IDS["match"][old_id] = new_id


def _create_teams(team_data, client):
    query = """
        mutation($name: String!) {
            createTeam(data: { name: $name }) { _id }
        }
    """

    for team in team_data:
        old_id = str(team["pk"])
        fields = team["fields"]
        variables = {"name": fields["name"]}

        result = client.graphql(query, variables=variables)
        new_id = result["createTeam"]["_id"]

        RECORD_IDS["team"][old_id] = new_id


RecordDict = Dict[str, List[Dict[str, Any]]]


def _separate_data(data) -> RecordDict:
    separated_data: RecordDict = {
        "server.team": [],
        "server.teammatch": [],
        "server.match": [],
        "server.mlmodel": [],
        "server.prediction": [],
    }

    for record in data:
        model_name = record["model"]

        if model_name in separated_data.keys():
            separated_data[model_name].append(record)

    return separated_data


def main():
    """Load existing data from Postgres DB dump to FaunaDB."""
    client = FaunadbClient()
    client.import_schema(mode="override")

    data_filepath = os.path.join(settings.BASE_DIR, "server/db/backups/db_dump.json")
    with open(data_filepath, "r") as f:
        data = json.load(f)

    separated_models = _separate_data(data)

    # Creating records is order sensitive, as we create parent records first,
    # then children records
    _create_teams(separated_models["server.team"], client)
    _create_matches(separated_models["server.match"], client)
    _create_team_matches(separated_models["server.teammatch"], client)
    _create_ml_models(separated_models["server.mlmodel"], client)
    _create_predictions(separated_models["server.prediction"], client)


if __name__ == "__main__":
    main()
