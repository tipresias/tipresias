export const presentNumber = (
  value: number | null,
  fractionDigits: number | undefined = undefined
) => (value === null ? "NA" : value.toFixed(fractionDigits));

export const presentPercentage = (
  value: number | null,
  fractionDigits: number = 2
) => (value === null ? "NA" : `${(value * 100).toFixed(fractionDigits)}%`);
