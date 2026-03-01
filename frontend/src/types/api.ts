export interface AuthClaims {
  sub: string
  session_id: string
  role: "HOST" | "GUEST" | "MOD"
  exp: number
  iat: number
}

export interface StoredAuth {
  token: string
  claims: AuthClaims
  code: string
}

export interface SessionSettings {
  allow_guest_add: boolean
  allow_downvotes: boolean
  max_adds_per_guest_per_10min: number
  max_votes_per_guest_per_min: number
  dedupe_tracks: boolean
  fairness_enabled: boolean
  cooldown_songs: number
  explicit_filter?: string
}

export interface SessionOut {
  id: string
  code: string
  title: string
  status: string
  settings: SessionSettings
  created_at: string
  ended_at: string | null
}

export interface SessionCreateResponse {
  session_id: string
  code: string
  host_token: string
}

export interface SessionJoinResponse {
  member_id: string
  member_token: string
  role: string
}

export interface TrackOut {
  id: string
  provider: string
  provider_track_id: string
  title: string | null
  artist: string | null
  duration_ms: number | null
  artwork_url: string | null
  explicit: boolean | null
  source_url: string | null
  metadata_status: "PENDING" | "RESOLVED" | "FAILED"
}

export interface SessionTrackOut {
  id: string
  session_id: string
  track_id: string
  added_by_member_id: string
  added_at: string
  status: "QUEUED" | "PLAYING" | "PLAYED" | "REMOVED"
  score_cached: number
  track: TrackOut
}

export interface VoteOut {
  id: string
  session_track_id: string
  member_id: string
  value: 1 | -1
  created_at: string
}

export interface PlaybackOut {
  session_id: string
  current_session_track_id: string | null
  state: "PLAYING" | "PAUSED" | "STOPPED"
  started_at: string | null
  position_ms: number
  updated_at: string
}

export interface MemberOut {
  id: string
  session_id: string
  display_name: string
  role: "HOST" | "GUEST" | "MOD"
  is_banned: boolean
  muted_until: string | null
  joined_at: string
}

export interface QueueItem {
  session_track_id: string
  score: number
  status: string
}

export type WsEvent =
  | { type: "queue.updated"; data: { queue: QueueItem[] } }
  | { type: "vote.updated"; data: { session_track_id: string; score: number; upvotes: number; downvotes: number } }
  | { type: "playback.updated"; data: PlaybackOut }
  | { type: "track.added"; data: { session_track_id: string; track_id: string } }
  | { type: "track.updated"; data: { session_track_id: string } }
  | { type: "track.removed"; data: { session_track_id: string } }
  | { type: "member.joined"; data: { member_id: string; display_name: string } }
  | { type: "member.banned"; data: { member_id: string } }
  | { type: "session.updated"; data: { settings: SessionSettings } }
