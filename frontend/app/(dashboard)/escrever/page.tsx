"use client"

import type React from "react"
import { useState } from "react"
// Adicionei o icone 'FileCode' para o botão do TeX
import { PenTool, Upload, FileText, Loader2, CheckCircle, AlertCircle, Download, FileCode } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"

export default function EscreverPage() {
  const [formatType, setFormatType] = useState<string>("")
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [isFormatting, setIsFormatting] = useState(false)
  const [statusMessage, setStatusMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)
  
  // NOVO: Estado para armazenar os links de download retornados pela API
  const [downloadLinks, setDownloadLinks] = useState<{ pdf: string, tex: string } | null>(null)

  const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api"

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      const validTypes = ["application/pdf", "text/plain"]
      if (validTypes.includes(file.type) || file.name.toLowerCase().endsWith('.txt') || file.name.toLowerCase().endsWith('.pdf')) {
        setSelectedFile(file)
        setStatusMessage(null)
        setDownloadLinks(null) // Reseta os downloads se trocar o arquivo
      } else {
        alert("Por favor, selecione apenas arquivos PDF ou TXT.")
      }
    }
  }

  const handleFormat = async () => {
    if (!selectedFile || !formatType) return

    setIsFormatting(true)
    setStatusMessage(null)
    setDownloadLinks(null)

    const formData = new FormData()
    formData.append("file", selectedFile)
    formData.append("style", formatType)
    formData.append("filename", selectedFile.name) 

    try {
      const response = await fetch(`${API_BASE_URL}/format/`, {
        method: "POST",
        body: formData,
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.error || "Erro ao processar o arquivo.")
      }

      // --- SUCESSO ---
      // Agora salvamos as URLs retornadas pelo backend
      setDownloadLinks({
        pdf: `${API_BASE_URL}${data.pdf_download_url}`, 
        tex: `${API_BASE_URL}${data.tex_download_url}`
      })

      setStatusMessage({
        type: 'success',
        text: "Formatação concluída! Escolha o formato para baixar abaixo."
      })

    } catch (error) {
      console.error("Erro na formatação:", error)
      setStatusMessage({
        type: 'error',
        text: error instanceof Error ? error.message : "Ocorreu um erro ao gerar o PDF."
      })
    } finally {
      setIsFormatting(false)
    }
  }

  // Função auxiliar para baixar arquivos
  const handleDownload = (url: string) => {
    // Abre a URL em uma nova aba/janela para disparar o download
    window.open(url, '_blank')
  }

  return (
    <div className="container mx-auto max-w-4xl space-y-8 p-6">
      {/* ... Header e outras partes (Style Select, Upload) permanecem iguais ... */}
      
      {/* Header (MANTIDO) */}
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

        {/* --- Card 1: Estilo (MANTIDO IGUAL) --- */}
        <Card>
            <CardHeader><CardTitle>1. Escolha do estilo</CardTitle></CardHeader>
            <CardContent>
             <div className="space-y-2">
              <Label htmlFor="format-type">Estilo de Formatação</Label>
              <Select value={formatType} onValueChange={setFormatType}>
                <SelectTrigger id="format-type" className="w-full">
                  <SelectValue placeholder="Selecione uma norma..." />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ABNT">ABNT</SelectItem>
                  <SelectItem value="APA">APA</SelectItem>
                  <SelectItem value="IEEE">IEEE</SelectItem>
                  <SelectItem value="SBC">SBC</SelectItem>
                  <SelectItem value="ICML ">ICML </SelectItem>
                  <SelectItem value="NeurIPS ">NeurIPS </SelectItem>
                  <SelectItem value="AAAI ">AAAI </SelectItem>
                  <SelectItem value="Springer Nature Template">Springer Nature Template</SelectItem>
                  <SelectItem value="Elsevier LaTeX Template">Elsevier LaTeX Template</SelectItem>
                </SelectContent>
              </Select>
            </div>
            </CardContent>
        </Card>

        {/* --- Card 2: Upload (MANTIDO IGUAL) --- */}
        <Card>
            <CardHeader><CardTitle>2. Upload do arquivo</CardTitle></CardHeader>
            <CardContent>
                <div className="space-y-4">
                    <div className="flex flex-col space-y-2 sm:flex-row sm:items-center sm:gap-4 sm:space-y-0">
                        <Button variant="outline" onClick={() => document.getElementById("file-upload")?.click()} disabled={isFormatting}>
                            <Upload className="mr-2 h-4 w-4" /> Selecionar arquivo
                        </Button>
                        <input id="file-upload" type="file" accept=".pdf,.txt" onChange={handleFileChange} className="hidden"/>
                        {selectedFile && (
                            <div className="flex items-center gap-2 rounded-lg border p-3">
                                <FileText className="h-5 w-5 text-blue-600"/>
                                <span className="text-sm font-medium">{selectedFile.name}</span>
                                <Button variant="ghost" size="icon" onClick={() => setSelectedFile(null)} className="h-8 w-8">✕</Button>
                            </div>
                        )}
                    </div>
                </div>
            </CardContent>
        </Card>

        {/* --- AÇÃO DE GERAR --- */}
        {!downloadLinks && (
            <div className="flex justify-center pt-4">
            <Button
                onClick={handleFormat}
                disabled={isFormatting || !selectedFile || !formatType}
                size="lg"
                className="w-full max-w-md text-base shadow-lg hover:shadow-xl transition-all"
            >
                {isFormatting ? (
                <>
                    <Loader2 className="mr-2 h-5 w-5 animate-spin" /> Gerando PDF com IA...
                </>
                ) : (
                <>
                    <Download className="mr-2 h-5 w-5" /> Formatar Texto
                </>
                )}
            </Button>
            </div>
        )}

        {/* --- ÁREA DE DOWNLOAD (APARECE SÓ DEPOIS DO SUCESSO) --- */}
        {downloadLinks && (
            <Card className="border-green-200 bg-green-50/50 dark:border-green-900 dark:bg-green-900/10">
                <CardHeader>
                    <CardTitle className="text-green-800 dark:text-green-400">Download Disponível</CardTitle>
                    <CardDescription>Seu texto foi formatado com sucesso. Escolha o formato:</CardDescription>
                </CardHeader>
                <CardContent className="flex flex-col sm:flex-row gap-4 justify-center">
                    
                    <Button 
                        onClick={() => handleDownload(downloadLinks.pdf)}
                        className="flex-1 shadow-lg hover:shadow-xl transition-all"
                        size="lg"
                    >
                        <FileText className="mr-2 h-5 w-5" /> Baixar PDF
                    </Button>

                    <Button 
                        onClick={() => handleDownload(downloadLinks.tex)}
                        className="flex-1 shadow-lg hover:shadow-xl transition-all"
                        size="lg"
                    >
                        <FileCode className="mr-2 h-5 w-5" /> Baixar Código LaTeX (.tex)
                    </Button>

                </CardContent>
                <div className="flex justify-center pb-6">
                    <Button variant="link" onClick={() => setDownloadLinks(null)} className="text-sm text-gray-500">
                        Formatar outro arquivo
                    </Button>
                </div>
            </Card>
        )}

      </div>
    </div>
  )
}