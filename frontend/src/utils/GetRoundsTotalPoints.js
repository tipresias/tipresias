const getRoundsTotalPoints = (rounds) => {
  const models = Object.keys(rounds[0]);
  const newRounds = rounds.reduce((acc, currentItem, currentIndex) => {
    acc[currentIndex] = acc[currentIndex] || {};

    models.forEach((model) => {
      acc[currentIndex][model] = currentItem[model].total_points;
    });
    return acc;
  }, []);
  return newRounds;
};
export default getRoundsTotalPoints;
