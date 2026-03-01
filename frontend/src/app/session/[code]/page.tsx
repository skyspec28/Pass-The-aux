"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { useQuery } from "@tanstack/react-query"
import { Skeleton } from "@/components/ui/skeleton"
import { Separator } from "@/components/ui/separator"
import { getSession, getTracks, getPlayback } from "@/lib/api"
import { getAuth } from "@/lib/auth"
import { useSessionStore } from "@/store/session"
import { useWebSocket } from "@/hooks/useWebSocket"
import SessionHeader from "@/components/session/SessionHeader"
import QueueList from "@/components/session/QueueList"
import NowPlaying from "@/components/session/NowPlaying"
import PlaybackBar from "@/components/session/PlaybackBar"
import MemberList from "@/components/session/MemberList"

interface Props {
  params: Promise<{ code: string }>
}

export default function SessionPage({ params }: Props) {
  const router = useRouter()
  const [code, setCode] = useState<string | null>(null)

  // Auth + store
  const setAuth = useSessionStore((s) => s.setAuth)
  const setQueue = useSessionStore((s) => s.setQueue)
  const setPlayback = useSessionStore((s) => s.setPlayback)
  const setSettings = useSessionStore((s) => s.setSettings)
  const addMember = useSessionStore((s) => s.addMember)
  const auth = useSessionStore((s) => s.auth)

  // Resolve params + auth on mount
  useEffect(() => {
    params.then(({ code: c }) => {
      setCode(c)
      const stored = getAuth()
      if (!stored) {
        router.push(`/?tab=join&join=${c}`)
        return
      }
      setAuth(stored)
    })
  }, [params, router, setAuth])

  // Seed self into member list
  useEffect(() => {
    if (!auth) return
    addMember({
      id: auth.claims.sub,
      session_id: auth.claims.session_id,
      display_name: "You",
      role: auth.claims.role,
      is_banned: false,
      muted_until: null,
      joined_at: new Date().toISOString(),
    })
  }, [auth, addMember])

  // Fetch session metadata
  const { data: session, isLoading: sessionLoading } = useQuery({
    queryKey: ["session", code],
    queryFn: () => getSession(code!, auth!.token),
    enabled: !!code && !!auth,
  })

  // Fetch initial track queue
  const { isLoading: tracksLoading } = useQuery({
    queryKey: ["tracks", code],
    queryFn: async () => {
      const tracks = await getTracks(code!, auth!.token, "QUEUED")
      setQueue(tracks)
      return tracks
    },
    enabled: !!code && !!auth,
  })

  // Fetch initial playback state
  useQuery({
    queryKey: ["playback", code],
    queryFn: async () => {
      const pb = await getPlayback(code!, auth!.token)
      setPlayback(pb)
      return pb
    },
    enabled: !!code && !!auth,
  })

  // Sync session settings to store
  useEffect(() => {
    if (session?.settings) setSettings(session.settings)
  }, [session, setSettings])

  // Connect WebSocket
  useWebSocket(code ?? "")

  if (!code || !auth) return null

  const isLoading = sessionLoading || tracksLoading

  return (
    <div className="flex flex-col h-screen bg-zinc-950">
      {/* Header */}
      {isLoading ? (
        <div className="flex items-center px-4 py-3 bg-zinc-900 border-b border-zinc-800 gap-3 h-[57px]">
          <Skeleton className="h-8 w-8 rounded-lg bg-zinc-800" />
          <div className="space-y-1.5">
            <Skeleton className="h-4 w-32 bg-zinc-800" />
            <Skeleton className="h-3 w-16 bg-zinc-800" />
          </div>
        </div>
      ) : (
        <SessionHeader code={code} title={session?.title ?? code} />
      )}

      {/* Body */}
      <div className="flex flex-1 min-h-0">
        {/* Left: Now Playing */}
        <div className="hidden lg:flex flex-col w-64 xl:w-72 bg-zinc-950 border-r border-zinc-800 shrink-0">
          <NowPlaying code={code} />
        </div>

        <Separator orientation="vertical" className="bg-zinc-800 hidden lg:block" />

        {/* Center: Queue */}
        <div className="flex-1 min-w-0 flex flex-col">
          <div className="flex items-center justify-between px-4 py-2.5 border-b border-zinc-800">
            <h2 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">
              Up next
            </h2>
          </div>
          <div className="flex-1 min-h-0">
            <QueueList code={code} />
          </div>
        </div>

        <Separator orientation="vertical" className="bg-zinc-800 hidden lg:block" />

        {/* Right: Members */}
        <div className="hidden lg:flex flex-col w-52 xl:w-60 bg-zinc-950 border-l border-zinc-800 shrink-0">
          <MemberList code={code} />
        </div>
      </div>

      {/* Playback bar */}
      <PlaybackBar code={code} />
    </div>
  )
}
