/*
  Warnings:

  - A unique constraint covering the columns `[seasonId,mlModelId]` on the table `MlModelSeason` will be added. If there are existing duplicate values, this will fail.

*/
-- DropIndex
DROP INDEX "MlModelSeason_seasonId_isPrincipal_key";

-- CreateIndex
CREATE UNIQUE INDEX "MlModelSeason_seasonId_mlModelId_key" ON "MlModelSeason"("seasonId", "mlModelId");
