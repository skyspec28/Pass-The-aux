"use client"

import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { Music2 } from "lucide-react"
import TrackCard from "./TrackCard"
import { useSessionStore } from "@/store/session"

interface Props {
  code: string
}

export default function QueueList({ code }: Props) {
  const queue = useSessionStore((s) => s.queue)
  const queued = queue.filter((t) => t.status === "QUEUED")

  if (queued.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-zinc-600 gap-3 py-16">
        <Music2 className="h-10 w-10" />
        <p className="text-sm">No tracks in the queue yet</p>
        <p className="text-xs">Be the first to add one!</p>
      </div>
    )
  }

  return (
    <ScrollArea className="h-full">
      <div>
        {queued.map((track, i) => (
          <div key={track.id}>
            <TrackCard track={track} code={code} rank={i + 1} />
            {i < queued.length - 1 && <Separator className="bg-zinc-800/50" />}
          </div>
        ))}
      </div>
    </ScrollArea>
  )
}
