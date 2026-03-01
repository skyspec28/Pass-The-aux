"use client"

import Image from "next/image"
import { ChevronUp, ChevronDown, X, Music } from "lucide-react"
import { toast } from "sonner"
import { useState } from "react"
import { cn, formatDuration, formatScore } from "@/lib/utils"
import { castVote, removeVote, removeTrack, ApiError } from "@/lib/api"
import { useSessionStore } from "@/store/session"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import type { SessionTrackOut } from "@/types/api"

interface Props {
  track: SessionTrackOut
  code: string
  rank?: number
}

export default function TrackCard({ track, code, rank }: Props) {
  const auth = useSessionStore((s) => s.auth)
  const isHost = auth?.claims.role === "HOST"
  const isMod = auth?.claims.role === "MOD"
  const isPending = track.track.metadata_status === "PENDING"

  const [myVote, setMyVote] = useState<1 | -1 | null>(null)
  const [voting, setVoting] = useState(false)

  const handleVote = async (value: 1 | -1) => {
    if (!auth || voting) return
    setVoting(true)
    try {
      if (myVote === value) {
        // Toggle off
        await removeVote(code, track.id, auth.token)
        setMyVote(null)
      } else {
        await castVote(code, track.id, value, auth.token)
        setMyVote(value)
      }
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 429) {
          toast.error("Slow down! Vote rate limit reached")
        } else if (err.status === 403) {
          toast.error("Downvotes are disabled in this session")
        } else {
          toast.error(err.message)
        }
      }
    } finally {
      setVoting(false)
    }
  }

  const handleRemove = async () => {
    if (!auth) return
    try {
      await removeTrack(code, track.id, auth.token)
    } catch (err) {
      if (err instanceof ApiError) toast.error(err.message)
    }
  }

  return (
    <div
      className={cn(
        "flex items-center gap-3 px-4 py-3 group hover:bg-zinc-800/50 transition-colors",
        track.status === "PLAYING" && "bg-violet-950/30 border-l-2 border-violet-500"
      )}
    >
      {/* Rank */}
      {rank !== undefined && (
        <span className="text-xs text-zinc-600 w-5 text-center shrink-0">{rank}</span>
      )}

      {/* Artwork */}
      <div className="relative h-12 w-12 shrink-0 rounded-md overflow-hidden bg-zinc-800">
        {track.track.artwork_url ? (
          <Image
            src={track.track.artwork_url}
            alt={track.track.title ?? "track"}
            fill
            className="object-cover"
            unoptimized
          />
        ) : (
          <div className="flex items-center justify-center h-full">
            <Music className="h-5 w-5 text-zinc-600" />
          </div>
        )}
        {isPending && (
          <div className="absolute inset-0 bg-black/60 flex items-center justify-center">
            <div className="h-3 w-3 rounded-full border-2 border-violet-400 border-t-transparent animate-spin" />
          </div>
        )}
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        {isPending ? (
          <div className="space-y-1">
            <Skeleton className="h-4 w-32 bg-zinc-700" />
            <Skeleton className="h-3 w-20 bg-zinc-800" />
          </div>
        ) : (
          <>
            <p className="text-sm font-medium text-white truncate leading-tight">
              {track.track.title ?? "Unknown title"}
            </p>
            <p className="text-xs text-zinc-500 truncate">
              {track.track.artist ?? track.track.provider}
              {track.track.duration_ms && (
                <span className="ml-1">· {formatDuration(track.track.duration_ms)}</span>
              )}
            </p>
          </>
        )}
      </div>

      {/* Score + Votes */}
      <div className="flex items-center gap-1 shrink-0">
        <Button
          size="icon"
          variant="ghost"
          className={cn(
            "h-7 w-7 rounded-full",
            myVote === 1
              ? "text-violet-400 bg-violet-950"
              : "text-zinc-500 hover:text-violet-400 hover:bg-violet-950/50"
          )}
          onClick={() => handleVote(1)}
          disabled={voting}
        >
          <ChevronUp className="h-4 w-4" />
        </Button>

        <span
          className={cn(
            "text-sm font-bold w-8 text-center tabular-nums",
            track.score_cached > 0 ? "text-violet-400" : track.score_cached < 0 ? "text-red-400" : "text-zinc-500"
          )}
        >
          {formatScore(track.score_cached)}
        </span>

        <Button
          size="icon"
          variant="ghost"
          className={cn(
            "h-7 w-7 rounded-full",
            myVote === -1
              ? "text-red-400 bg-red-950"
              : "text-zinc-500 hover:text-red-400 hover:bg-red-950/50"
          )}
          onClick={() => handleVote(-1)}
          disabled={voting}
        >
          <ChevronDown className="h-4 w-4" />
        </Button>

        {(isHost || isMod) && (
          <Button
            size="icon"
            variant="ghost"
            className="h-7 w-7 rounded-full text-zinc-700 hover:text-red-400 hover:bg-red-950/30 opacity-0 group-hover:opacity-100 transition-opacity ml-1"
            onClick={handleRemove}
          >
            <X className="h-3.5 w-3.5" />
          </Button>
        )}
      </div>
    </div>
  )
}
