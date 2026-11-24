import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { DownloadIcon, EllipsisIcon, PencilIcon, Trash2Icon } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { toast } from "sonner";

import { ConfirmDialog } from "@/components/ConfirmDialog";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyTitle,
} from "@/components/ui/empty";
import { Skeleton } from "@/components/ui/skeleton";
import { Spinner } from "@/components/ui/spinner";
import { Switch } from "@/components/ui/switch";
import { ApiError, api, type Campaign } from "@/lib/api";
import { RenameDialog } from "@/pages/editor/RenameDialog";
import { StreamCard } from "@/pages/editor/StreamCard";

export function CampaignPage() {
  const id = Number(useParams().id);
  const queryClient = useQueryClient();

  const campaign = useQuery({
    queryKey: ["campaign", id],
    queryFn: () => loadCampaign(id),
    retry: false,
  });

  const fetchStreams = useMutation({
    mutationFn: () => api.fetchCampaign(id),
    onSuccess: (data) => {
      queryClient.setQueryData(["campaign", id], data);
      queryClient.invalidateQueries({ queryKey: ["campaigns"] });
    },
    onError: (error) => {
      toast.error(error.message);
      // Deleted in Keitaro: the backend dropped it, reload to show that.
      if (isNotFound(error)) {
        queryClient.invalidateQueries({ queryKey: ["campaign", id] });
        queryClient.invalidateQueries({ queryKey: ["campaigns"] });
      }
    },
  });

  const fetchButton = (
    <Button
      variant="outline"
      disabled={fetchStreams.isPending}
      onClick={() => fetchStreams.mutate()}
    >
      {fetchStreams.isPending ? (
        <Spinner data-icon="inline-start" />
      ) : (
        <DownloadIcon data-icon="inline-start" />
      )}
      Fetch streams
    </Button>
  );

  if (campaign.isPending) {
    return (
      <div className="flex flex-col gap-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-48 w-full" />
      </div>
    );
  }

  if (campaign.isError) {
    if (isNotFound(campaign.error)) {
      return (
        <Empty>
          <EmptyHeader>
            <EmptyTitle>Campaign #{id} not found</EmptyTitle>
            <EmptyDescription>
              It does not exist in Keitaro, or it was deleted there.
            </EmptyDescription>
          </EmptyHeader>
          <EmptyContent>
            <Button asChild variant="outline">
              <Link to="/">Back to campaigns</Link>
            </Button>
          </EmptyContent>
        </Empty>
      );
    }
    return (
      <Alert variant="destructive">
        <AlertTitle>Could not load the campaign</AlertTitle>
        <AlertDescription>{campaign.error.message}</AlertDescription>
      </Alert>
    );
  }

  const { name, alias, streams } = campaign.data;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="flex flex-col gap-1">
          <h1 className="text-2xl font-semibold">{name}</h1>
          <p className="text-sm text-muted-foreground">
            Keitaro campaign #{id}
            {alias && ` · ${alias}`}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {fetchButton}
          <CampaignMenu campaign={campaign.data} />
        </div>
      </div>
      {streams.map((stream) => (
        <StreamCard key={stream.id} campaignId={id} stream={stream} />
      ))}
    </div>
  );
}

function CampaignMenu({ campaign }: { campaign: Campaign }) {
  const id = campaign.keitaro_id;
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [dialog, setDialog] = useState<"rename" | "delete" | null>(null);

  const onSaved = (data: Campaign) => {
    queryClient.setQueryData(["campaign", id], data);
    queryClient.invalidateQueries({ queryKey: ["campaigns"] });
  };
  const toggle = useMutation({
    mutationFn: (enabled: boolean) => api.switchCampaign(id, enabled ? "enable" : "disable"),
    onSuccess: onSaved,
    onError: (error) => toast.error(error.message),
  });
  const rename = useMutation({
    mutationFn: (name: string) => api.renameCampaign(id, name),
    onSuccess: (data) => {
      onSaved(data);
      setDialog(null);
    },
    onError: (error) => toast.error(error.message),
  });
  const remove = useMutation({
    mutationFn: () => api.deleteCampaign(id),
    onSuccess: () => {
      queryClient.removeQueries({ queryKey: ["campaign", id] });
      queryClient.invalidateQueries({ queryKey: ["campaigns"] });
      toast.success(`Campaign ${campaign.name} deleted`);
      navigate("/");
    },
    onError: (error) => toast.error(error.message),
  });

  return (
    <>
      <label className="flex items-center gap-2 px-2 text-sm">
        {toggle.isPending && <Spinner />}
        <Switch
          checked={campaign.state === "active"}
          disabled={toggle.isPending}
          onCheckedChange={(enabled) => toggle.mutate(enabled)}
        />
        {campaign.state === "active" ? "Enabled" : "Disabled"}
      </label>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="outline" size="icon" aria-label="Campaign actions">
            <EllipsisIcon />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-48">
          <DropdownMenuGroup>
            <DropdownMenuItem onSelect={() => setDialog("rename")}>
              <PencilIcon />
              Rename
            </DropdownMenuItem>
            <DropdownMenuItem variant="destructive" onSelect={() => setDialog("delete")}>
              <Trash2Icon />
              Delete campaign
            </DropdownMenuItem>
          </DropdownMenuGroup>
        </DropdownMenuContent>
      </DropdownMenu>
      <RenameDialog
        open={dialog === "rename"}
        onOpenChange={(open) => setDialog(open ? "rename" : null)}
        name={campaign.name}
        pending={rename.isPending}
        onRename={(name) => rename.mutate(name)}
      />
      <ConfirmDialog
        open={dialog === "delete"}
        onOpenChange={(open) => setDialog(open ? "delete" : null)}
        title={`Delete ${campaign.name}?`}
        description="The campaign and all its streams are deleted in Keitaro. Keitaro has no archive, so this cannot be undone."
        action="Delete"
        pending={remove.isPending}
        onConfirm={() => remove.mutate()}
      />
    </>
  );
}

/** A campaign seen for the first time is loaded from Keitaro right away. */
async function loadCampaign(id: number) {
  try {
    return await api.campaign(id);
  } catch (error) {
    if (isNotFound(error)) return api.fetchCampaign(id);
    throw error;
  }
}

function isNotFound(error: unknown) {
  return error instanceof ApiError && error.status === 404;
}
