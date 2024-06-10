import { json, LoaderFunctionArgs } from "@remix-run/node";
import { fetchRoundPredictions } from "~/.server/predictionService";

export const loader = async ({ params }: LoaderFunctionArgs) => {
  const { seasonYear, roundNumber } = params;

  if (!seasonYear || !roundNumber) return json([], { status: 422 });

  const predictions = await fetchRoundPredictions(
    parseInt(seasonYear),
    parseInt(roundNumber)
  );
  return json(predictions);
};
