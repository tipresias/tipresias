/* eslint-disable consistent-return */
/* eslint-disable camelcase */
// @flow
import type {
  fetchLatestRoundPredictions_fetchLatestRoundPredictions_matches as MatchType,
  fetchLatestRoundPredictions_fetchLatestRoundPredictions_matches_predictions as PredictionType,
} from '../../graphql/graphql-types/fetchLatestRoundPredictions';
import images from '../../images';

const { iconCheck, iconCross } = images;

type MatchesType = Array<MatchType>;

type RowType = Array<string | Object>;
type DataTableType = Array<RowType>;

const getPredictedMargin = (
  predictionsWithMargin: Array<PredictionType> | null,
) => {
  // loop the array of predictions and choose the predictedmargin value that is higher
  if (!predictionsWithMargin) return [];
  return predictionsWithMargin.reduce(
    (prevValue: number, currentItem: PredictionType) => {
      if (!currentItem.predictedMargin) return 0;
      return (
        currentItem.predictedMargin > prevValue ? currentItem.predictedMargin : prevValue
      );
    }, 0,
  );
};

const dataTransformerTable = (
  matches: MatchesType,
  principalModelName: string,
): DataTableType => {
  const newDataSet = matches.reduce((acc, matchItem, currentIndex) => {
    if (matchItem.predictions.length === 0) return [];

    acc[currentIndex] = acc[currentIndex] || [];

    const [date] = matchItem.startDateTime.split('T');
    acc[currentIndex][0] = date;

    // predicted Winner (form principalModel)
    const [predictionWithPrincipleModel] = matchItem.predictions.filter(
      (item: any) => (item && item.mlModel.name === principalModelName)
      ,
    );
    if (!predictionWithPrincipleModel) { return []; }
    acc[currentIndex][1] = predictionWithPrincipleModel.predictedWinner.name;

    // predictedMargin
    const predictionsWithValidMargin = matchItem.predictions.filter(
      (item: any) => item.mlModel.forCompetition === true && item.predictedMargin !== null,
    );
    acc[currentIndex][2] = getPredictedMargin(predictionsWithValidMargin);

    // predictedWinProbability
    const winProbabilityForCompetition = matchItem.predictions.filter(
      (item: any) => item.mlModel.forCompetition === true && item.predictedWinProbability !== null,
    );

    const predictedWinProbability = winProbabilityForCompetition
    && winProbabilityForCompetition.reduce(
      (prevValue: number, currentItem: PredictionType) => {
        if (!currentItem.predictedWinProbability) return 0;
        return currentItem.predictedWinProbability > prevValue
          ? currentItem.predictedWinProbability
          : prevValue;
      },
      0,
    );
    acc[currentIndex][3] = `${(Math.round(predictedWinProbability * 100)).toString()}%`;

    // isCorrect (form principalModel)
    const { isCorrect } = predictionWithPrincipleModel;
    acc[currentIndex][4] = isCorrect
      ? { svg: true, text: 'prediction is correct', path: iconCheck }
      : { svg: true, text: 'prediction is incorrect', path: iconCross };
    return acc;
  }, []);
  return newDataSet;
};
export default dataTransformerTable;
