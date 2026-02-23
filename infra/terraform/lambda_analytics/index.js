const {
  AthenaClient,
  StartQueryExecutionCommand,
  GetQueryExecutionCommand,
  GetQueryResultsCommand,
} = require("@aws-sdk/client-athena");

const AWS_REGION =
  process.env.AWS_REGION || process.env.AWS_DEFAULT_REGION || "ap-northeast-2";
const ATHENA_WORKGROUP = process.env.ATHENA_WORKGROUP || "";
const ATHENA_DATABASE = process.env.ATHENA_DATABASE || "";
const ATHENA_OUTPUT_S3 = process.env.ATHENA_OUTPUT_S3 || "";
const ALLOWED_ORIGIN = process.env.ALLOWED_ORIGIN || "*";

const athena = new AthenaClient({ region: AWS_REGION });

function response(statusCode, payload) {
  return {
    statusCode,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
      "Access-Control-Allow-Headers": "*",
      "Access-Control-Allow-Methods": "GET,OPTIONS",
    },
    body: JSON.stringify(payload),
  };
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function waitForQuery(queryExecutionId, timeoutMs = 12000) {
  const startedAt = Date.now();
  while (true) {
    const execution = await athena.send(
      new GetQueryExecutionCommand({ QueryExecutionId: queryExecutionId })
    );
    const state = execution?.QueryExecution?.Status?.State;
    const reason = execution?.QueryExecution?.Status?.StateChangeReason || "";

    if (state === "SUCCEEDED") {
      return { ok: true, state };
    }
    if (state === "FAILED" || state === "CANCELLED") {
      return { ok: false, state, reason };
    }
    if (Date.now() - startedAt > timeoutMs) {
      return { ok: false, state: "TIMEOUT", reason: "Athena query timeout" };
    }
    await sleep(400);
  }
}

function rowsToObjects(resultRows) {
  if (!Array.isArray(resultRows) || resultRows.length < 2) {
    return [];
  }

  const headers =
    resultRows[0]?.Data?.map((x) => x.VarCharValue || "").filter(Boolean) || [];
  return resultRows.slice(1).map((row) => {
    const out = {};
    const cols = row?.Data || [];
    headers.forEach((key, idx) => {
      out[key] = cols[idx]?.VarCharValue ?? null;
    });
    return out;
  });
}

exports.handler = async (event) => {
  try {
    const method = event?.requestContext?.http?.method || event?.httpMethod || "GET";
    if (method === "OPTIONS") {
      return response(200, { ok: true });
    }

    const queryString = `
      SELECT
        CAST(current_timestamp AS varchar) AS queriedAt,
        'athena-ok' AS status
    `;

    const startParams = {
      QueryString: queryString,
    };

    if (ATHENA_WORKGROUP) {
      startParams.WorkGroup = ATHENA_WORKGROUP;
    }
    if (ATHENA_DATABASE) {
      startParams.QueryExecutionContext = { Database: ATHENA_DATABASE };
    }
    if (ATHENA_OUTPUT_S3) {
      startParams.ResultConfiguration = { OutputLocation: ATHENA_OUTPUT_S3 };
    }

    const started = await athena.send(new StartQueryExecutionCommand(startParams));
    const queryExecutionId = started.QueryExecutionId;

    if (!queryExecutionId) {
      return response(500, {
        code: "ATHENA_START_FAILED",
        message: "Athena 쿼리 시작에 실패했습니다.",
        data: null,
      });
    }

    const waitResult = await waitForQuery(queryExecutionId);
    if (!waitResult.ok) {
      return response(500, {
        code: "ATHENA_QUERY_FAILED",
        message: "Athena 쿼리 실행에 실패했습니다.",
        data: {
          queryExecutionId,
          state: waitResult.state,
          reason: waitResult.reason || null,
        },
      });
    }

    const result = await athena.send(
      new GetQueryResultsCommand({ QueryExecutionId: queryExecutionId })
    );
    const rows = rowsToObjects(result?.ResultSet?.Rows);

    return response(200, {
      code: "ATHENA_QUERY_SUCCESS",
      message: "Athena 질의가 성공했습니다.",
      data: {
        source: "athena",
        queryExecutionId,
        rowCount: rows.length,
        rows,
      },
    });
  } catch (error) {
    return response(500, {
      code: "ATHENA_INTERNAL_ERROR",
      message: "Athena 처리 중 오류가 발생했습니다.",
      data: {
        error: error.message,
      },
    });
  }
};
