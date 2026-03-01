"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { toast } from "sonner"
import { Loader2, UserPlus } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { joinSession, ApiError } from "@/lib/api"
import { storeAuth } from "@/lib/auth"

const schema = z.object({
  code: z.string().min(1, "Session code is required").max(8).toUpperCase(),
  display_name: z.string().min(1, "Display name is required").max(40),
})
type FormValues = z.infer<typeof schema>

interface Props {
  defaultCode?: string
}

export default function JoinSessionForm({ defaultCode }: Props) {
  const router = useRouter()
  const [loading, setLoading] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { code: defaultCode ?? "" },
  })

  const onSubmit = async (data: FormValues) => {
    setLoading(true)
    try {
      const res = await joinSession(data.code, data.display_name)
      storeAuth(res.member_token, data.code)
      toast.success(`Joined as ${data.display_name}!`)
      router.push(`/session/${data.code}`)
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 409) {
          toast.error("That display name is already taken in this session")
        } else if (err.status === 404) {
          toast.error("Session not found — check the code and try again")
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
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="code">Session code</Label>
        <Input
          id="code"
          placeholder="PARTY1"
          {...register("code")}
          className="bg-zinc-800 border-zinc-700 uppercase tracking-widest font-mono"
        />
        {errors.code && (
          <p className="text-sm text-destructive">{errors.code.message}</p>
        )}
      </div>
      <div className="space-y-2">
        <Label htmlFor="display_name">Your name</Label>
        <Input
          id="display_name"
          placeholder="Alice"
          {...register("display_name")}
          className="bg-zinc-800 border-zinc-700"
        />
        {errors.display_name && (
          <p className="text-sm text-destructive">{errors.display_name.message}</p>
        )}
      </div>
      <Button type="submit" className="w-full" variant="secondary" disabled={loading}>
        {loading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <UserPlus className="h-4 w-4 mr-2" />}
        Join Party
      </Button>
    </form>
  )
}
