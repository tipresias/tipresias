const createCumulativeModelsFlat = (rounds) => {
  const models = Object.keys(rounds[0]);
  const data = rounds.reduce((roundsAcc, currentItem, currentIndex) => {
    const newCurrentItem = { ...currentItem };

    models.forEach((model) => {
      const prevIndex = currentIndex - 1;
      if (prevIndex < 0) {
        newCurrentItem[model] += 0;
      } else {
        newCurrentItem[model] += roundsAcc[prevIndex][model];
      }
    });

    newCurrentItem.round = currentIndex + 1;

    roundsAcc.push(newCurrentItem);

    return roundsAcc;
  }, []);

  return data;
};

export default createCumulativeModelsFlat;
