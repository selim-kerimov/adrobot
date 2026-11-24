import { useQuery } from "@tanstack/react-query";
import { PlusIcon } from "lucide-react";
import { Link } from "react-router";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from "@/components/ui/empty";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { api } from "@/lib/api";

export function CampaignsPage() {
  const campaigns = useQuery({ queryKey: ["campaigns"], queryFn: api.campaigns });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Campaigns</CardTitle>
        <CardDescription>All campaigns in Keitaro. Open one to edit its offers.</CardDescription>
        <CardAction>
          <Button asChild size="sm">
            <Link to="/new">
              <PlusIcon data-icon="inline-start" />
              New campaign
            </Link>
          </Button>
        </CardAction>
      </CardHeader>
      <CardContent>
        {campaigns.isPending ? (
          <Skeleton className="h-32 w-full" />
        ) : campaigns.isError ? (
          <Alert variant="destructive">
            <AlertTitle>Could not load campaigns</AlertTitle>
            <AlertDescription>{campaigns.error.message}</AlertDescription>
          </Alert>
        ) : campaigns.data.length === 0 ? (
          <Empty>
            <EmptyHeader>
              <EmptyTitle>No campaigns in Keitaro</EmptyTitle>
              <EmptyDescription>Create the first one.</EmptyDescription>
            </EmptyHeader>
          </Empty>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-24">ID</TableHead>
                <TableHead>Name</TableHead>
                <TableHead className="w-56">In Adrobot</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {campaigns.data.map((campaign) => (
                <TableRow key={campaign.keitaro_id}>
                  <TableCell>{campaign.keitaro_id}</TableCell>
                  <TableCell className="flex items-center gap-2">
                    <Link
                      className="underline-offset-4 hover:underline"
                      to={`/campaigns/${campaign.keitaro_id}`}
                    >
                      {campaign.name}
                    </Link>
                    {campaign.state === "disabled" && <Badge variant="secondary">Disabled</Badge>}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {campaign.synced_at ? (
                      `Fetched ${new Date(campaign.synced_at).toLocaleString()}`
                    ) : (
                      <Badge variant="outline">Not loaded yet</Badge>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}
