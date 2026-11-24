import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Controller, useForm, type Control } from "react-hook-form";
import { useNavigate } from "react-router";
import { toast } from "sonner";
import { z } from "zod";

import { OfferPicker } from "@/components/OfferPicker";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Field, FieldDescription, FieldError, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Spinner } from "@/components/ui/spinner";
import { api, type CampaignOptions, type Option } from "@/lib/api";

function parseCountries(value: string): string[] {
  const codes = value
    .toUpperCase()
    .split(/[\s,;]+/)
    .filter(Boolean);
  return [...new Set(codes)];
}

const isCountryCode = (code: string) => /^[A-Z]{2}$/.test(code);

const schema = z.object({
  name: z.string().trim().min(1, "Enter a campaign name"),
  geo: z
    .string()
    .refine((value) => parseCountries(value).length > 0, "Enter at least one country")
    .refine(
      (value) => parseCountries(value).every(isCountryCode),
      "Use two-letter country codes, e.g. AU",
    ),
  offer: z.object({ id: z.number(), name: z.string() }, { error: "Choose an offer" }),
  domainId: z.string().min(1, "Choose a domain"),
  groupId: z.string().min(1, "Choose a group"),
  sourceId: z.string().min(1, "Choose a source"),
});

type FormValues = z.infer<typeof schema>;

export function NewCampaignPage() {
  const options = useQuery({ queryKey: ["campaign-options"], queryFn: api.campaignOptions });

  return (
    <Card className="mx-auto w-full max-w-lg">
      <CardHeader>
        <CardTitle>New campaign</CardTitle>
        <CardDescription>
          Visitors from the selected countries go to Google, everyone else goes to the offer.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {options.isPending ? (
          <Skeleton className="h-96 w-full" />
        ) : options.isError ? (
          <Alert variant="destructive">
            <AlertTitle>Could not load domains, groups and sources</AlertTitle>
            <AlertDescription>{options.error.message}</AlertDescription>
          </Alert>
        ) : (
          <NewCampaignForm options={options.data} />
        )}
      </CardContent>
    </Card>
  );
}

function NewCampaignForm({ options }: { options: CampaignOptions }) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: "",
      geo: "",
      domainId: firstId(options.domains),
      groupId: firstId(options.groups),
      sourceId: firstId(options.traffic_sources),
    },
  });

  const create = useMutation({
    mutationFn: api.createCampaign,
    onSuccess: (campaign) => {
      queryClient.setQueryData(["campaign", campaign.keitaro_id], campaign);
      queryClient.invalidateQueries({ queryKey: ["campaigns"] });
      toast.success(`Campaign ${campaign.name} created`);
      navigate(`/campaigns/${campaign.keitaro_id}`);
    },
    onError: (error) => toast.error(error.message),
  });

  const onSubmit = form.handleSubmit((values) =>
    create.mutate({
      name: values.name,
      countries: parseCountries(values.geo),
      offer_id: values.offer.id,
      domain_id: Number(values.domainId),
      group_id: Number(values.groupId),
      traffic_source_id: Number(values.sourceId),
    }),
  );

  return (
    <form onSubmit={onSubmit} noValidate>
      <FieldGroup>
        <Controller
          name="name"
          control={form.control}
          render={({ field, fieldState }) => (
            <Field data-invalid={fieldState.invalid}>
              <FieldLabel htmlFor="name">Name</FieldLabel>
              <Input
                {...field}
                id="name"
                placeholder="test_ivanov_campaign1"
                aria-invalid={fieldState.invalid}
              />
              <FieldError errors={[fieldState.error]} />
            </Field>
          )}
        />

        <Controller
          name="geo"
          control={form.control}
          render={({ field, fieldState }) => {
            const countries = parseCountries(field.value);
            return (
              <Field data-invalid={fieldState.invalid}>
                <FieldLabel htmlFor="geo">Geo</FieldLabel>
                <Input
                  {...field}
                  id="geo"
                  placeholder="MX, AU, RO"
                  aria-invalid={fieldState.invalid}
                />
                {countries.length > 0 ? (
                  <div className="flex flex-wrap gap-1">
                    {countries.map((code) => (
                      <Badge key={code} variant={isCountryCode(code) ? "secondary" : "destructive"}>
                        {code}
                      </Badge>
                    ))}
                  </div>
                ) : (
                  <FieldDescription>
                    Two-letter country codes, separated by commas.
                  </FieldDescription>
                )}
                <FieldError errors={[fieldState.error]} />
              </Field>
            );
          }}
        />

        <Controller
          name="offer"
          control={form.control}
          render={({ field, fieldState }) => (
            <Field data-invalid={fieldState.invalid}>
              <FieldLabel htmlFor="offer">Offer</FieldLabel>
              <OfferPicker
                id="offer"
                value={field.value ?? null}
                onChange={field.onChange}
                invalid={fieldState.invalid}
              />
              <FieldError errors={[fieldState.error]} />
            </Field>
          )}
        />

        <div className="grid gap-4 sm:grid-cols-3">
          <OptionSelect
            control={form.control}
            name="domainId"
            label="Domain"
            items={options.domains}
          />
          <OptionSelect
            control={form.control}
            name="groupId"
            label="Group"
            items={options.groups}
          />
          <OptionSelect
            control={form.control}
            name="sourceId"
            label="Source"
            items={options.traffic_sources}
          />
        </div>

        <Button type="submit" disabled={create.isPending}>
          {create.isPending && <Spinner data-icon="inline-start" />}
          Create
        </Button>
      </FieldGroup>
    </form>
  );
}

function firstId(items: Option[]): string {
  return items.length > 0 ? String(items[0].id) : "";
}

interface OptionSelectProps {
  control: Control<FormValues>;
  name: "domainId" | "groupId" | "sourceId";
  label: string;
  items: Option[];
}

function OptionSelect({ control, name, label, items }: OptionSelectProps) {
  return (
    <Controller
      name={name}
      control={control}
      render={({ field, fieldState }) => (
        <Field data-invalid={fieldState.invalid}>
          <FieldLabel htmlFor={name}>{label}</FieldLabel>
          <Select name={field.name} value={field.value} onValueChange={field.onChange}>
            <SelectTrigger id={name} className="w-full" aria-invalid={fieldState.invalid}>
              <SelectValue placeholder="Choose" />
            </SelectTrigger>
            <SelectContent>
              <SelectGroup>
                {items.map((item) => (
                  <SelectItem key={item.id} value={String(item.id)}>
                    {item.name}
                  </SelectItem>
                ))}
              </SelectGroup>
            </SelectContent>
          </Select>
          <FieldError errors={[fieldState.error]} />
        </Field>
      )}
    />
  );
}
