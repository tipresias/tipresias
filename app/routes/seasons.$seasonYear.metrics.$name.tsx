import { json, LoaderFunctionArgs } from "@remix-run/node";
import { fetchRoundMetrics, isMetricName } from "~/.server/predictionService";

export const loader = async ({ params }: LoaderFunctionArgs) => {
  const { seasonYear, name } = params;

  if (!seasonYear || !isMetricName(name)) return json([], { status: 422 });

  const roundMetrics = await fetchRoundMetrics(parseInt(seasonYear), name);
  return json(roundMetrics);
};
