"use client";

import { useCallback, useMemo } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

const DEMO_STORAGE_KEY = "legal_ai_demo_mode";

export function useDemoMode() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const isDemo = useMemo(() => {
    const fromQuery = searchParams.get("demo");
    if (fromQuery === "true") {
      if (typeof window !== "undefined") {
        localStorage.setItem(DEMO_STORAGE_KEY, "true");
      }
      return true;
    }
    if (fromQuery === "false") {
      if (typeof window !== "undefined") {
        localStorage.removeItem(DEMO_STORAGE_KEY);
      }
      return false;
    }
    if (typeof window !== "undefined") {
      return localStorage.getItem(DEMO_STORAGE_KEY) === "true";
    }
    return false;
  }, [searchParams]);

  const setDemo = useCallback(
    (next: boolean) => {
      const params = new URLSearchParams(searchParams.toString());
      if (next) {
        params.set("demo", "true");
        if (typeof window !== "undefined") {
          localStorage.setItem(DEMO_STORAGE_KEY, "true");
        }
      } else {
        params.delete("demo");
        if (typeof window !== "undefined") {
          localStorage.removeItem(DEMO_STORAGE_KEY);
        }
      }
      const query = params.toString();
      router.replace(query ? `${pathname}?${query}` : pathname);
    },
    [pathname, router, searchParams],
  );

  return { isDemo, setDemo };
}

