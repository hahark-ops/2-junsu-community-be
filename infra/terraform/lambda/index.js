const { S3Client, PutObjectCommand } = require("@aws-sdk/client-s3");
const { getSignedUrl } = require("@aws-sdk/s3-request-presigner");
const crypto = require("crypto");

const ALLOWED_TYPES = new Set(["profile", "post"]);
const ALLOWED_CONTENT_TYPES = new Set([
  "image/jpeg",
  "image/png",
  "image/gif",
  "image/webp",
]);
const MAX_UPLOAD_SIZE = Number(process.env.MAX_UPLOAD_SIZE_BYTES || 30 * 1024 * 1024);
const MAX_PROFILE_UPLOAD_SIZE = Number(
  process.env.MAX_PROFILE_UPLOAD_SIZE_BYTES || MAX_UPLOAD_SIZE
);
const MAX_POST_UPLOAD_SIZE = Number(
  process.env.MAX_POST_UPLOAD_SIZE_BYTES || 30 * 1024 * 1024
);

const UPLOAD_BUCKET = process.env.UPLOAD_BUCKET;
const AWS_REGION =
  process.env.AWS_REGION || process.env.AWS_DEFAULT_REGION || "ap-northeast-2";
const UPLOAD_INTERNAL_TOKEN = (process.env.UPLOAD_INTERNAL_TOKEN || "").trim();
const ALLOWED_ORIGIN = (process.env.ALLOWED_ORIGIN || "http://localhost:3000").trim();

const s3 = new S3Client({ region: AWS_REGION });

function response(statusCode, payload) {
  return {
    statusCode,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
      "Access-Control-Allow-Headers": "Content-Type,X-Upload-Internal-Token",
      "Access-Control-Allow-Methods": "OPTIONS,POST",
    },
    body: JSON.stringify(payload),
  };
}

function parseHeaders(rawHeaderText) {
  const headers = {};
  for (const line of rawHeaderText.split("\r\n")) {
    const idx = line.indexOf(":");
    if (idx === -1) continue;
    const key = line.slice(0, idx).trim().toLowerCase();
    const value = line.slice(idx + 1).trim();
    headers[key] = value;
  }
  return headers;
}

function parseContentDisposition(value) {
  const out = { name: "", filename: "" };
  const nameMatch = /name="([^"]+)"/i.exec(value || "");
  const filenameMatch = /filename="([^"]*)"/i.exec(value || "");
  if (nameMatch) out.name = nameMatch[1];
  if (filenameMatch) out.filename = filenameMatch[1];
  return out;
}

function extractBoundary(contentType) {
  const match = /boundary="?([^";]+)"?/i.exec(contentType || "");
  if (!match) {
    throw new Error("multipart boundary를 찾을 수 없습니다.");
  }
  return match[1];
}

function parseMultipart(bodyBuffer, contentType) {
  const boundary = extractBoundary(contentType);
  const marker = `--${boundary}`;
  const raw = bodyBuffer.toString("latin1");
  const chunks = raw.split(marker).slice(1, -1);
  const parts = [];

  for (let chunk of chunks) {
    if (chunk.startsWith("\r\n")) chunk = chunk.slice(2);
    if (chunk.endsWith("\r\n")) chunk = chunk.slice(0, -2);

    const headerEnd = chunk.indexOf("\r\n\r\n");
    if (headerEnd === -1) continue;

    const rawHeaders = chunk.slice(0, headerEnd);
    const rawData = chunk.slice(headerEnd + 4);
    const headers = parseHeaders(rawHeaders);
    const disposition = parseContentDisposition(headers["content-disposition"] || "");

    parts.push({
      name: disposition.name,
      filename: disposition.filename,
      contentType: (headers["content-type"] || "application/octet-stream").toLowerCase(),
      data: Buffer.from(rawData, "latin1"),
    });
  }

  return parts;
}

function normalizeUploadType(value) {
  const v = String(value || "post").trim().toLowerCase();
  return ALLOWED_TYPES.has(v) ? v : "post";
}

function getUploadLimit(uploadType) {
  if (uploadType === "profile") return MAX_PROFILE_UPLOAD_SIZE;
  if (uploadType === "post") return MAX_POST_UPLOAD_SIZE;
  return MAX_UPLOAD_SIZE;
}

function formatLimitMb(bytes) {
  return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
}

function getExtension(filename) {
  const lower = String(filename || "").toLowerCase();
  if (lower.endsWith(".jpg")) return ".jpg";
  if (lower.endsWith(".jpeg")) return ".jpeg";
  if (lower.endsWith(".png")) return ".png";
  if (lower.endsWith(".gif")) return ".gif";
  if (lower.endsWith(".webp")) return ".webp";
  return ".png";
}

function parseJsonBody(event) {
  if (!event.body) return {};
  if (event.isBase64Encoded) {
    return JSON.parse(Buffer.from(event.body, "base64").toString("utf8"));
  }
  return JSON.parse(event.body);
}

function getHeader(headers, key) {
  const target = String(key || "").toLowerCase();
  for (const [headerKey, value] of Object.entries(headers || {})) {
    if (String(headerKey).toLowerCase() === target) {
      return value;
    }
  }
  return "";
}

function buildObjectKey(uploadType, filename) {
  const extension = getExtension(filename);
  const savedFilename = `${crypto.randomUUID()}${extension}`;
  return {
    savedFilename,
    objectKey: `uploads/${uploadType}/${savedFilename}`,
  };
}

function buildFileUrl(objectKey) {
  return `https://${UPLOAD_BUCKET}.s3.${AWS_REGION}.amazonaws.com/${objectKey}`;
}

async function generatePresignedPutUrl(objectKey, contentType, contentLength) {
  return getSignedUrl(
    s3,
    new PutObjectCommand({
      Bucket: UPLOAD_BUCKET,
      Key: objectKey,
      ContentType: contentType,
      ContentLength: contentLength,
    }),
    { expiresIn: 300 }
  );
}

exports.handler = async (event) => {
  try {
    if (!UPLOAD_BUCKET) {
      return response(500, {
        code: "CONFIG_ERROR",
        message: "UPLOAD_BUCKET 환경변수가 설정되지 않았습니다.",
        data: null,
      });
    }

    const method = event?.requestContext?.http?.method || event?.httpMethod || "POST";
    if (method === "OPTIONS") {
      return response(200, { ok: true });
    }

    if (!UPLOAD_INTERNAL_TOKEN) {
      return response(500, {
        code: "CONFIG_ERROR",
        message: "UPLOAD_INTERNAL_TOKEN 환경변수가 설정되지 않았습니다.",
        data: null,
      });
    }

    const headers = event.headers || {};
    const requestToken = getHeader(headers, "x-upload-internal-token");
    if (requestToken !== UPLOAD_INTERNAL_TOKEN) {
      return response(401, {
        code: "UNAUTHORIZED",
        message: "업로드 URL 발급 권한이 없습니다.",
        data: null,
      });
    }

    const contentType = headers["content-type"] || headers["Content-Type"] || "";

    if (contentType.toLowerCase().startsWith("application/json")) {
      const body = parseJsonBody(event);
      const uploadType = normalizeUploadType(body.type || "post");
      const requestFilename = body.filename || "upload.png";
      const requestContentType = String(body.contentType || "image/png").toLowerCase();
      const requestSize = Number(body.sizeBytes || 0);

      if (!ALLOWED_CONTENT_TYPES.has(requestContentType)) {
        return response(400, {
          code: "INVALID_FILE_TYPE",
          message: "지원하지 않는 파일 형식입니다.",
          data: null,
        });
      }

      if (!Number.isFinite(requestSize) || requestSize <= 0) {
        return response(400, {
          code: "INVALID_FILE_SIZE",
          message: "파일 크기 정보가 필요합니다.",
          data: null,
        });
      }

      const uploadLimit = getUploadLimit(uploadType);
      if (requestSize > uploadLimit) {
        return response(413, {
          code: "FILE_TOO_LARGE",
          message: `파일 크기가 제한을 초과했습니다. (최대 ${formatLimitMb(uploadLimit)})`,
          data: null,
        });
      }

      const { savedFilename, objectKey } = buildObjectKey(uploadType, requestFilename);
      const fileUrl = buildFileUrl(objectKey);
      const uploadUrl = await generatePresignedPutUrl(
        objectKey,
        requestContentType,
        requestSize
      );

      return response(200, {
        code: "PRESIGNED_URL_CREATED",
        message: "Presigned URL 생성 성공",
        data: {
          uploadUrl,
          fileUrl,
          objectKey,
          filename: savedFilename,
          contentLength: requestSize,
          provider: "lambda-presigned",
        },
      });
    }

    if (!contentType.toLowerCase().startsWith("multipart/form-data")) {
      return response(400, {
        code: "INVALID_CONTENT_TYPE",
        message: "multipart/form-data 또는 application/json 요청만 지원합니다.",
        data: null,
      });
    }

    if (!event.body) {
      return response(400, {
        code: "EMPTY_BODY",
        message: "요청 본문이 비어 있습니다.",
        data: null,
      });
    }

    const bodyBuffer = event.isBase64Encoded
      ? Buffer.from(event.body, "base64")
      : Buffer.from(event.body);

    const parts = parseMultipart(bodyBuffer, contentType);
    const filePart =
      parts.find((p) => p.name === "file" && p.filename) ||
      parts.find((p) => p.filename);
    const typePart = parts.find((p) => p.name === "type");

    if (!filePart || !filePart.data || filePart.data.length === 0) {
      return response(400, {
        code: "FILE_NOT_FOUND",
        message: "업로드 파일을 찾을 수 없습니다.",
        data: null,
      });
    }

    if (!ALLOWED_CONTENT_TYPES.has(filePart.contentType)) {
      return response(400, {
        code: "INVALID_FILE_TYPE",
        message: "지원하지 않는 파일 형식입니다.",
        data: null,
      });
    }

    const uploadType = normalizeUploadType(
      typePart ? typePart.data.toString("utf8").trim() : "post"
    );
    const uploadLimit = getUploadLimit(uploadType);

    if (filePart.data.length > uploadLimit) {
      return response(413, {
        code: "FILE_TOO_LARGE",
        message: `파일 크기가 제한을 초과했습니다. (최대 ${formatLimitMb(uploadLimit)})`,
        data: null,
      });
    }

    const { savedFilename, objectKey } = buildObjectKey(uploadType, filePart.filename);

    await s3.send(
      new PutObjectCommand({
        Bucket: UPLOAD_BUCKET,
        Key: objectKey,
        Body: filePart.data,
        ContentType: filePart.contentType,
      })
    );

    const fileUrl = buildFileUrl(objectKey);

    return response(201, {
      status: 201,
      code: "UPLOAD_SUCCESS",
      message: "File upload success",
      data: {
        filePath: fileUrl,
        fileUrl,
        filename: savedFilename,
        objectKey,
        provider: "lambda",
      },
    });
  } catch (error) {
    return response(500, {
      status: 500,
      code: "UPLOAD_FAILED",
      message: "File upload failed",
      error: error.message,
    });
  }
};
