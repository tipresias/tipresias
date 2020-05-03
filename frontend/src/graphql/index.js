import { gql } from 'apollo-boost';
// eslint-disable-next-line import/prefer-default-export

// TODO: This query is no longer used, but is included in the specs
// for the App component, which are out of date.
// Update the tests and delete this.
export const FETCH_PREDICTIONS_QUERY = gql`
  query fetchPredictions($year: Int){
    fetchPredictions(year: $year) {
      id
      match {
        startDateTime
        roundNumber
        year
        teammatchSet {
          atHome
          team {
            name
          }
          score
        }
      }
      mlModel {
        name
      }
      predictedWinner {
        name
      }
      predictedMargin
      isCorrect
    }
  }`;

export const FETCH_LATEST_ROUND_PREDICTIONS_QUERY = gql`
query fetchLatestRoundPredictions{
  fetchLatestRoundPredictions {
    roundNumber
    matches {
      year
      startDateTime
      homeTeam{
        name
      }
      awayTeam{
        name
      }
      predictions{
        mlModel{
          name
          usedInCompetitions
          isPrinciple
        }
        predictedWinner{
          name
        }
        predictedMargin
        predictedWinProbability
        isCorrect
      }
    }
  }
}
`;

export const FETCH_SEASON_METRICS_QUERY = gql`
  query($season: Int, $roundNumber: Int, $forCompetitionOnly: Boolean) {
    fetchSeasonModelMetrics(season: $season){
      season
      roundModelMetrics(roundNumber: $roundNumber) {
        roundNumber
        modelMetrics(forCompetitionOnly: $forCompetitionOnly) {
          mlModel { name }
          cumulativeAccuracy
          cumulativeBits
          cumulativeMeanAbsoluteError
          cumulativeCorrectCount
          cumulativeMarginDifference
        }
      }
    }
  }
`;

export const FETCH_CHART_PARAMETERS_QUERY = gql`
  query fetchSeasonPerformanceChartParameters {
    fetchSeasonPerformanceChartParameters {
      availableSeasons
      availableMlModels {
        name
        isPrinciple
        usedInCompetitions
      }
    }
  }
`;
