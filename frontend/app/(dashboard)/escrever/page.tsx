"use client"

import type React from "react"
import { useState } from "react"
import { PenTool, Upload, FileText, Loader2, CheckCircle, AlertCircle, Download } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"

export default function EscreverPage() {
  const [formatType, setFormatType] = useState<string>("")
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [isFormatting, setIsFormatting] = useState(false)
  const [statusMessage, setStatusMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)

  // URL da API
  const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api"

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      const validTypes = ["application/pdf", "text/plain"]
      // Verifica extensão e MIME type
      if (validTypes.includes(file.type) || file.name.toLowerCase().endsWith('.txt') || file.name.toLowerCase().endsWith('.pdf')) {
        setSelectedFile(file)
        setStatusMessage(null)
      } else {
        alert("Por favor, selecione apenas arquivos PDF ou TXT.")
      }
    }
  }

  const handleFormat = async () => {
    if (!selectedFile) {
      setStatusMessage({ type: 'error', text: "Por favor, faça upload de um arquivo." })
      return
    }
    if (!formatType) {
      setStatusMessage({ type: 'error', text: "Por favor, escolha um estilo de formatação." })
      return
    }

    setIsFormatting(true)
    setStatusMessage(null)

    const formData = new FormData()
    formData.append("file", selectedFile)
    formData.append("style", formatType)
    formData.append("filename", selectedFile.name) 

    try {
      const response = await fetch(`${API_BASE_URL}/format/`, {
        method: "POST",
        body: formData,
      })

      if (!response.ok) {
        let errorMessage = "Erro ao processar o arquivo."
        try {
          const errorData = await response.json()
          errorMessage = errorData.error || errorMessage
        } catch (e) {
          console.warn("Erro não é JSON válido.")
        }
        throw new Error(errorMessage)
      }

      // --- LÓGICA DE DOWNLOAD DO ARQUIVO ---
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      
      const originalName = selectedFile.name.split('.')[0]
      a.download = `${originalName}_formatado_${formatType}.pdf`
      
      document.body.appendChild(a)
      a.click()
      a.remove()
      window.URL.revokeObjectURL(url)
      // -------------------------------------

      setStatusMessage({
        type: 'success',
        text: "Texto formatado com sucesso! O download começou automaticamente."
      })

    } catch (error) {
      console.error("Erro na formatação:", error)
      setStatusMessage({
        type: 'error',
        text: error instanceof Error ? error.message : "Ocorreu um erro ao gerar o PDF. Verifique se o texto original não contém caracteres inválidos."
      })
    } finally {
      setIsFormatting(false)
    }
  }

  return (
    <div className="container mx-auto max-w-4xl space-y-8 p-6">
      {/* Header */}
      <div className="space-y-2">
        <div className="flex items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-blue-100 dark:bg-blue-900/30">
            <PenTool className="h-6 w-6 text-blue-600 dark:text-blue-400" />
          </div>
          <div>
            <h1 className="text-3xl font-semibold tracking-tight text-gray-900 dark:text-gray-100">
              Assistente de Escrita
            </h1>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Formate seu texto acadêmico automaticamente para LaTeX/PDF usando IA
            </p>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="space-y-6">
        
        {/* Status Message */}
        {statusMessage && (
          <div className={`p-4 rounded-md flex items-center gap-3 border ${
            statusMessage.type === 'success' 
              ? 'bg-green-50 border-green-200 text-green-800 dark:bg-green-900/20 dark:border-green-800 dark:text-green-300' 
              : 'bg-red-50 border-red-200 text-red-800 dark:bg-red-900/20 dark:border-red-800 dark:text-red-300'
          }`}>
            {statusMessage.type === 'success' ? <CheckCircle className="h-5 w-5"/> : <AlertCircle className="h-5 w-5"/>}
            <p className="font-medium">{statusMessage.text}</p>
          </div>
        )}

        {/* 1. Estilo */}
        <Card>
          <CardHeader>
            <CardTitle>1. Escolha do estilo</CardTitle>
            <CardDescription>Selecione o padrão de formatação</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <Label htmlFor="format-type">Estilo de Formatação</Label>
              <Select value={formatType} onValueChange={setFormatType}>
                <SelectTrigger id="format-type" className="w-full">
                  <SelectValue placeholder="Selecione uma norma..." />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="abnt">ABNT</SelectItem>
                  <SelectItem value="apa">APA</SelectItem>
                  <SelectItem value="ieee">IEEE</SelectItem>
                  <SelectItem value="sbc">SBC</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        {/* 2. Upload */}
        <Card>
          <CardHeader>
            <CardTitle>2. Upload do arquivo</CardTitle>
            <CardDescription>Envie seu rascunho (PDF ou TXT)</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex flex-col space-y-2 sm:flex-row sm:items-center sm:gap-4 sm:space-y-0">
                <Button
                  variant="outline"
                  onClick={() => document.getElementById("file-upload")?.click()}
                  className="w-full sm:w-auto"
                  disabled={isFormatting}
                >
                  <Upload className="mr-2 h-4 w-4" />
                  Selecionar arquivo
                </Button>
                <input
                  id="file-upload"
                  type="file"
                  accept=".pdf,.txt"
                  onChange={handleFileChange}
                  className="hidden"
                />
                {selectedFile && (
                  <div className="flex items-center gap-2 rounded-lg border border-gray-200 bg-gray-50 p-3 dark:border-gray-700 dark:bg-gray-800 w-full sm:w-auto">
                    <FileText className="h-5 w-5 text-blue-600 dark:text-blue-400 flex-shrink-0" />
                    <div className="flex flex-col">
                        <span className="text-sm font-medium text-gray-700 dark:text-gray-300 truncate max-w-[200px]">
                            {selectedFile.name}
                        </span>
                    </div>
                    <Button 
                        variant="ghost" 
                        size="icon" 
                        onClick={() => setSelectedFile(null)} 
                        className="ml-auto h-8 w-8 text-gray-500 hover:text-red-500"
                        disabled={isFormatting}
                    >
                      ✕
                    </Button>
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Botão de Ação */}
        <div className="flex justify-center pt-4">
          <Button
            onClick={handleFormat}
            disabled={isFormatting || !selectedFile || !formatType}
            size="lg"
            className="w-full max-w-md text-base shadow-lg hover:shadow-xl transition-all"
          >
            {isFormatting ? (
              <>
                <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                Gerando PDF com IA (Pode demorar)...
              </>
            ) : (
              <>
                <Download className="mr-2 h-5 w-5" />
                Formatar e Baixar PDF
              </>
            )}
          </Button>
        </div>
      </div>
    </div>
  )
}