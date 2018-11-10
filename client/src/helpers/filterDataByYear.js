const filterDataByYear = (gamesData, year) => gamesData.filter(
  item => item.year === parseInt(year, 10),
);

export default filterDataByYear;
