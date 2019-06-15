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
query {
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
      predictions(mlModelName: "tipresias"){
        mlModel{
          name
        }
        predictedWinner{
          name
        }
        predictedMargin
        isCorrect
      }

    }
  }
}`;

export const FETCH_PREDICTION_YEARS_QUERY = gql`
  query {
    fetchPredictionYears
  }`;

export const FETCH_YEARLY_PREDICTIONS_QUERY = gql`
  query fetchYearlyPredictions($year: Int){
    fetchYearlyPredictions(year: $year){
      predictionModelNames
       predictionsByRound{
        roundNumber
        modelPredictions{
          modelName
          cumulativeCorrectCount
        }
      }
   }
  }`;
