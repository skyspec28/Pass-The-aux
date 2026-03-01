"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { toast } from "sonner"
import { Loader2, Music2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { createSession } from "@/lib/api"
import { storeAuth } from "@/lib/auth"
import { ApiError } from "@/lib/api"

const schema = z.object({
  title: z.string().min(1, "Party name is required").max(100),
})
type FormValues = z.infer<typeof schema>

export default function CreateSessionForm() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema) })

  const onSubmit = async (data: FormValues) => {
    setLoading(true)
    try {
      const res = await createSession(data.title)
      storeAuth(res.host_token, res.code)
      toast.success(`Party created! Code: ${res.code}`)
      router.push(`/session/${res.code}`)
    } catch (err) {
      if (err instanceof ApiError) {
        toast.error(err.message)
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
        <Label htmlFor="title">Party name</Label>
        <Input
          id="title"
          placeholder="Friday Night Vibes"
          {...register("title")}
          className="bg-zinc-800 border-zinc-700"
        />
        {errors.title && (
          <p className="text-sm text-destructive">{errors.title.message}</p>
        )}
      </div>
      <Button type="submit" className="w-full bg-violet-600 hover:bg-violet-500" disabled={loading}>
        {loading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Music2 className="h-4 w-4 mr-2" />}
        Create Party
      </Button>
    </form>
  )
}
