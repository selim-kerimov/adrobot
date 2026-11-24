import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  EllipsisIcon,
  PinIcon,
  RefreshCwIcon,
  RotateCcwIcon,
  Trash2Icon,
  UndoIcon,
  UploadIcon,
} from "lucide-react";
import { useState, type KeyboardEvent } from "react";
import { toast } from "sonner";

import { ConfirmDialog } from "@/components/ConfirmDialog";
import { OfferPicker } from "@/components/OfferPicker";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { Switch } from "@/components/ui/switch";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Toggle } from "@/components/ui/toggle";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import {
  ApiError,
  api,
  type Campaign,
  type Option,
  type Stream,
  type StreamOffer,
} from "@/lib/api";
import { cn } from "@/lib/utils";

/** Every editor action returns the whole stream, so the cache is patched in place. */
function useStreamAction<T>(campaignId: number, action: (input: T) => Promise<Stream>) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: action,
    onSuccess: (stream) => {
      queryClient.setQueryData<Campaign>(
        ["campaign", campaignId],
        (campaign) =>
          campaign && {
            ...campaign,
            streams: campaign.streams.map((item) => (item.id === stream.id ? stream : item)),
          },
      );
    },
    onError: (error) => {
      toast.error(error.message);
      // Deleted in Keitaro: the backend dropped the stream, reload the campaign to show that.
      if (error instanceof ApiError && error.status === 404) {
        queryClient.invalidateQueries({ queryKey: ["campaign", campaignId] });
      }
    },
  });
}

interface StreamCardProps {
  campaignId: number;
  stream: Stream;
}

export function StreamCard({ campaignId, stream }: StreamCardProps) {
  const add = useStreamAction(campaignId, (offer: Option) => api.addOffer(stream.id, offer.id));
  const push = useStreamAction(campaignId, () => api.push(stream.id));
  const cancel = useStreamAction(campaignId, () => api.cancel(stream.id));

  if (!stream.has_offers) {
    return (
      <Card size="sm">
        <CardHeader>
          <CardTitle>{stream.name}</CardTitle>
          <CardDescription>No offers in this stream, nothing to edit here.</CardDescription>
          <CardAction>
            <StreamActions campaignId={campaignId} stream={stream} />
          </CardAction>
        </CardHeader>
      </Card>
    );
  }

  const busy = push.isPending || cancel.isPending;

  return (
    <Card className={cn(stream.is_draft && "ring-2 ring-warning")}>
      <CardHeader>
        <CardTitle>{stream.name}</CardTitle>
        <CardDescription>Keitaro stream #{stream.keitaro_id}</CardDescription>
        <CardAction className="flex items-center gap-2">
          {stream.is_draft && <Badge variant="outline">Not published</Badge>}
          <StreamActions campaignId={campaignId} stream={stream} />
        </CardAction>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Offer</TableHead>
              <TableHead className="w-32">Share</TableHead>
              <TableHead className="w-28 text-right" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {stream.offers.map((offer) => (
              <OfferRow key={offer.id} campaignId={campaignId} offer={offer} />
            ))}
          </TableBody>
        </Table>
      </CardContent>
      <CardFooter className="flex-wrap gap-2">
        <div className="min-w-60 flex-1">
          <OfferPicker
            value={null}
            placeholder={add.isPending ? `Adding ${add.variables.name}…` : "Add offer…"}
            loading={add.isPending}
            onChange={(offer) => add.mutate(offer)}
          />
        </div>
        <Button
          variant="outline"
          disabled={!stream.is_draft || busy}
          onClick={() => cancel.mutate(undefined)}
        >
          {cancel.isPending ? (
            <Spinner data-icon="inline-start" />
          ) : (
            <UndoIcon data-icon="inline-start" />
          )}
          Cancel
        </Button>
        <Button disabled={!stream.is_draft || busy} onClick={() => push.mutate(undefined)}>
          {push.isPending ? (
            <Spinner data-icon="inline-start" />
          ) : (
            <UploadIcon data-icon="inline-start" />
          )}
          Push to Keitaro
        </Button>
      </CardFooter>
    </Card>
  );
}

function StreamActions({ campaignId, stream }: StreamCardProps) {
  const queryClient = useQueryClient();
  const [confirming, setConfirming] = useState(false);
  const toggle = useStreamAction(campaignId, (enabled: boolean) =>
    api.switchStream(stream.id, enabled ? "enable" : "disable"),
  );
  const refresh = useStreamAction(campaignId, () => api.fetchStream(stream.id));
  const remove = useMutation({
    mutationFn: () => api.deleteStream(stream.id),
    onSuccess: () => {
      queryClient.setQueryData<Campaign>(
        ["campaign", campaignId],
        (campaign) =>
          campaign && {
            ...campaign,
            streams: campaign.streams.filter((item) => item.id !== stream.id),
          },
      );
      toast.success(`Stream ${stream.name} deleted`);
    },
    onError: (error) => toast.error(error.message),
  });

  return (
    <div className="flex items-center gap-2">
      <label className="flex items-center gap-2 text-sm text-muted-foreground">
        {toggle.isPending && <Spinner />}
        <Switch
          size="sm"
          checked={stream.state === "active"}
          disabled={toggle.isPending}
          onCheckedChange={(enabled) => toggle.mutate(enabled)}
        />
        {stream.state === "active" ? "Enabled" : "Disabled"}
      </label>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="icon-sm" aria-label="Stream actions">
            {refresh.isPending ? <Spinner /> : <EllipsisIcon />}
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-48">
          <DropdownMenuGroup>
            <DropdownMenuItem onSelect={() => refresh.mutate(undefined)}>
              <RefreshCwIcon />
              Reload from Keitaro
            </DropdownMenuItem>
            <DropdownMenuItem variant="destructive" onSelect={() => setConfirming(true)}>
              <Trash2Icon />
              Delete stream
            </DropdownMenuItem>
          </DropdownMenuGroup>
        </DropdownMenuContent>
      </DropdownMenu>
      <ConfirmDialog
        open={confirming}
        onOpenChange={setConfirming}
        title={`Delete ${stream.name}?`}
        description="The stream is deleted in Keitaro. Keitaro has no archive, so this cannot be undone."
        action="Delete"
        pending={remove.isPending}
        onConfirm={() => remove.mutate()}
      />
    </div>
  );
}

interface OfferRowProps {
  campaignId: number;
  offer: StreamOffer;
}

function OfferRow({ campaignId, offer }: OfferRowProps) {
  const remove = useStreamAction(campaignId, () => api.removeOffer(offer.id));
  const restore = useStreamAction(campaignId, () => api.restoreOffer(offer.id));
  const pin = useStreamAction(campaignId, (share?: number) => api.pin(offer.id, share));
  const unpin = useStreamAction(campaignId, () => api.unpin(offer.id));
  const removed = offer.state === "removed";
  const pinning = pin.isPending || unpin.isPending;

  return (
    <TableRow className={cn(offer.is_draft && "bg-warning/15", removed && "text-muted-foreground")}>
      <TableCell className={cn("max-w-0 truncate", removed && "line-through")}>
        {offer.offer_name}
      </TableCell>
      <TableCell>
        {removed ? (
          "0%"
        ) : (
          <ShareInput
            // Remount when the share changes elsewhere so the field shows the new value.
            key={offer.share}
            share={offer.share}
            disabled={pin.isPending}
            onCommit={(share) => pin.mutate(share)}
          />
        )}
      </TableCell>
      <TableCell className="text-right">
        {removed ? (
          <Button
            variant="ghost"
            size="sm"
            disabled={restore.isPending}
            onClick={() => restore.mutate(undefined)}
          >
            {restore.isPending ? (
              <Spinner data-icon="inline-start" />
            ) : (
              <RotateCcwIcon data-icon="inline-start" />
            )}
            Bring back
          </Button>
        ) : (
          <div className="flex justify-end gap-1">
            <Tooltip>
              <TooltipTrigger asChild>
                <Toggle
                  size="sm"
                  // The pressed background looks like hover, so a pinned offer also gets
                  // a border and a filled icon.
                  variant={offer.pinned ? "outline" : "default"}
                  aria-label="Pin share"
                  pressed={offer.pinned}
                  disabled={pinning}
                  onPressedChange={(pressed) =>
                    pressed ? pin.mutate(undefined) : unpin.mutate(undefined)
                  }
                >
                  {pinning ? (
                    <Spinner />
                  ) : (
                    <PinIcon fill={offer.pinned ? "currentColor" : "none"} />
                  )}
                </Toggle>
              </TooltipTrigger>
              <TooltipContent>
                {offer.pinned ? "Pinned: kept when shares are recalculated" : "Pin share"}
              </TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon-sm"
                  aria-label="Remove offer"
                  disabled={remove.isPending}
                  onClick={() => remove.mutate(undefined)}
                >
                  {remove.isPending ? <Spinner /> : <Trash2Icon />}
                </Button>
              </TooltipTrigger>
              <TooltipContent>Remove</TooltipContent>
            </Tooltip>
          </div>
        )}
      </TableCell>
    </TableRow>
  );
}

interface ShareInputProps {
  share: number;
  disabled: boolean;
  onCommit: (share: number) => void;
}

/** Typing a share pins it: the other offers split what is left. */
function ShareInput({ share, disabled, onCommit }: ShareInputProps) {
  const [value, setValue] = useState(String(share));

  function commit() {
    const next = Number(value);
    if (value === "" || !Number.isInteger(next) || next < 0 || next > 100) {
      setValue(String(share));
      return;
    }
    if (next !== share) onCommit(next);
  }

  function onKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Enter") event.currentTarget.blur();
    if (event.key === "Escape") setValue(String(share));
  }

  return (
    <div className="flex items-center gap-1">
      <Input
        type="number"
        min={0}
        max={100}
        className="h-7 w-16"
        aria-label="Share, %"
        value={value}
        disabled={disabled}
        onChange={(event) => setValue(event.target.value)}
        onBlur={commit}
        onKeyDown={onKeyDown}
      />
      %
    </div>
  );
}
