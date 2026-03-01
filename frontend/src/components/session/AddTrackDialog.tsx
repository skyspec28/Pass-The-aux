"use client"

import { useState } from "react"
import { toast } from "sonner"
import { Link2, Loader2, Plus } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { addTrack, ApiError } from "@/lib/api"
import { useSessionStore } from "@/store/session"

interface Props {
  code: string
}

export default function AddTrackDialog({ code }: Props) {
  const auth = useSessionStore((s) => s.auth)
  const [open, setOpen] = useState(false)
  const [url, setUrl] = useState("")
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!auth || !url.trim()) return
    setLoading(true)
    try {
      await addTrack(code, url.trim(), auth.token)
      toast.success("Track added — resolving metadata…")
      setUrl("")
      setOpen(false)
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 409) {
          toast.error("This track is already in the queue")
        } else if (err.status === 429) {
          toast.error("Slow down! Track add rate limit reached")
        } else if (err.status === 422) {
          toast.error("Couldn\u2019t parse that URL — try a direct Spotify, YouTube, or Apple Music link")
        } else {
          toast.error(err.message)
        }
      } else {
        toast.error("Something went wrong")
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button className="bg-violet-600 hover:bg-violet-500 gap-2">
          <Plus className="h-4 w-4" />
          Add track
        </Button>
      </DialogTrigger>
      <DialogContent className="bg-zinc-900 border-zinc-800 text-white">
        <DialogHeader>
          <DialogTitle>Add a track</DialogTitle>
          <DialogDescription className="text-zinc-400">
            Paste a Spotify, YouTube, or Apple Music link
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4 mt-2">
          <div className="space-y-2">
            <Label htmlFor="track-url" className="text-zinc-300">
              Track URL
            </Label>
            <div className="relative">
              <Link2 className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-500" />
              <Input
                id="track-url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://open.spotify.com/track/..."
                className="pl-10 bg-zinc-800 border-zinc-700 text-white placeholder:text-zinc-600"
                autoFocus
              />
            </div>
            <p className="text-xs text-zinc-500">
              Supports Spotify, YouTube, and Apple Music URLs
            </p>
          </div>
          <div className="flex gap-2 justify-end">
            <Button
              type="button"
              variant="ghost"
              className="text-zinc-400 hover:text-white"
              onClick={() => setOpen(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              className="bg-violet-600 hover:bg-violet-500"
              disabled={loading || !url.trim()}
            >
              {loading && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
              Add to queue
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
