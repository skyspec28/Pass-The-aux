import { Suspense } from "react"
import { Music2 } from "lucide-react"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import CreateSessionForm from "@/components/home/CreateSessionForm"
import JoinSessionForm from "@/components/home/JoinSessionForm"

interface SearchParams {
  join?: string
  tab?: string
}

export default async function HomePage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>
}) {
  const params = await searchParams
  const defaultTab = params.tab === "join" || params.join ? "join" : "create"

  return (
    <main className="min-h-screen bg-zinc-950 flex flex-col items-center justify-center p-4">
      <div className="w-full max-w-md space-y-8">
        <div className="text-center space-y-2">
          <div className="flex items-center justify-center gap-2">
            <div className="rounded-xl bg-violet-600 p-2">
              <Music2 className="h-8 w-8 text-white" />
            </div>
          </div>
          <h1 className="text-3xl font-bold text-white tracking-tight">PassTheAux</h1>
          <p className="text-zinc-400 text-sm">
            Collaborative party playlists — everyone votes, the best track plays next
          </p>
        </div>

        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader className="pb-4">
            <CardTitle className="text-white text-lg">Get started</CardTitle>
            <CardDescription className="text-zinc-400">
              Create a new party or join one with a code
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue={defaultTab} className="w-full">
              <TabsList className="w-full bg-zinc-800 mb-6">
                <TabsTrigger value="create" className="flex-1 data-[state=active]:bg-zinc-700">
                  Create party
                </TabsTrigger>
                <TabsTrigger value="join" className="flex-1 data-[state=active]:bg-zinc-700">
                  Join party
                </TabsTrigger>
              </TabsList>
              <TabsContent value="create">
                <Suspense fallback={null}>
                  <CreateSessionForm />
                </Suspense>
              </TabsContent>
              <TabsContent value="join">
                <Suspense fallback={null}>
                  <JoinSessionForm defaultCode={params.join} />
                </Suspense>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      </div>
    </main>
  )
}
