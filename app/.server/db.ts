import { Prisma, PrismaClient } from "@prisma/client";

export const db = new PrismaClient();

export const buildSql = Prisma.sql;
export const sqlQuery = <T>(sql: Prisma.Sql) => db.$queryRaw<T>(sql);
