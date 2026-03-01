"use client"

import { toast } from "sonner"
import { Crown, ShieldCheck, User, MoreVertical, VolumeX, Ban } from "lucide-react"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { ScrollArea } from "@/components/ui/scroll-area"
import { banMember, muteMember, ApiError } from "@/lib/api"
import { useSessionStore } from "@/store/session"

interface Props {
  code: string
}

function roleIcon(role: string) {
  if (role === "HOST") return <Crown className="h-3 w-3 text-amber-400" />
  if (role === "MOD") return <ShieldCheck className="h-3 w-3 text-blue-400" />
  return <User className="h-3 w-3 text-zinc-500" />
}

export default function MemberList({ code }: Props) {
  const auth = useSessionStore((s) => s.auth)
  const members = useSessionStore((s) => s.members)
  const canModerate = auth?.claims.role === "HOST" || auth?.claims.role === "MOD"

  const handleBan = async (memberId: string) => {
    if (!auth) return
    try {
      await banMember(code, memberId, auth.token)
      toast.success("Member removed")
    } catch (err) {
      if (err instanceof ApiError) toast.error(err.message)
    }
  }

  const handleMute = async (memberId: string) => {
    if (!auth) return
    try {
      await muteMember(code, memberId, 300, auth.token)
      toast.success("Member muted for 5 minutes")
    } catch (err) {
      if (err instanceof ApiError) toast.error(err.message)
    }
  }

  if (members.length === 0) {
    return (
      <div className="p-4">
        <p className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-3">
          Members
        </p>
        <p className="text-xs text-zinc-600">No members yet</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 pb-2">
        <p className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">
          Members ({members.length})
        </p>
      </div>
      <ScrollArea className="flex-1">
        <div className="px-2 pb-4 space-y-1">
          {members.map((member) => (
            <div
              key={member.id}
              className="flex items-center gap-2.5 px-2 py-2 rounded-lg hover:bg-zinc-800/50 group"
            >
              <Avatar className="h-7 w-7 shrink-0">
                <AvatarFallback className="bg-zinc-700 text-zinc-200 text-xs">
                  {member.display_name.slice(0, 2).toUpperCase()}
                </AvatarFallback>
              </Avatar>

              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1">
                  {roleIcon(member.role)}
                  <span className="text-sm text-zinc-300 truncate">{member.display_name}</span>
                  {member.id === auth?.claims.sub && (
                    <Badge variant="outline" className="text-[10px] py-0 px-1 border-zinc-700 text-zinc-500 ml-1">
                      You
                    </Badge>
                  )}
                </div>
              </div>

              {canModerate && member.id !== auth?.claims.sub && member.role !== "HOST" && (
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      size="icon"
                      variant="ghost"
                      className="h-6 w-6 opacity-0 group-hover:opacity-100 text-zinc-500 hover:text-zinc-300"
                    >
                      <MoreVertical className="h-3.5 w-3.5" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent
                    align="end"
                    className="bg-zinc-800 border-zinc-700 text-zinc-200"
                  >
                    <DropdownMenuItem
                      className="hover:bg-zinc-700 cursor-pointer gap-2"
                      onClick={() => handleMute(member.id)}
                    >
                      <VolumeX className="h-3.5 w-3.5" />
                      Mute 5 min
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      className="hover:bg-red-950 text-red-400 cursor-pointer gap-2"
                      onClick={() => handleBan(member.id)}
                    >
                      <Ban className="h-3.5 w-3.5" />
                      Ban
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              )}
            </div>
          ))}
        </div>
      </ScrollArea>
    </div>
  )
}
