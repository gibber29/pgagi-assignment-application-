import { NextRequest, NextResponse } from "next/server";
import { spawn, type ChildProcessWithoutNullStreams } from "node:child_process";
import path from "node:path";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";
const BACKEND_HEALTH_URL = new URL("/", BACKEND_URL).toString();

export const runtime = "nodejs";

declare global {
  // eslint-disable-next-line no-var
  var pgagiBackendProcess: ChildProcessWithoutNullStreams | undefined;
  // eslint-disable-next-line no-var
  var pgagiBackendStarting: Promise<boolean> | undefined;
}

type RouteContext = {
  params: Promise<{
    path: string[];
  }>;
};

const HOP_BY_HOP_HEADERS = new Set([
  "connection",
  "content-length",
  "host",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailer",
  "transfer-encoding",
  "upgrade",
]);

async function isBackendReachable() {
  try {
    const response = await fetch(BACKEND_HEALTH_URL, {
      cache: "no-store",
      signal: AbortSignal.timeout(1000),
    });
    return response.ok;
  } catch {
    return false;
  }
}

async function waitForBackend(timeoutMs = 25000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    if (await isBackendReachable()) {
      return true;
    }
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }
  return false;
}

async function ensureBackendRunning() {
  if (await isBackendReachable()) {
    return true;
  }

  if (process.env.NODE_ENV === "production") {
    return false;
  }

  if (globalThis.pgagiBackendStarting) {
    return globalThis.pgagiBackendStarting;
  }

  globalThis.pgagiBackendStarting = (async () => {
    const projectRoot = path.resolve(process.cwd(), "..");
    const backendDir = path.join(projectRoot, "backend");
    const pythonPath = path.join(backendDir, "venv", "Scripts", "python.exe");

    if (!globalThis.pgagiBackendProcess || globalThis.pgagiBackendProcess.killed) {
      globalThis.pgagiBackendProcess = spawn(
        pythonPath,
        ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
        {
          cwd: backendDir,
          windowsHide: true,
          stdio: "pipe",
        }
      );

      globalThis.pgagiBackendProcess.on("exit", () => {
        globalThis.pgagiBackendProcess = undefined;
      });
    }

    const ready = await waitForBackend();
    globalThis.pgagiBackendStarting = undefined;
    return ready;
  })();

  return globalThis.pgagiBackendStarting;
}

async function proxy(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  const targetUrl = new URL(`/api/${path.join("/")}`, BACKEND_URL);
  targetUrl.search = request.nextUrl.search;

  const headers = new Headers(request.headers);
  for (const header of HOP_BY_HOP_HEADERS) {
    headers.delete(header);
  }

  try {
    const backendReady = await ensureBackendRunning();
    if (!backendReady) {
      return NextResponse.json(
        {
          detail:
            "Backend API is not reachable. Run .\\dev.ps1 from the project root, or start FastAPI on http://127.0.0.1:8000.",
        },
        { status: 503 }
      );
    }

    const body =
      request.method === "GET" || request.method === "HEAD"
        ? undefined
        : await request.arrayBuffer();

    const response = await fetch(targetUrl, {
      method: request.method,
      headers,
      body,
      cache: "no-store",
    });

    const responseHeaders = new Headers(response.headers);
    for (const header of HOP_BY_HOP_HEADERS) {
      responseHeaders.delete(header);
    }

    return new NextResponse(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: responseHeaders,
    });
  } catch {
    return NextResponse.json(
      {
        detail:
          "Backend API is not reachable. Run .\\dev.ps1 from the project root, or start FastAPI on http://127.0.0.1:8000.",
      },
      { status: 503 }
    );
  }
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
