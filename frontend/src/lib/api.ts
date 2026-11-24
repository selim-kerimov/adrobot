export type OfferState = "active" | "removed";
export type State = "active" | "disabled";
export type Switch = "enable" | "disable";

export interface StreamOffer {
  id: number;
  offer_id: number;
  offer_name: string;
  share: number;
  state: OfferState;
  pinned: boolean;
  is_draft: boolean;
}

export interface Stream {
  id: number;
  keitaro_id: number;
  name: string;
  position: number;
  state: State;
  has_offers: boolean;
  is_draft: boolean;
  offers: StreamOffer[];
}

export interface CampaignListItem {
  keitaro_id: number;
  name: string;
  state: State;
  /** null while the campaign has never been loaded into the editor. */
  synced_at: string | null;
}

export interface Campaign {
  keitaro_id: number;
  name: string;
  alias: string | null;
  state: State;
  synced_at: string | null;
  streams: Stream[];
}

export interface Option {
  id: number;
  name: string;
}

export interface CampaignOptions {
  domains: Option[];
  groups: Option[];
  traffic_sources: Option[];
}

export interface CampaignCreate {
  name: string;
  countries: string[];
  offer_id: number;
  domain_id: number;
  group_id: number;
  traffic_source_id: number;
}

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const response = await fetch(`/api${path}`, {
    method,
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(response.status, errorMessage(data) ?? `HTTP ${response.status}`);
  }
  return data as T;
}

// FastAPI sends {"detail": "..."} for our errors and {"detail": [{msg}]} for validation.
function errorMessage(data: unknown): string | undefined {
  if (typeof data !== "object" || data === null || !("detail" in data)) return undefined;
  const { detail } = data;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((item) => item.msg).join("; ");
  return undefined;
}

export const api = {
  campaigns: () => request<CampaignListItem[]>("GET", "/campaigns"),
  campaign: (id: number) => request<Campaign>("GET", `/campaigns/${id}`),
  fetchCampaign: (id: number) => request<Campaign>("POST", `/campaigns/${id}/fetch`),
  renameCampaign: (id: number, name: string) =>
    request<Campaign>("PATCH", `/campaigns/${id}`, { name }),
  switchCampaign: (id: number, to: Switch) => request<Campaign>("POST", `/campaigns/${id}/${to}`),
  deleteCampaign: (id: number) => request<null>("DELETE", `/campaigns/${id}`),
  createCampaign: (data: CampaignCreate) => request<Campaign>("POST", "/campaigns", data),
  campaignOptions: () => request<CampaignOptions>("GET", "/campaign-options"),
  offers: (query: string) => request<Option[]>("GET", `/offers?q=${encodeURIComponent(query)}`),

  fetchStream: (streamId: number) => request<Stream>("POST", `/streams/${streamId}/fetch`),
  switchStream: (streamId: number, to: Switch) =>
    request<Stream>("POST", `/streams/${streamId}/${to}`),
  deleteStream: (streamId: number) => request<null>("DELETE", `/streams/${streamId}`),

  addOffer: (streamId: number, offerId: number) =>
    request<Stream>("POST", `/streams/${streamId}/offers`, { offer_id: offerId }),
  push: (streamId: number) => request<Stream>("POST", `/streams/${streamId}/push`),
  cancel: (streamId: number) => request<Stream>("POST", `/streams/${streamId}/cancel`),
  removeOffer: (id: number) => request<Stream>("POST", `/offers/${id}/remove`),
  restoreOffer: (id: number) => request<Stream>("POST", `/offers/${id}/restore`),
  pin: (id: number, share?: number) => request<Stream>("PUT", `/offers/${id}/pin`, { share }),
  unpin: (id: number) => request<Stream>("DELETE", `/offers/${id}/pin`),
};
