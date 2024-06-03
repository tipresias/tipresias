-- AlterTable
ALTER TABLE "Match" ADD COLUMN     "seasonId" INTEGER;

-- CreateTable
CREATE TABLE "MlModelSeason" (
    "id" SERIAL NOT NULL,
    "isPrincipal" BOOLEAN NOT NULL DEFAULT false,
    "isUsedInCompetitions" BOOLEAN NOT NULL DEFAULT false,
    "seasonId" INTEGER NOT NULL,
    "mlModelId" INTEGER NOT NULL,

    CONSTRAINT "MlModelSeason_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Season" (
    "id" SERIAL NOT NULL,
    "year" INTEGER NOT NULL,

    CONSTRAINT "Season_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "MlModelSeason_seasonId_idx" ON "MlModelSeason"("seasonId");

-- CreateIndex
CREATE INDEX "MlModelSeason_mlModelId_idx" ON "MlModelSeason"("mlModelId");

-- CreateIndex
CREATE UNIQUE INDEX "MlModelSeason_seasonId_isPrincipal_key" ON "MlModelSeason"("seasonId", "isPrincipal");

-- CreateIndex
CREATE UNIQUE INDEX "Season_year_key" ON "Season"("year");

-- CreateIndex
CREATE INDEX "Season_year_idx" ON "Season"("year");

-- AddForeignKey
ALTER TABLE "Match" ADD CONSTRAINT "Match_seasonId_fkey" FOREIGN KEY ("seasonId") REFERENCES "Season"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "MlModelSeason" ADD CONSTRAINT "MlModelSeason_seasonId_fkey" FOREIGN KEY ("seasonId") REFERENCES "Season"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "MlModelSeason" ADD CONSTRAINT "MlModelSeason_mlModelId_fkey" FOREIGN KEY ("mlModelId") REFERENCES "MlModel"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
