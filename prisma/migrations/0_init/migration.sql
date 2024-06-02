-- CreateTable
CREATE TABLE "server_match" (
    "id" SERIAL NOT NULL,
    "start_date_time" TIMESTAMPTZ(6) NOT NULL,
    "round_number" SMALLINT NOT NULL,
    "venue" VARCHAR(100),
    "margin" INTEGER,
    "winner_id" INTEGER,

    CONSTRAINT "server_match_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "server_mlmodel" (
    "id" SERIAL NOT NULL,
    "name" VARCHAR(100) NOT NULL,
    "description" TEXT,
    "is_principal" BOOLEAN NOT NULL,
    "prediction_type" VARCHAR(100) NOT NULL,
    "used_in_competitions" BOOLEAN NOT NULL,

    CONSTRAINT "server_mlmodel_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "server_prediction" (
    "id" SERIAL NOT NULL,
    "predicted_margin" DOUBLE PRECISION,
    "match_id" INTEGER NOT NULL,
    "ml_model_id" INTEGER NOT NULL,
    "predicted_winner_id" INTEGER NOT NULL,
    "is_correct" BOOLEAN,
    "predicted_win_probability" DOUBLE PRECISION,
    "created_at" TIMESTAMPTZ(6) NOT NULL,
    "updated_at" TIMESTAMPTZ(6) NOT NULL,

    CONSTRAINT "server_prediction_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "server_team" (
    "id" SERIAL NOT NULL,
    "name" VARCHAR(100) NOT NULL,

    CONSTRAINT "server_team_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "server_teammatch" (
    "id" SERIAL NOT NULL,
    "at_home" BOOLEAN NOT NULL,
    "score" SMALLINT NOT NULL,
    "match_id" INTEGER NOT NULL,
    "team_id" INTEGER NOT NULL,

    CONSTRAINT "server_teammatch_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "server_match_winner_id_8e4d5c8a" ON "server_match"("winner_id");

-- CreateIndex
CREATE UNIQUE INDEX "unique_start_date_time_and_venue" ON "server_match"("start_date_time", "venue");

-- CreateIndex
CREATE UNIQUE INDEX "server_mlmodel_name_b67f6f08_uniq" ON "server_mlmodel"("name");

-- CreateIndex
CREATE INDEX "server_mlmodel_name_b67f6f08_like" ON "server_mlmodel"("name");

-- CreateIndex
CREATE INDEX "server_prediction_match_id_00aaa745" ON "server_prediction"("match_id");

-- CreateIndex
CREATE INDEX "server_prediction_ml_model_id_3de99081" ON "server_prediction"("ml_model_id");

-- CreateIndex
CREATE INDEX "server_prediction_predicted_winner_id_7487ef4f" ON "server_prediction"("predicted_winner_id");

-- CreateIndex
CREATE UNIQUE INDEX "server_team_name_1a256729_uniq" ON "server_team"("name");

-- CreateIndex
CREATE INDEX "server_team_name_1a256729_like" ON "server_team"("name");

-- CreateIndex
CREATE INDEX "server_teammatch_match_id_d0498fdb" ON "server_teammatch"("match_id");

-- CreateIndex
CREATE INDEX "server_teammatch_team_id_9a0c00f1" ON "server_teammatch"("team_id");

-- AddForeignKey
ALTER TABLE "server_match" ADD CONSTRAINT "server_match_winner_id_8e4d5c8a_fk_server_team_id" FOREIGN KEY ("winner_id") REFERENCES "server_team"("id") ON DELETE NO ACTION ON UPDATE NO ACTION;

-- AddForeignKey
ALTER TABLE "server_prediction" ADD CONSTRAINT "server_prediction_match_id_00aaa745_fk_server_match_id" FOREIGN KEY ("match_id") REFERENCES "server_match"("id") ON DELETE NO ACTION ON UPDATE NO ACTION;

-- AddForeignKey
ALTER TABLE "server_prediction" ADD CONSTRAINT "server_prediction_ml_model_id_3de99081_fk_server_mlmodel_id" FOREIGN KEY ("ml_model_id") REFERENCES "server_mlmodel"("id") ON DELETE NO ACTION ON UPDATE NO ACTION;

-- AddForeignKey
ALTER TABLE "server_prediction" ADD CONSTRAINT "server_prediction_predicted_winner_id_7487ef4f_fk_server_te" FOREIGN KEY ("predicted_winner_id") REFERENCES "server_team"("id") ON DELETE NO ACTION ON UPDATE NO ACTION;

-- AddForeignKey
ALTER TABLE "server_teammatch" ADD CONSTRAINT "server_teammatch_match_id_d0498fdb_fk_server_match_id" FOREIGN KEY ("match_id") REFERENCES "server_match"("id") ON DELETE NO ACTION ON UPDATE NO ACTION;

-- AddForeignKey
ALTER TABLE "server_teammatch" ADD CONSTRAINT "server_teammatch_team_id_9a0c00f1_fk_server_team_id" FOREIGN KEY ("team_id") REFERENCES "server_team"("id") ON DELETE NO ACTION ON UPDATE NO ACTION;

