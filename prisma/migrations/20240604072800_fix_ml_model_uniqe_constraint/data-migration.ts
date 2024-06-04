import { Prisma, PrismaClient } from "@prisma/client";
import * as R from "ramda";

interface PredictedYear {
  year: number;
}

const PREDICTED_YEARS_SQL = `
  SELECT EXTRACT(YEAR FROM "startDateTime") AS year FROM "Match"
  INNER JOIN "Prediction" ON "Prediction"."matchId" = "Match".id
  GROUP BY year
  ORDER BY year
`;

const ML_MODEL_USAGE = {
  footy_tipper: {
    2018: {
      isPrincipal: true,
      isUsedInCompetitions: true,
    },
  },
  tipresias_2019: {
    2019: {
      isPrincipal: true,
      isUsedInCompetitions: true,
    },
  },
  tipresias_margin_2020: {
    2020: {
      isPrincipal: true,
      isUsedInCompetitions: true,
    },
  },
  tipresias_proba_2020: {
    2020: {
      isPrincipal: false,
      isUsedInCompetitions: true,
    },
  },
  tipresias_margin_2021: {
    2021: {
      isPrincipal: true,
      isUsedInCompetitions: true,
    },
    2022: {
      isPrincipal: true,
      isUsedInCompetitions: true,
    },
  },
  tipresias_proba_2021: {
    2021: {
      isPrincipal: false,
      isUsedInCompetitions: true,
    },
  },
};

const prisma = new PrismaClient();

async function main() {
  await prisma.$transaction(async (tx) => {
    const predictedYears = await tx.$queryRaw<PredictedYear[]>(
      Prisma.sql([PREDICTED_YEARS_SQL])
    );
    await tx.season.createMany({
      data: predictedYears,
    });

    const seasons = await tx.season.findMany();
    const mlModels = await tx.mlModel.findMany();
    const mlModelSeasons = await Promise.all(
      seasons.map(async ({ id: seasonId, year }) => {
        await tx.match.updateMany({
          where: {
            startDateTime: {
              gte: new Date(Date.UTC(year)),
              lt: new Date(Date.UTC(year + 1)),
            },
          },
          data: {
            seasonId,
          },
        });

        return mlModels.map(({ id: mlModelId, name }) => ({
          seasonId,
          mlModelId,
          isPrincipal: R.path<boolean>(
            [name, year, "isPrincipal"],
            ML_MODEL_USAGE
          ),
          isUsedInCompetitions: R.path<boolean>(
            [name, year, "isUsedInCompetitions"],
            ML_MODEL_USAGE
          ),
        }));
      })
    );

    await tx.mlModelSeason.createMany({ data: R.flatten(mlModelSeasons) });
  });
}

main()
  .catch(async (e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(async () => await prisma.$disconnect());
