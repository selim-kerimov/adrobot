import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { ChevronsUpDownIcon } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Spinner } from "@/components/ui/spinner";
import { api, type Option } from "@/lib/api";

interface OfferPickerProps {
  value: Option | null;
  onChange: (offer: Option) => void;
  placeholder?: string;
  disabled?: boolean;
  loading?: boolean;
  invalid?: boolean;
  id?: string;
}

/** Offer search with autocomplete. The backend filters the Keitaro catalog. */
export function OfferPicker({
  value,
  onChange,
  placeholder = "Search offers…",
  disabled,
  loading,
  invalid,
  id,
}: OfferPickerProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const search = useDebounced(query, 250);

  const offers = useQuery({
    queryKey: ["offers", search],
    queryFn: () => api.offers(search),
    enabled: open,
    staleTime: 60_000,
    // Keep the old results on screen while the next query loads.
    placeholderData: keepPreviousData,
  });

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          id={id}
          variant="outline"
          role="combobox"
          aria-expanded={open}
          aria-invalid={invalid}
          disabled={disabled || loading}
          className="w-full justify-between font-normal"
        >
          <span className="truncate">{value ? value.name : placeholder}</span>
          {loading ? (
            <Spinner data-icon="inline-end" />
          ) : (
            <ChevronsUpDownIcon data-icon="inline-end" />
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-(--radix-popover-trigger-width) min-w-80 p-0" align="start">
        <Command shouldFilter={false}>
          <CommandInput placeholder="Name or ID" value={query} onValueChange={setQuery} />
          <CommandList>
            {offers.isFetching && !offers.data ? (
              <div className="flex justify-center p-4">
                <Spinner />
              </div>
            ) : (
              <CommandEmpty>
                {offers.isError ? offers.error.message : "No offers found"}
              </CommandEmpty>
            )}
            <CommandGroup>
              {offers.data?.map((offer) => (
                <CommandItem
                  key={offer.id}
                  value={String(offer.id)}
                  data-checked={offer.id === value?.id}
                  onSelect={() => {
                    onChange(offer);
                    setOpen(false);
                    setQuery("");
                  }}
                >
                  <span className="truncate">{offer.name}</span>
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}

function useDebounced<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(timer);
  }, [value, delayMs]);
  return debounced;
}
