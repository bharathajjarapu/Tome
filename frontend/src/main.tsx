import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { BrowserRouter, Navigate, Route, Routes } from "react-router"
import "streamdown/styles.css"
import "./index.css"

import { gettoken, subscribe } from "@/api/token"
import { RequireAuth } from "@/auth"
import { Chat } from "@/routes/chat"
import { DocumentsPage } from "@/routes/documents"
import { Login } from "@/routes/login"
import { Project } from "@/routes/project"
import { Projects } from "@/routes/projects"

// The system preference is the whole theme system; there is no toggle to build.
const dark = matchMedia("(prefers-color-scheme: dark)")
const paint = () => document.documentElement.classList.toggle("dark", dark.matches)
dark.addEventListener("change", paint)
paint()

const queries = new QueryClient({ defaultOptions: { queries: { retry: false } } })
subscribe(() => {
  if (!gettoken()) queries.clear()
})

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queries}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route element={<RequireAuth />}>
            <Route path="/" element={<Projects />} />
            <Route path="/projects/:projectid" element={<Project />}>
              <Route index element={<Chat />} />
              <Route path="c/:conversationid" element={<Chat />} />
              <Route path="documents" element={<DocumentsPage />} />
            </Route>
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
)
