"use client"

import Image from "next/image"
import { Play, Pause, SkipForward, Music } from "lucide-react"
import { toast } from "sonner"
import { cn, formatDuration } from "@/lib/utils"
import { startPlayback, pausePlayback, nextTrack, ApiError } from "@/lib/api"
import { useSessionStore } from "@/store/session"
import { Button } from "@/components/ui/button"
import AddTrackDialog from "./AddTrackDialog"

interface Props {
  code: string
}

export default function PlaybackBar({ code }: Props) {
  const auth = useSessionStore((s) => s.auth)
  const queue = useSessionStore((s) => s.queue)
  const playback = useSessionStore((s) => s.playback)
  const setPlayback = useSessionStore((s) => s.setPlayback)

  const isHost = auth?.claims.role === "HOST"
  const isPlaying = playback?.state === "PLAYING"

  const currentTrack = playback?.current_session_track_id
    ? queue.find((t) => t.id === playback.current_session_track_id)
    : null

  const handlePlayPause = async () => {
    if (!auth) return
    try {
      const result = isPlaying
        ? await pausePlayback(code, auth.token)
        : await startPlayback(code, auth.token)
      setPlayback(result)
    } catch (err) {
      if (err instanceof ApiError) toast.error(err.message)
    }
  }

  const handleNext = async () => {
    if (!auth) return
    try {
      const result = await nextTrack(code, auth.token)
      setPlayback(result)
    } catch (err) {
      if (err instanceof ApiError) toast.error(err.message)
    }
  }

  return (
    <div className="flex items-center justify-between px-4 py-3 bg-zinc-900 border-t border-zinc-800 gap-4">
      {/* Current track info */}
      <div className="flex items-center gap-3 min-w-0 flex-1">
        <div className="relative h-10 w-10 shrink-0 rounded-md overflow-hidden bg-zinc-800">
          {currentTrack?.track.artwork_url ? (
            <Image
              src={currentTrack.track.artwork_url}
              alt={currentTrack.track.title ?? "track"}
              fill
              className="object-cover"
              unoptimized
            />
          ) : (
            <div className="flex items-center justify-center h-full">
              <Music className="h-4 w-4 text-zinc-600" />
            </div>
          )}
        </div>
        <div className="min-w-0">
          <p className="text-sm text-white truncate leading-tight font-medium">
            {currentTrack?.track.title ?? (playback?.state === "STOPPED" ? "Nothing playing" : "—")}
          </p>
          <p className="text-xs text-zinc-500 truncate">
            {currentTrack?.track.artist ?? (isHost ? "Add a track to get started" : "Waiting for host")}
            {currentTrack?.track.duration_ms && (
              <span className="ml-1">· {formatDuration(currentTrack.track.duration_ms)}</span>
            )}
          </p>
        </div>
      </div>

      {/* Playback controls (HOST only) */}
      <div className="flex items-center gap-2 shrink-0">
        {isHost && (
          <>
            <Button
              size="icon"
              variant="ghost"
              className={cn(
                "h-9 w-9 rounded-full",
                isPlaying
                  ? "text-violet-400 hover:text-violet-300 bg-violet-950/50"
                  : "text-zinc-400 hover:text-white"
              )}
              onClick={handlePlayPause}
            >
              {isPlaying ? <Pause className="h-5 w-5" /> : <Play className="h-5 w-5" />}
            </Button>
            <Button
              size="icon"
              variant="ghost"
              className="h-9 w-9 rounded-full text-zinc-400 hover:text-white"
              onClick={handleNext}
            >
              <SkipForward className="h-5 w-5" />
            </Button>
          </>
        )}

        <AddTrackDialog code={code} />
      </div>
    </div>
  )
}
