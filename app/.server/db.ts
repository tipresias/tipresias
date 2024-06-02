import { Prisma, PrismaClient } from "@prisma/client";

const db = new PrismaClient();

export const sqlQuery = <T>(sql: string) => db.$queryRaw<T>(Prisma.sql([sql]));
