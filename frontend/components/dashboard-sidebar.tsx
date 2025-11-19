"use client"

import { Search, GraduationCap, Menu, Brain, PenTool, FileText, MessageSquareText } from "lucide-react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet"
// --- NOVOS IMPORTS ---
import { Badge } from "@/components/ui/badge"


const menuItems = [
  {
    title: "Explorar Artigos",
    icon: Search,
    href: "/explorar",
  },
  // --- NOVO ITEM DO CHAT ---
  {
    title: "Chat Inteligente",
    icon: MessageSquareText,
    href: "/chat",
  },
  {
    title: "Analisar com IA",
    icon: Brain,
    href: "/analisar",
  },
  {
    title: "Assistente de Escrita",
    icon: PenTool,
    href: "/escrever",
  },
  {
    title: "Meus Projetos", // Renomeado para consistência
    icon: FileText,
    href: "/projetos",
  },
]

function SidebarContent() {
  const pathname = usePathname()
  
  // --- HOOK DO CONTADOR ---
 

  return (
    <div className="flex h-full flex-col">
      <Link href="/dashboard" className="block border-b border-border">
        <div className="flex items-center gap-3 px-6 py-5 transition-colors hover:bg-gray-50 dark:hover:bg-gray-800">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-600 dark:bg-blue-500">
            <GraduationCap className="h-6 w-6 text-white" />
          </div>
          <div className="flex flex-col">
            <span className="text-lg font-semibold tracking-tight text-foreground">Research Flow</span>
            <span className="text-xs text-muted-foreground">Pesquisa com IA</span>
          </div>
        </div>
      </Link>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 p-4">
        {menuItems.map((item) => {
          const isActive = pathname === item.href
          return (
            <Link key={item.href} href={item.href}>
              <div
                className={cn(
                  "flex items-center gap-3 rounded-lg px-4 py-3 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-blue-600 text-white dark:bg-blue-500"
                    : "text-gray-700 hover:bg-gray-100 dark:text-gray-100 dark:hover:bg-gray-800",
                )}
              >
                <item.icon className="h-5 w-5" />
                <span className="flex-1">{item.title}</span>
                
              </div>
            </Link>
          )
        })}
      </nav>
    </div>
  )
}

export function DashboardSidebar() {
  return (
    <>
      {/* Desktop Sidebar */}
      <aside className="hidden h-screen w-64 border-r border-border bg-white dark:bg-gray-900 lg:block">
        <SidebarContent />
      </aside>

      {/* Mobile Sidebar */}
      <Sheet>
        <SheetTrigger asChild>
          <Button variant="ghost" size="icon" className="lg:hidden">
            <Menu className="h-6 w-6" />
          </Button>
        </SheetTrigger>
        <SheetContent side="left" className="w-64 p-0">
          <SidebarContent />
        </SheetContent>
      </Sheet>
    </>
  )
}