import "server-only";

import { Pool, type PoolClient, type QueryResultRow } from "pg";

import { requireServerEnv } from "@/lib/server-env";

let pool: Pool | null = null;

function getPool() {
  if (pool) {
    return pool;
  }

  const connectionString = requireServerEnv("DATABASE_URL");
  const isRemote =
    !connectionString.includes("127.0.0.1") &&
    !connectionString.includes("localhost");

  pool = new Pool({
    connectionString,
    ssl: isRemote ? { rejectUnauthorized: false } : undefined,
    max: 4,
  });

  return pool;
}

export async function query<T extends QueryResultRow>(
  sql: string,
  params: unknown[] = [],
) {
  return getPool().query<T>(sql, params);
}

export async function withClient<T>(
  callback: (client: PoolClient) => Promise<T>,
) {
  const client = await getPool().connect();

  try {
    return await callback(client);
  } finally {
    client.release();
  }
}
