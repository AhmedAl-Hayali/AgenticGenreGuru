/** Canonical error codes the backend emits in error envelopes. */
export const ERROR_CODES = {
  trackNotFound: "TrackNotFoundError",
  networkDisconnected: "NetworkDisconnectedError",
  audioProcessing: "AudioProcessingError",
} as const;

/** Does the body carry the given error `code`? */
export function hasErrorCode(body: Record<string, unknown> | undefined, code: string): boolean {
  return body?.error === code;
}

/** Does `status` match OR does the body carry `code`? */
export function matchesStatusOrCode(
  response: Response,
  body: Record<string, unknown> | undefined,
  status: number,
  code: string,
): boolean {
  return response.status === status || hasErrorCode(body, code);
}

/** Reachability failure: HTTP 503 or the network-disconnected error code. */
export function isNetworkDown(
  response: Response,
  body: Record<string, unknown> | undefined,
): boolean {
  return matchesStatusOrCode(response, body, 503, ERROR_CODES.networkDisconnected);
}
