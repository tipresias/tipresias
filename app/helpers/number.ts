export const presentNumber = (value: number | null) =>
  value === null ? "NA" : value.toFixed(2);
