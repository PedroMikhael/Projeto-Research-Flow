"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Trash2, Calendar, Bookmark, MessageSquareText } from "lucide-react"
import { useRouter } from "next/navigation"

export default function ProjetosPage() {
  const [savedArticles, setSavedArticles] = useState([])
  const router = useRouter()

  useEffect(() => {
    const savedItems = localStorage.getItem("researchFlowFavorites")
    const favorites = savedItems ? JSON.parse(savedItems) : []
    setSavedArticles(favorites)
  }, [])

  const handleDelete = (urlToDelete) => {
    const newFavorites = savedArticles.filter((item) => item.url !== urlToDelete)
    setSavedArticles(newFavorites)
    localStorage.setItem("researchFlowFavorites", JSON.stringify(newFavorites))
    window.dispatchEvent(new Event('favoritesChanged'))
  }

  const handleChat = (articleUrl) => {
    router.push(`/chat?url=${encodeURIComponent(articleUrl)}`)
  }

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Meus Artigos Salvos</h1>
        <p className="text-muted-foreground">
          Gerencie os artigos que você favoritou para leitura posterior.
        </p>
      </div>

      <div className="space-y-4">
        <h2 className="text-xl font-semibold">
          Artigos Salvos ({savedArticles.length})
        </h2>
        
        {savedArticles.length === 0 && (
            <Card className="text-center p-8 border-dashed">
                <Bookmark className="mx-auto h-12 w-12 text-gray-300" />
                <h3 className="mt-4 text-lg font-semibold">Nenhum artigo salvo</h3>
                <p className="mt-2 text-sm text-muted-foreground">
                    Vá para a página "Explorar Artigos" e clique no botão "Salvar" 
                    para adicionar seus favoritos aqui.
                </p>
            </Card>
        )}

        {savedArticles.map((article) => (
          <Card key={article.url} className="hover:shadow-md transition-shadow">
            <CardHeader>
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <CardTitle className="text-lg text-blue-600 hover:underline dark:text-blue-400">
                    <a href={article.url} target="_blank" rel="noopener noreferrer">
                        {article.title}
                    </a>
                  </CardTitle>
                  <CardDescription className="mt-2 flex flex-wrap items-center gap-4">
                    <Badge variant="secondary">
                      Citações: {article.citationCount}
                    </Badge>
                    <span className="flex items-center gap-1 text-xs">
                      <Calendar className="h-3 w-3" />
                      {article.year}
                    </span>
                  </CardDescription>
                  <p className="mt-2 text-sm text-gray-600 dark:text-gray-400 line-clamp-2">
                    {article.authors.join(", ")}
                  </p>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="flex gap-2">
                <Button onClick={() => handleChat(article.url)} size="sm" className="bg-blue-600 hover:bg-blue-700 text-white">
                  <MessageSquareText className="mr-2 h-4 w-4" />
                  Conversar com a IA
                </Button>
                <Button
                  onClick={() => handleDelete(article.url)}
                  variant="outline"
                  size="sm"
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  Remover
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}