// @flow
import type {
  fetchLatestRoundPredictions_fetchLatestRoundPredictions_matchPredictions as MatchPredictionType,
} from '../../graphql/graphql-types/fetchLatestRoundPredictions';
import icons from '../../icons';

const { iconCheck, iconCross, iconQuestion } = icons;

type MatchPredictionsType = Array<MatchPredictionType>;
type svgIcon = { svg: boolean, text: string, path: string }
type RowType = Array<string | svgIcon>;
type DataTableType = Array<RowType>;

const determineResultIcon = (isCorrect: ?boolean) => {
  if (isCorrect) {
    return { svg: true, text: 'prediction was correct', path: iconCheck };
  }

  return isCorrect === false
    ? { svg: true, text: 'prediction was incorrect', path: iconCross }
    : { svg: true, text: 'result is unknown', path: iconQuestion };
};

const dataTransformerTable = (
  matchPredictions: MatchPredictionsType,
): DataTableType => {
  const newDataSet = matchPredictions.reduce((acc, {
    startDateTime, predictedWinner, predictedMargin, predictedWinProbability, isCorrect,
  }, currentIndex) => {
    acc[currentIndex] = acc[currentIndex] || [];

    const [date] = startDateTime.split('T');
    const formattedWinProbability = `
      ${(Math.round(predictedWinProbability * 100)).toString()}%
    `;
    const resultIcon = determineResultIcon(isCorrect);

    acc[currentIndex] = [
      date,
      predictedWinner,
      predictedMargin.toString(),
      formattedWinProbability,
      resultIcon,
    ];

    return acc;
  }, []);
  return newDataSet;
};
export default dataTransformerTable;
