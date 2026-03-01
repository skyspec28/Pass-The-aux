"use client"

import { useEffect, useRef } from "react"
import { useRouter } from "next/navigation"
import { toast } from "sonner"
import { useSessionStore } from "@/store/session"
import { getSessionTrack } from "@/lib/api"
import type { WsEvent } from "@/types/api"

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8080/v1"

export function useWebSocket(code: string) {
  const router = useRouter()
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const mountedRef = useRef(true)

  const auth = useSessionStore((s) => s.auth)
  const setPlayback = useSessionStore((s) => s.setPlayback)
  const setSettings = useSessionStore((s) => s.setSettings)
  const upsertTrack = useSessionStore((s) => s.upsertTrack)
  const removeTrack = useSessionStore((s) => s.removeTrack)
  const reorderQueue = useSessionStore((s) => s.reorderQueue)
  const addMember = useSessionStore((s) => s.addMember)
  const removeMember = useSessionStore((s) => s.removeMember)
  const clearAuth = useSessionStore((s) => s.clearAuth)

  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
    }
  }, [])

  useEffect(() => {
    if (!auth?.token) return

    function connect() {
      if (!mountedRef.current) return
      const token = auth!.token
      const ws = new WebSocket(`${WS_BASE}/ws/sessions/${code}?token=${token}`)
      wsRef.current = ws

      ws.onopen = () => {
        if (reconnectRef.current) {
          clearTimeout(reconnectRef.current)
          reconnectRef.current = null
        }
      }

      ws.onmessage = async (event) => {
        let msg: WsEvent
        try {
          msg = JSON.parse(event.data as string) as WsEvent
        } catch {
          return
        }

        switch (msg.type) {
          case "queue.updated": {
            // Update scores on existing tracks then reorder
            const orderedIds = msg.data.queue.map((q) => q.session_track_id)
            reorderQueue(orderedIds)
            break
          }

          case "vote.updated": {
            // Scores are resynced via queue.updated which follows; nothing extra needed
            break
          }

          case "track.added":
          case "track.updated": {
            // Fetch full track data and upsert into queue
            try {
              const st = await getSessionTrack(code, msg.data.session_track_id, auth!.token)
              upsertTrack(st)
            } catch {
              // track may have been removed already
            }
            break
          }

          case "track.removed": {
            removeTrack(msg.data.session_track_id)
            break
          }

          case "playback.updated": {
            setPlayback(msg.data)
            break
          }

          case "session.updated": {
            setSettings(msg.data.settings)
            break
          }

          case "member.joined": {
            // Add a minimal member entry with display_name
            addMember({
              id: msg.data.member_id,
              session_id: "",
              display_name: msg.data.display_name,
              role: "GUEST",
              is_banned: false,
              muted_until: null,
              joined_at: new Date().toISOString(),
            })
            break
          }

          case "member.banned": {
            removeMember(msg.data.member_id)
            // If it's the current user, kick them
            if (auth!.claims.sub === msg.data.member_id) {
              toast.error("You have been removed from this session")
              clearAuth()
              router.push("/")
            }
            break
          }
        }
      }

      ws.onclose = (e) => {
        if (!mountedRef.current) return
        // Don't reconnect on policy violation (banned / bad token)
        if (e.code === 1008) return
        reconnectRef.current = setTimeout(connect, 3000)
      }

      ws.onerror = () => {
        ws.close()
      }
    }

    connect()

    return () => {
      mountedRef.current = false
      if (reconnectRef.current) clearTimeout(reconnectRef.current)
      wsRef.current?.close()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [code, auth?.token])
}
