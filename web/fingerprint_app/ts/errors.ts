/** Canonical error codes the backend emits in error envelopes. */
const ERROR_CODES = {
  trackNotFound: "TrackNotFoundError",
  networkDisconnected: "NetworkDisconnectedError",
  audioProcessing: "AudioProcessingError",
} as const;

/** Does the body carry the given error `code`? */
function hasErrorCode(body: Record<string, unknown> | undefined, code: string): boolean {
  return body?.error === code;
}

/** Does `status` match OR does the body carry `code`? */
function matchesStatusOrCode(
  response: Response,
  body: Record<string, unknown> | undefined,
  status: number,
  code: string,
): boolean {
  return response.status === status || hasErrorCode(body, code);
}

/** Classified outcome of a failed response. `"unknown"` is the fallback for anything else. */
export type Outcome = "notFound" | "unprocessable" | "networkDown" | "unknown";

/**
 * Map a failed response to a UI outcome. The two endpoints share the same
 * classification vocabulary: confirm's unprocessable body (400) and the
 * search's not-found body (404) both classify by status or canonical code;
 * 503/`NetworkDisconnectedError` is reachability across both.
 */
export function outcomeFor(response: Response, body: Record<string, unknown> | undefined): Outcome {
  if (matchesStatusOrCode(response, body, 400, ERROR_CODES.audioProcessing)) {
    return "unprocessable";
  }
  if (matchesStatusOrCode(response, body, 404, ERROR_CODES.trackNotFound)) {
    return "notFound";
  }
  if (matchesStatusOrCode(response, body, 503, ERROR_CODES.networkDisconnected)) {
    return "networkDown";
  }
  return "unknown";
}
