import React from 'react';

const Image = ({
  url,
  alt,
  width,
}) => (
    <img src={url} className="App-logo" alt={alt} width={width} />
  );

export default Image;
