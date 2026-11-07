"use client";

import { ThemeProvider as NextThemesProvider } from "next-themes";

// Thin wrapper so the provider can be used from the server layout.
export function ThemeProvider(props: React.ComponentProps<typeof NextThemesProvider>) {
  return <NextThemesProvider {...props} />;
}
