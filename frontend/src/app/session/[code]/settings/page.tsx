"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { toast } from "sonner"
import { ArrowLeft, Loader2 } from "lucide-react"
import Link from "next/link"
import { getAuth } from "@/lib/auth"
import { updateSettings, ApiError } from "@/lib/api"
import { useSessionStore } from "@/store/session"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import { Switch } from "@/components/ui/switch"
import { Separator } from "@/components/ui/separator"
import type { SessionSettings } from "@/types/api"

interface Props {
  params: Promise<{ code: string }>
}

export default function SettingsPage({ params }: Props) {
  const router = useRouter()
  const [code, setCode] = useState<string | null>(null)

  const setAuth = useSessionStore((s) => s.setAuth)
  const auth = useSessionStore((s) => s.auth)
  const storeSettings = useSessionStore((s) => s.settings)
  const setStoreSettings = useSessionStore((s) => s.setSettings)

  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState<Partial<SessionSettings>>({})

  useEffect(() => {
    params.then(({ code: c }) => {
      setCode(c)
      const stored = getAuth()
      if (!stored || stored.claims.role !== "HOST") {
        router.push(`/session/${c}`)
        return
      }
      setAuth(stored)
    })
  }, [params, router, setAuth])

  useEffect(() => {
    if (storeSettings) {
      setForm(storeSettings)
    }
  }, [storeSettings])

  const update = (key: keyof SessionSettings, value: boolean | number) => {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  const handleSave = async () => {
    if (!auth || !code) return
    setSaving(true)
    try {
      const result = await updateSettings(code, form, auth.token)
      setStoreSettings(result.settings)
      toast.success("Settings saved")
    } catch (err) {
      if (err instanceof ApiError) toast.error(err.message)
      else toast.error("Failed to save settings")
    } finally {
      setSaving(false)
    }
  }

  if (!code || !auth) return null

  return (
    <div className="min-h-screen bg-zinc-950 text-white">
      {/* Header */}
      <header className="flex items-center gap-3 px-4 py-3 bg-zinc-900 border-b border-zinc-800">
        <Link href={`/session/${code}`}>
          <Button size="icon" variant="ghost" className="text-zinc-400 hover:text-white">
            <ArrowLeft className="h-5 w-5" />
          </Button>
        </Link>
        <h1 className="text-white font-semibold">Session settings</h1>
      </header>

      <div className="max-w-lg mx-auto p-6 space-y-6">
        {/* Track adds */}
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader>
            <CardTitle className="text-base text-white">Track additions</CardTitle>
            <CardDescription className="text-zinc-400">
              Control who can add tracks and how often
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="flex items-center justify-between">
              <div>
                <Label className="text-zinc-200">Allow guests to add tracks</Label>
                <p className="text-xs text-zinc-500 mt-0.5">When off, only the host can add</p>
              </div>
              <Switch
                checked={form.allow_guest_add ?? true}
                onCheckedChange={(v) => update("allow_guest_add", v)}
              />
            </div>
            <Separator className="bg-zinc-800" />
            <div className="flex items-center justify-between">
              <div>
                <Label className="text-zinc-200">Deduplicate tracks</Label>
                <p className="text-xs text-zinc-500 mt-0.5">Prevent the same track being added twice</p>
              </div>
              <Switch
                checked={form.dedupe_tracks ?? true}
                onCheckedChange={(v) => update("dedupe_tracks", v)}
              />
            </div>
            <Separator className="bg-zinc-800" />
            <div className="flex items-center justify-between gap-4">
              <div>
                <Label className="text-zinc-200">Max adds per guest (per 10 min)</Label>
                <p className="text-xs text-zinc-500 mt-0.5">Rate limit for track additions</p>
              </div>
              <Input
                type="number"
                min={1}
                max={50}
                value={form.max_adds_per_guest_per_10min ?? 3}
                onChange={(e) => update("max_adds_per_guest_per_10min", parseInt(e.target.value) || 3)}
                className="w-20 bg-zinc-800 border-zinc-700 text-center"
              />
            </div>
          </CardContent>
        </Card>

        {/* Voting */}
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader>
            <CardTitle className="text-base text-white">Voting</CardTitle>
            <CardDescription className="text-zinc-400">
              Configure how members can vote
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="flex items-center justify-between">
              <div>
                <Label className="text-zinc-200">Allow downvotes</Label>
                <p className="text-xs text-zinc-500 mt-0.5">Let members downvote tracks</p>
              </div>
              <Switch
                checked={form.allow_downvotes ?? true}
                onCheckedChange={(v) => update("allow_downvotes", v)}
              />
            </div>
            <Separator className="bg-zinc-800" />
            <div className="flex items-center justify-between gap-4">
              <div>
                <Label className="text-zinc-200">Max votes per guest (per min)</Label>
                <p className="text-xs text-zinc-500 mt-0.5">Rate limit for voting</p>
              </div>
              <Input
                type="number"
                min={1}
                max={100}
                value={form.max_votes_per_guest_per_min ?? 12}
                onChange={(e) => update("max_votes_per_guest_per_min", parseInt(e.target.value) || 12)}
                className="w-20 bg-zinc-800 border-zinc-700 text-center"
              />
            </div>
          </CardContent>
        </Card>

        {/* Fairness */}
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader>
            <CardTitle className="text-base text-white">Queue fairness</CardTitle>
            <CardDescription className="text-zinc-400">
              Prevent one person&apos;s tracks from dominating the queue
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="flex items-center justify-between">
              <div>
                <Label className="text-zinc-200">Enable fairness</Label>
                <p className="text-xs text-zinc-500 mt-0.5">Spread tracks from different members</p>
              </div>
              <Switch
                checked={form.fairness_enabled ?? true}
                onCheckedChange={(v) => update("fairness_enabled", v)}
              />
            </div>
            <Separator className="bg-zinc-800" />
            <div className="flex items-center justify-between gap-4">
              <div>
                <Label className="text-zinc-200">Cooldown (songs)</Label>
                <p className="text-xs text-zinc-500 mt-0.5">
                  Min tracks between adds by the same member
                </p>
              </div>
              <Input
                type="number"
                min={1}
                max={10}
                value={form.cooldown_songs ?? 1}
                onChange={(e) => update("cooldown_songs", parseInt(e.target.value) || 1)}
                className="w-20 bg-zinc-800 border-zinc-700 text-center"
                disabled={!form.fairness_enabled}
              />
            </div>
          </CardContent>
        </Card>

        {/* Save */}
        <Button
          className="w-full bg-violet-600 hover:bg-violet-500"
          onClick={handleSave}
          disabled={saving}
        >
          {saving && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
          Save settings
        </Button>
      </div>
    </div>
  )
}
