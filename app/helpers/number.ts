export const presentNumber = (value: number | null) =>
  value === null ? "NA" : value.toFixed(2);

export const presentPercentage = (value: number | null) =>
  value === null ? "NA" : `${(value * 100).toFixed(2)}%`;
