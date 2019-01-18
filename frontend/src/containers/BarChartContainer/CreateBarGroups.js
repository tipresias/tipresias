// @flow
import type {
  createBarGroupsArgs,
  Bar,
} from '../../types';

const createBarGroups = ({
  barWidth,
  xScale,
  yScale,
  colorScale,
  cumulativeModels,
}: createBarGroupsArgs): Array<Array<Bar>> => {
  const createCoordinates = ({ modelItem, modelItemIndex, roundItemIndex }) => {
    const x = xScale(roundItemIndex) + (barWidth * modelItemIndex);
    const y = yScale(modelItem.cumulativeTotalPoints);
    return { x, y };
  };

  const createDimensions = ({ modelItem }) => {
    const h = yScale(0) - yScale(modelItem.cumulativeTotalPoints);
    const w = barWidth;
    return { w, h };
  };

  const barsGroups = cumulativeModels.map((roundItem, roundItemIndex) => {
    const barsPerRound = roundItem.map((modelItem, modelItemIndex) => {
      const { x, y } = createCoordinates({ modelItem, modelItemIndex, roundItemIndex });
      const { w, h } = createDimensions({ modelItem });
      return ({
        key: `${roundItemIndex + 1}-${modelItem.model}`,
        round: roundItemIndex + 1,
        x: parseFloat(x),
        y,
        height: h,
        width: w,
        fill: colorScale(modelItem.model),
      });
    });
    return barsPerRound;
  });

  return barsGroups;
};

export default createBarGroups;
