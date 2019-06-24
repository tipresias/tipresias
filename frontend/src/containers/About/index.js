import React from 'react';
import AboutStyled from './style';

const About = () => (
  <AboutStyled>
    <h2>About Tipresias</h2>
    <p>A machine-learning model for predicting AFL match results through accessible Data visualizations.</p>
    <p>
      Team:
      <ul>
        <li>
          <a href="https://github.com/tipresias">Craig Franklin</a>
          (Backend developer)
        </li>
        <li>
          <a href="https://github.com/tipresias">Mel Gattoni</a>
          (Frontend developer)
        </li>
      </ul>
    </p>
  </AboutStyled>
);

export default About;
