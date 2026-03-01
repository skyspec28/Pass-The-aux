"use client"

import { Copy, Settings, Music2 } from "lucide-react"
import { toast } from "sonner"
import Link from "next/link"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { useSessionStore } from "@/store/session"

interface Props {
  code: string
  title: string
}

export default function SessionHeader({ code, title }: Props) {
  const auth = useSessionStore((s) => s.auth)
  const isHost = auth?.claims.role === "HOST"

  const copyCode = () => {
    navigator.clipboard.writeText(code).then(() => toast.success("Code copied!"))
  }

  return (
    <header className="flex items-center justify-between px-4 py-3 bg-zinc-900 border-b border-zinc-800">
      <div className="flex items-center gap-3 min-w-0">
        <div className="rounded-lg bg-violet-600 p-1.5 shrink-0">
          <Music2 className="h-5 w-5 text-white" />
        </div>
        <div className="min-w-0">
          <h1 className="text-white font-semibold text-sm leading-tight truncate">{title}</h1>
          <div className="flex items-center gap-1.5 mt-0.5">
            <Badge
              variant="outline"
              className="text-xs font-mono tracking-widest border-zinc-700 text-zinc-400 cursor-pointer hover:border-violet-500 hover:text-violet-400 transition-colors"
              onClick={copyCode}
            >
              {code}
            </Badge>
            <Button
              size="icon"
              variant="ghost"
              className="h-5 w-5 text-zinc-500 hover:text-zinc-300"
              onClick={copyCode}
            >
              <Copy className="h-3 w-3" />
            </Button>
          </div>
        </div>
      </div>

      {isHost && (
        <Link href={`/session/${code}/settings`}>
          <Button size="icon" variant="ghost" className="text-zinc-400 hover:text-white">
            <Settings className="h-5 w-5" />
          </Button>
        </Link>
      )}
    </header>
  )
}
