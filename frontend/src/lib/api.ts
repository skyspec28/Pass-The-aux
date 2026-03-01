import type {
  SessionCreateResponse,
  SessionJoinResponse,
  SessionOut,
  SessionTrackOut,
  VoteOut,
  PlaybackOut,
  MemberOut,
  SessionSettings,
  PlaylistImportResult,
} from "@/types/api"

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080/v1"

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string
  ) {
    super(message)
    this.name = "ApiError"
  }
}

async function apiFetch<T>(
  path: string,
  opts: RequestInit & { token?: string } = {}
): Promise<T> {
  const { token, headers: extraHeaders, ...rest } = opts
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(extraHeaders as Record<string, string>),
  }
  if (token) headers["Authorization"] = `Bearer ${token}`

  const res = await fetch(`${BASE}${path}`, { ...rest, headers })

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }))
    throw new ApiError(res.status, body.detail ?? res.statusText)
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

// ─── Sessions ───────────────────────────────────────────────────────────────

export const createSession = (title: string) =>
  apiFetch<SessionCreateResponse>("/sessions", {
    method: "POST",
    body: JSON.stringify({ title }),
  })

export const joinSession = (code: string, display_name: string) =>
  apiFetch<SessionJoinResponse>(`/sessions/${code}/join`, {
    method: "POST",
    body: JSON.stringify({ display_name }),
  })

export const getSession = (code: string, token: string) =>
  apiFetch<SessionOut>(`/sessions/${code}`, { token })

export const updateSettings = (
  code: string,
  settings: Partial<SessionSettings>,
  token: string
) =>
  apiFetch<SessionOut>(`/sessions/${code}/settings`, {
    method: "PATCH",
    body: JSON.stringify({ settings }),
    token,
  })

// ─── Tracks ─────────────────────────────────────────────────────────────────

export const getTracks = (code: string, token: string, status?: string) =>
  apiFetch<SessionTrackOut[]>(
    `/sessions/${code}/tracks${status ? `?track_status=${status}` : ""}`,
    { token }
  )

export const getSessionTrack = (code: string, sessionTrackId: string, token: string) =>
  apiFetch<SessionTrackOut>(`/sessions/${code}/tracks/${sessionTrackId}`, { token })

export const addTrack = (code: string, url: string, token: string) =>
  apiFetch<SessionTrackOut>(`/sessions/${code}/tracks`, {
    method: "POST",
    body: JSON.stringify({ url }),
    token,
  })

export const removeTrack = (code: string, trackId: string, token: string) =>
  apiFetch<void>(`/sessions/${code}/tracks/${trackId}`, {
    method: "DELETE",
    token,
  })

// ─── Votes ───────────────────────────────────────────────────────────────────

export const castVote = (
  code: string,
  sessionTrackId: string,
  value: 1 | -1,
  token: string
) =>
  apiFetch<VoteOut>(`/sessions/${code}/tracks/${sessionTrackId}/vote`, {
    method: "POST",
    body: JSON.stringify({ value }),
    token,
  })

export const removeVote = (code: string, sessionTrackId: string, token: string) =>
  apiFetch<void>(`/sessions/${code}/tracks/${sessionTrackId}/vote`, {
    method: "DELETE",
    token,
  })

// ─── Playback ────────────────────────────────────────────────────────────────

export const getPlayback = (code: string, token: string) =>
  apiFetch<PlaybackOut>(`/sessions/${code}/playback`, { token })

export const startPlayback = (code: string, token: string) =>
  apiFetch<PlaybackOut>(`/sessions/${code}/playback/start`, {
    method: "POST",
    token,
  })

export const pausePlayback = (code: string, token: string) =>
  apiFetch<PlaybackOut>(`/sessions/${code}/playback/pause`, {
    method: "POST",
    token,
  })

export const nextTrack = (code: string, token: string) =>
  apiFetch<PlaybackOut>(`/sessions/${code}/playback/next`, {
    method: "POST",
    token,
  })

// ─── Members ─────────────────────────────────────────────────────────────────

export const banMember = (code: string, memberId: string, token: string) =>
  apiFetch<MemberOut>(`/sessions/${code}/members/${memberId}/ban`, {
    method: "POST",
    token,
  })

export const muteMember = (
  code: string,
  memberId: string,
  seconds: number,
  token: string
) =>
  apiFetch<MemberOut>(`/sessions/${code}/members/${memberId}/mute`, {
    method: "POST",
    body: JSON.stringify({ seconds }),
    token,
  })

// ─── Playlist Import ──────────────────────────────────────────────────────────

export const importPlaylist = (code: string, url: string, token: string) =>
  apiFetch<PlaylistImportResult>(`/sessions/${code}/import`, {
    method: "POST",
    body: JSON.stringify({ url }),
    token,
  })
