import { create } from "zustand"
import type {
  StoredAuth,
  SessionTrackOut,
  PlaybackOut,
  SessionSettings,
  MemberOut,
} from "@/types/api"

interface SessionStore {
  // Auth
  auth: StoredAuth | null
  setAuth: (auth: StoredAuth) => void
  clearAuth: () => void

  // Live queue (full SessionTrackOut[], in server-determined order)
  queue: SessionTrackOut[]
  setQueue: (items: SessionTrackOut[]) => void
  upsertTrack: (track: SessionTrackOut) => void
  removeTrack: (session_track_id: string) => void
  reorderQueue: (orderedIds: string[]) => void

  // Playback
  playback: PlaybackOut | null
  setPlayback: (p: PlaybackOut) => void

  // Session settings
  settings: SessionSettings | null
  setSettings: (s: SessionSettings) => void

  // Members (accumulated from WS events)
  members: MemberOut[]
  addMember: (m: MemberOut) => void
  removeMember: (member_id: string) => void
}

export const useSessionStore = create<SessionStore>((set) => ({
  auth: null,
  setAuth: (auth) => set({ auth }),
  clearAuth: () => set({ auth: null }),

  queue: [],
  setQueue: (items) => set({ queue: items }),
  upsertTrack: (track) =>
    set((state) => {
      const idx = state.queue.findIndex((t) => t.id === track.id)
      if (idx >= 0) {
        const next = [...state.queue]
        next[idx] = track
        return { queue: next }
      }
      return { queue: [...state.queue, track] }
    }),
  removeTrack: (session_track_id) =>
    set((state) => ({
      queue: state.queue.filter((t) => t.id !== session_track_id),
    })),
  reorderQueue: (orderedIds) =>
    set((state) => {
      const map = new Map(state.queue.map((t) => [t.id, t]))
      const reordered = orderedIds
        .map((id) => map.get(id))
        .filter((t): t is SessionTrackOut => t !== undefined)
      const rest = state.queue.filter((t) => !orderedIds.includes(t.id))
      return { queue: [...reordered, ...rest] }
    }),

  playback: null,
  setPlayback: (playback) => set({ playback }),

  settings: null,
  setSettings: (settings) => set({ settings }),

  members: [],
  addMember: (m) =>
    set((state) => {
      if (state.members.find((x) => x.id === m.id)) return state
      return { members: [...state.members, m] }
    }),
  removeMember: (member_id) =>
    set((state) => ({
      members: state.members.filter((m) => m.id !== member_id),
    })),
}))
