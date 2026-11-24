import { lazy, Suspense } from "react";
import { NavLink, Route, Routes } from "react-router";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

// Each page is its own chunk, so the first load does not pull in every form and table.
const CampaignsPage = lazy(() =>
  import("@/pages/CampaignsPage").then((module) => ({ default: module.CampaignsPage })),
);
const NewCampaignPage = lazy(() =>
  import("@/pages/NewCampaignPage").then((module) => ({ default: module.NewCampaignPage })),
);
const CampaignPage = lazy(() =>
  import("@/pages/editor/CampaignPage").then((module) => ({ default: module.CampaignPage })),
);

const NAV = [
  { to: "/", label: "Campaigns" },
  { to: "/new", label: "New campaign" },
];

export default function App() {
  return (
    <div className="min-h-svh bg-muted/40">
      <header className="border-b bg-background">
        <nav className="mx-auto flex max-w-5xl items-center gap-2 px-6 py-3">
          <span className="mr-4 font-semibold">Adrobot</span>
          {NAV.map((item) => (
            <NavLink key={item.to} to={item.to} end>
              {({ isActive }) => (
                <Button variant={isActive ? "secondary" : "ghost"} size="sm" tabIndex={-1}>
                  {item.label}
                </Button>
              )}
            </NavLink>
          ))}
        </nav>
      </header>
      <main className="mx-auto max-w-5xl px-6 py-8">
        <Suspense fallback={<Skeleton className="h-48 w-full" />}>
          <Routes>
            <Route path="/" element={<CampaignsPage />} />
            <Route path="/new" element={<NewCampaignPage />} />
            <Route path="/campaigns/:id" element={<CampaignPage />} />
          </Routes>
        </Suspense>
      </main>
    </div>
  );
}
