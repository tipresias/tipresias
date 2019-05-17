// {
//   1: {
//     benchmark_estimator: {
//       roundArray: [{ … }, { … }, { … }, { … }, { … }, { … }, { … }, { … }, { … }]
//       total_points: 5
//     }
//     tipresias: {
//       roundArray: (9)[{ … }, { … }, { … }, { … }, { … }, { … }, { … }, { … }, { … }]
//       total_points: 5
//     }
//   },
//   2: {
//     benchmark_estimator: {
//       roundArray: [{ … }, { … }, { … }, { … }, { … }, { … }, { … }, { … }, { … }]
//       total_points: 5
//     }
//     tipresias: {
//       roundArray: (9)[{ … }, { … }, { … }, { … }, { … }, { … }, { … }, { … }, { … }]
//       total_points: 5
//     }
//   }
// }

// const current = [
//   [
//     { model: 'benchmark_estimator', cumulativeTotalPoints: 5 },
//     { model: 'tipresias', cumulativeTotalPoints: 5 },
//   ],
//   [
//     { model: 'benchmark_estimator', cumulativeTotalPoints: 13 },
//     { model: 'tipresias', cumulativeTotalPoints: 13 },
//   ],
//   [
//     { model: 'benchmark_estimator', cumulativeTotalPoints: 20 },

//     { model: 'tipresias', cumulativeTotalPoints: 21 },
//   ],
// ];

// const new = [
//   { round: '1', benchmark_estimator: 5, tipresias: 5 },
//   { round: '2', benchmark_estimator: 13, tipresias: 13 },
//   { round: '3', benchmark_estimator: 20, tipresias: 21 },
// ];


const createCumulativeModelsFlat = (modelsByRound) => {
  // const roundsArray = Object.keys(modelsByRound);
  // const modelsNamesArray = Object.keys(modelsByRound[0]);
  // const data = modelsByRound.reduce((acc, currentItem, currentIndex, array) => {

  // });

  // return data;
};

export default createCumulativeModelsFlat;


// const data = roundsArray.map((currentRound, index) => {
//   const cumulativeModels = modelsNamesArray.map((model) => {
//     const prevRound = parseInt(currentRound, 10) - 1;
//     const currentModel = modelsByRound[currentRound][model];
//     let prevModel;

//     if (index === 0) {
//       prevModel = { total_points: 0 };
//     }
//     prevModel = modelsByRound[prevRound][model];

//     const cumulativeTotalPoints = currentModel.total_points + prevModel.total_points;
//     currentModel.total_points = cumulativeTotalPoints;
//     return { model, cumulativeTotalPoints };
//   });
//   return cumulativeModels;
// });
