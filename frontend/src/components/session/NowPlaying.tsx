"use client"

import Image from "next/image"
import { Music } from "lucide-react"
import { cn, formatDuration } from "@/lib/utils"
import { useSessionStore } from "@/store/session"

interface Props {
  code: string
}

export default function NowPlaying({ code: _code }: Props) {
  const queue = useSessionStore((s) => s.queue)
  const playback = useSessionStore((s) => s.playback)

  const currentTrack = playback?.current_session_track_id
    ? queue.find((t) => t.id === playback.current_session_track_id)
    : null

  const isPlaying = playback?.state === "PLAYING"
  const isPaused = playback?.state === "PAUSED"

  return (
    <div className="flex flex-col items-center gap-4 p-6">
      {/* Artwork */}
      <div
        className={cn(
          "relative h-48 w-48 rounded-2xl overflow-hidden bg-zinc-800 shadow-2xl",
          isPlaying && "ring-2 ring-violet-500 ring-offset-2 ring-offset-zinc-950"
        )}
      >
        {currentTrack?.track.artwork_url ? (
          <Image
            src={currentTrack.track.artwork_url}
            alt={currentTrack.track.title ?? "now playing"}
            fill
            className={cn("object-cover transition-all duration-500", isPlaying && "scale-105")}
            unoptimized
          />
        ) : (
          <div className="flex items-center justify-center h-full">
            <Music className="h-16 w-16 text-zinc-600" />
          </div>
        )}
        {isPaused && (
          <div className="absolute inset-0 bg-black/40 flex items-center justify-center">
            <div className="text-white text-xs font-medium tracking-wider uppercase">Paused</div>
          </div>
        )}
      </div>

      {/* Track info */}
      <div className="text-center min-w-0 w-full px-2">
        {currentTrack ? (
          <>
            <p className="text-white font-semibold truncate leading-tight">
              {currentTrack.track.title ?? "Unknown track"}
            </p>
            <p className="text-zinc-400 text-sm truncate mt-0.5">
              {currentTrack.track.artist ?? currentTrack.track.provider}
            </p>
            {currentTrack.track.duration_ms && (
              <p className="text-zinc-600 text-xs mt-1">
                {formatDuration(currentTrack.track.duration_ms)}
              </p>
            )}
          </>
        ) : (
          <>
            <p className="text-zinc-500 font-medium">Nothing playing</p>
            <p className="text-zinc-600 text-sm mt-0.5">
              {playback?.state === "STOPPED" ? "Queue up a track to get started" : "Press play to start"}
            </p>
          </>
        )}
      </div>

      {/* State badge */}
      {playback?.state === "PLAYING" && (
        <div className="flex items-center gap-1.5">
          <div className="flex gap-0.5 items-end h-4">
            {[1, 2, 3, 4].map((i) => (
              <div
                key={i}
                className="w-1 bg-violet-500 rounded-sm animate-pulse"
                style={{
                  height: `${[12, 16, 10, 14][i - 1]}px`,
                  animationDelay: `${i * 0.15}s`,
                }}
              />
            ))}
          </div>
          <span className="text-violet-400 text-xs font-medium tracking-wide">PLAYING</span>
        </div>
      )}
    </div>
  )
}
