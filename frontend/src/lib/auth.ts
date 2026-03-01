"use client"

import type { AuthClaims, StoredAuth } from "@/types/api"

const KEY = "pta_auth"

export function parseJwt(token: string): AuthClaims {
  const base64 = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/")
  const json = decodeURIComponent(
    atob(base64)
      .split("")
      .map((c) => "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2))
      .join("")
  )
  return JSON.parse(json) as AuthClaims
}

export function storeAuth(token: string, code: string): StoredAuth {
  const claims = parseJwt(token)
  const auth: StoredAuth = { token, claims, code }
  localStorage.setItem(KEY, JSON.stringify(auth))
  return auth
}

export function getAuth(): StoredAuth | null {
  if (typeof window === "undefined") return null
  try {
    const raw = localStorage.getItem(KEY)
    if (!raw) return null
    const auth = JSON.parse(raw) as StoredAuth
    if (auth.claims.exp * 1000 < Date.now()) {
      clearAuth()
      return null
    }
    return auth
  } catch {
    return null
  }
}

export function clearAuth(): void {
  if (typeof window !== "undefined") {
    localStorage.removeItem(KEY)
  }
}
