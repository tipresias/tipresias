/*
  Warnings:

  - You are about to drop the `server_match` table. If the table is not empty, all the data it contains will be lost.
  - You are about to drop the `server_mlmodel` table. If the table is not empty, all the data it contains will be lost.
  - You are about to drop the `server_prediction` table. If the table is not empty, all the data it contains will be lost.
  - You are about to drop the `server_team` table. If the table is not empty, all the data it contains will be lost.
  - You are about to drop the `server_teammatch` table. If the table is not empty, all the data it contains will be lost.

*/
-- DropForeignKey
ALTER TABLE "server_match" DROP CONSTRAINT "server_match_winner_id_8e4d5c8a_fk_server_team_id";

-- DropForeignKey
ALTER TABLE "server_prediction" DROP CONSTRAINT "server_prediction_match_id_00aaa745_fk_server_match_id";

-- DropForeignKey
ALTER TABLE "server_prediction" DROP CONSTRAINT "server_prediction_ml_model_id_3de99081_fk_server_mlmodel_id";

-- DropForeignKey
ALTER TABLE "server_prediction" DROP CONSTRAINT "server_prediction_predicted_winner_id_7487ef4f_fk_server_te";

-- DropForeignKey
ALTER TABLE "server_teammatch" DROP CONSTRAINT "server_teammatch_match_id_d0498fdb_fk_server_match_id";

-- DropForeignKey
ALTER TABLE "server_teammatch" DROP CONSTRAINT "server_teammatch_team_id_9a0c00f1_fk_server_team_id";

-- AlterTable
ALTER TABLE "server_match"
  RENAME TO "Match";
ALTER TABLE "Match"
  RENAME COLUMN "start_date_time" TO "startDateTime";
ALTER TABLE "Match"
  RENAME COLUMN "round_number" TO "roundNumber";
ALTER TABLE "Match"
  RENAME COLUMN "winner_id" TO "winnerId";
ALTER TABLE "Match"
  ALTER COLUMN "roundNumber" SET DATA TYPE INTEGER,
  ALTER COLUMN "venue" SET DATA TYPE TEXT,
  DROP CONSTRAINT "server_match_pkey",
  ADD CONSTRAINT "Match_pkey" PRIMARY KEY ("id");

-- AlterTable
ALTER TABLE "server_mlmodel"
  RENAME TO "MlModel";
ALTER TABLE "MlModel"
  RENAME COLUMN "is_principal" TO "isPrincipal";
ALTER TABLE "MlModel"
  RENAME COLUMN "prediction_type" TO "predictionType";
ALTER TABLE "MlModel"
  RENAME COLUMN "used_in_competitions" TO "usedInCompetitions";
ALTER TABLE "MlModel"
  ALTER COLUMN "name" SET DATA TYPE TEXT,
  ALTER COLUMN "description" SET DATA TYPE TEXT,
  ALTER COLUMN "predictionType" SET DATA TYPE TEXT,
  DROP CONSTRAINT "server_mlmodel_pkey",
  ADD CONSTRAINT "MlModel_pkey" PRIMARY KEY ("id");

-- AlterTable
ALTER TABLE "server_prediction"
  RENAME TO "Prediction";
ALTER TABLE "Prediction"
  RENAME COLUMN "predicted_margin" TO "predictedMargin";
ALTER TABLE "Prediction"
  RENAME COLUMN "match_id" TO "matchId";
ALTER TABLE "Prediction"
  RENAME COLUMN "ml_model_id" TO "mlModelId";
ALTER TABLE "Prediction"
  RENAME COLUMN "predicted_winner_id" TO "predictedWinnerId";
ALTER TABLE "Prediction"
  RENAME COLUMN "is_correct" TO "isCorrect";
ALTER TABLE "Prediction"
  RENAME COLUMN "predicted_win_probability" TO "predictedWinProbability";
ALTER TABLE "Prediction"
  RENAME COLUMN "created_at" TO "createdAt";
ALTER TABLE "Prediction"
  RENAME COLUMN "updated_at" TO "updatedAt";
ALTER TABLE "Prediction"
  ALTER COLUMN "createdAt" SET DEFAULT CURRENT_TIMESTAMP,
  ALTER COLUMN "updatedAt" SET DEFAULT CURRENT_TIMESTAMP,
  DROP CONSTRAINT "server_prediction_pkey",
  ADD CONSTRAINT "Prediction_pkey" PRIMARY KEY ("id");

-- AlterTable
ALTER TABLE "server_team"
  RENAME TO "Team";
ALTER TABLE "Team"
  ALTER COLUMN "name" SET DATA TYPE TEXT,
  DROP CONSTRAINT "server_team_pkey",
  ADD CONSTRAINT "Team_pkey" PRIMARY KEY ("id");

-- AlterTable
ALTER TABLE "server_teammatch"
  RENAME TO "TeamMatch";
ALTER TABLE "TeamMatch"
  RENAME COLUMN "at_home" TO "atHome";
ALTER TABLE "TeamMatch"
  RENAME COLUMN "match_id" TO "matchId";
ALTER TABLE "TeamMatch"
  RENAME COLUMN "team_id" TO "teamId";
ALTER TABLE "TeamMatch"
  ALTER COLUMN "score" SET DATA TYPE INTEGER,
  DROP CONSTRAINT "server_teammatch_pkey",
  ADD CONSTRAINT "TeamMatch_pkey" PRIMARY KEY ("id");

-- CreateIndex
DROP INDEX "server_match_winner_id_8e4d5c8a";
CREATE INDEX "Match_winnerId_idx" ON "Match"("winnerId");

-- CreateIndex
CREATE UNIQUE INDEX "Match_startDateTime_venue_key" ON "Match"("startDateTime", "venue");

-- CreateIndex
CREATE UNIQUE INDEX "MlModel_name_key" ON "MlModel"("name");

-- CreateIndex
DROP INDEX "server_mlmodel_name_b67f6f08_like";
CREATE INDEX "MlModel_name_idx" ON "MlModel"("name");

-- CreateIndex
DROP INDEX "server_prediction_match_id_00aaa745";
CREATE INDEX "Prediction_matchId_idx" ON "Prediction"("matchId");

-- CreateIndex
DROP INDEX "server_prediction_ml_model_id_3de99081";
CREATE INDEX "Prediction_mlModelId_idx" ON "Prediction"("mlModelId");

-- CreateIndex
DROP INDEX "server_prediction_predicted_winner_id_7487ef4f";
CREATE INDEX "Prediction_predictedWinnerId_idx" ON "Prediction"("predictedWinnerId");

-- CreateIndex
CREATE UNIQUE INDEX "Team_name_key" ON "Team"("name");

-- CreateIndex
DROP INDEX "server_team_name_1a256729_like";
CREATE INDEX "Team_name_idx" ON "Team"("name");

-- CreateIndex
DROP INDEX "server_teammatch_match_id_d0498fdb";
CREATE INDEX "TeamMatch_matchId_idx" ON "TeamMatch"("matchId");

-- CreateIndex
DROP INDEX "server_teammatch_team_id_9a0c00f1";
CREATE INDEX "TeamMatch_teamId_idx" ON "TeamMatch"("teamId");

-- AddForeignKey
ALTER TABLE "Match" ADD CONSTRAINT "Match_winnerId_fkey" FOREIGN KEY ("winnerId") REFERENCES "Team"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Prediction" ADD CONSTRAINT "Prediction_matchId_fkey" FOREIGN KEY ("matchId") REFERENCES "Match"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Prediction" ADD CONSTRAINT "Prediction_mlModelId_fkey" FOREIGN KEY ("mlModelId") REFERENCES "MlModel"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Prediction" ADD CONSTRAINT "Prediction_predictedWinnerId_fkey" FOREIGN KEY ("predictedWinnerId") REFERENCES "Team"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "TeamMatch" ADD CONSTRAINT "TeamMatch_matchId_fkey" FOREIGN KEY ("matchId") REFERENCES "Match"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "TeamMatch" ADD CONSTRAINT "TeamMatch_teamId_fkey" FOREIGN KEY ("teamId") REFERENCES "Team"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
