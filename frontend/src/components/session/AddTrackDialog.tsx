"use client"

import { useState } from "react"
import { toast } from "sonner"
import { Link2, ListMusic, Loader2, Plus } from "lucide-react"
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { addTrack, importPlaylist, ApiError } from "@/lib/api"
import { useSessionStore } from "@/store/session"

interface Props {
  code: string
}

export default function AddTrackDialog({ code }: Props) {
  const auth = useSessionStore((s) => s.auth)
  const [open, setOpen] = useState(false)
  const [url, setUrl] = useState("")
  const [playlistUrl, setPlaylistUrl] = useState("")
  const [loading, setLoading] = useState(false)

  const isHostOrMod = auth?.claims.role === "HOST" || auth?.claims.role === "MOD"

  const handleAddTrack = async (e: React.FormEvent) => {
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

  const handleImportPlaylist = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!auth || !playlistUrl.trim()) return
    setLoading(true)
    try {
      const result = await importPlaylist(code, playlistUrl.trim(), auth.token)
      const parts = [`${result.added} added`]
      if (result.skipped > 0) parts.push(`${result.skipped} skipped`)
      if (result.errors > 0) parts.push(`${result.errors} failed`)
      toast.success(`Playlist imported: ${parts.join(", ")}`)
      setPlaylistUrl("")
      setOpen(false)
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 503) {
          toast.error("Spotify credentials not configured on this server")
        } else if (err.status === 502) {
          toast.error("Could not fetch the playlist from Spotify")
        } else if (err.status === 422) {
          toast.error("Only Spotify playlist URLs are supported right now")
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
          <DialogTitle>Add music</DialogTitle>
          <DialogDescription className="text-zinc-400">
            Add a single track or import a whole Spotify playlist
          </DialogDescription>
        </DialogHeader>

        <Tabs defaultValue="track" className="mt-2">
          <TabsList className="bg-zinc-800 w-full">
            <TabsTrigger value="track" className="flex-1 data-[state=active]:bg-zinc-700">
              <Link2 className="h-3.5 w-3.5 mr-1.5" />
              Single track
            </TabsTrigger>
            {isHostOrMod && (
              <TabsTrigger value="playlist" className="flex-1 data-[state=active]:bg-zinc-700">
                <ListMusic className="h-3.5 w-3.5 mr-1.5" />
                Import playlist
              </TabsTrigger>
            )}
          </TabsList>

          <TabsContent value="track">
            <form onSubmit={handleAddTrack} className="space-y-4 mt-3">
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
          </TabsContent>

          {isHostOrMod && (
            <TabsContent value="playlist">
              <form onSubmit={handleImportPlaylist} className="space-y-4 mt-3">
                <div className="space-y-2">
                  <Label htmlFor="playlist-url" className="text-zinc-300">
                    Spotify Playlist URL
                  </Label>
                  <div className="relative">
                    <ListMusic className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-500" />
                    <Input
                      id="playlist-url"
                      value={playlistUrl}
                      onChange={(e) => setPlaylistUrl(e.target.value)}
                      placeholder="https://open.spotify.com/playlist/..."
                      className="pl-10 bg-zinc-800 border-zinc-700 text-white placeholder:text-zinc-600"
                    />
                  </div>
                  <p className="text-xs text-zinc-500">
                    All tracks in the playlist will be added to the queue.
                    Duplicates are skipped automatically.
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
                    disabled={loading || !playlistUrl.trim()}
                  >
                    {loading && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
                    Import playlist
                  </Button>
                </div>
              </form>
            </TabsContent>
          )}
        </Tabs>
      </DialogContent>
    </Dialog>
  )
}
