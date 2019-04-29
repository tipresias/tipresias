import { gql } from "apollo-boost";

export const getPredictionsQuery = gql`
  query Predictions($year: Int){
    predictions(year: $year) {
      id
      match {
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
  }
`;