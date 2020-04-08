import { gql } from 'apollo-boost';
// eslint-disable-next-line import/prefer-default-export

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
          forCompetition
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

export const FETCH_YEARLY_PREDICTIONS_QUERY = gql`
  query fetchYearlyPredictions($year: Int){
    fetchYearlyPredictions(year: $year){
      predictionsByRound{
        roundNumber
        modelMetrics{
          modelName
          cumulativeAccuracy
          cumulativeBits
          cumulativeMeanAbsoluteError
        }
      }
    }
  }
`;

export const FETCH_LATEST_ROUND_STATS = gql`
  query fetchYearlyPredictions($year: Int, $roundNumber: Int, $mlModelName: String){
    fetchYearlyPredictions(year: $year){
      seasonYear
      predictionsByRound(roundNumber: $roundNumber){
        roundNumber
        modelMetrics(mlModelName: $mlModelName){
          modelName
          cumulativeCorrectCount
          cumulativeMeanAbsoluteError
          cumulativeMarginDifference
        }
      }
    }
  }
`;

export const FETCH_MODELS_AND_YEARS_QUERY = gql`
query {
  fetchPredictionYears
  fetchMlModels {
    name
    isPrinciple
    forCompetition
  }
  fetchYearlyPredictions{
    predictionsByRound{
      roundNumber
      modelMetrics{
        cumulativeBits
        cumulativeAccuracy
        cumulativeMeanAbsoluteError
      }
    }
  }
}
`;
