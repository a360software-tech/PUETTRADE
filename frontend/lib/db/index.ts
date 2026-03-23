import { drizzle } from "drizzle-orm/postgres-js";
import postgres from "postgres";

const connectionString = process.env.DATABASE_URL;

if (!connectionString) {
  throw new Error("DATABASE_URL is not set");
}

const globalForDb = globalThis as typeof globalThis & {
  postgresSql?: ReturnType<typeof postgres>;
};

const sql =
  globalForDb.postgresSql ??
  postgres(connectionString, {
    ssl: process.env.NODE_ENV === "production" ? "require" : undefined,
    max: process.env.NODE_ENV === "production" ? 10 : 1,
  });

if (process.env.NODE_ENV !== "production") {
  globalForDb.postgresSql = sql;
}

export const db = drizzle(sql);
export { sql };
