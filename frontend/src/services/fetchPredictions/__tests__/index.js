import fetchPredictions from '../index';

describe('fetchPredictions', () => {
  it('renders', () => {
    // arrange
    // act
    // assert
    fetchPredictions().then((response) => {
      console.log(response);

      expect(true).toBe(true);
    });
  });
});
