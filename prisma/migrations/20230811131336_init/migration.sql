-- CreateTable
CREATE TABLE "Team" (
    "id" INT8 NOT NULL DEFAULT unique_rowid(),
    "updatedAt" TIMESTAMP(3) NOT NULL,
    "name" STRING NOT NULL,

    CONSTRAINT "Team_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Match" (
    "id" INT8 NOT NULL DEFAULT unique_rowid(),
    "updatedAt" TIMESTAMP(3) NOT NULL,
    "startDateTime" TIMESTAMP(3) NOT NULL,
    "roundNumber" INT4 NOT NULL,
    "venue" STRING NOT NULL,

    CONSTRAINT "Match_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "TeamMatch" (
    "id" INT8 NOT NULL DEFAULT unique_rowid(),
    "updatedAt" TIMESTAMP(3) NOT NULL,
    "atHome" BOOL NOT NULL,
    "score" INT4,
    "teamId" INT8 NOT NULL,
    "matchId" INT8 NOT NULL,

    CONSTRAINT "TeamMatch_pkey" PRIMARY KEY ("id")
);

-- AddForeignKey
ALTER TABLE "TeamMatch" ADD CONSTRAINT "TeamMatch_teamId_fkey" FOREIGN KEY ("teamId") REFERENCES "Team"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "TeamMatch" ADD CONSTRAINT "TeamMatch_matchId_fkey" FOREIGN KEY ("matchId") REFERENCES "Match"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
