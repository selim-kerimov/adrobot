import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Field, FieldError, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";

const schema = z.object({ name: z.string().trim().min(1, "Enter a name").max(255) });

interface RenameDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  name: string;
  pending: boolean;
  onRename: (name: string) => void;
}

export function RenameDialog({ open, onOpenChange, name, pending, onRename }: RenameDialogProps) {
  const form = useForm({ resolver: zodResolver(schema), values: { name } });
  const error = form.formState.errors.name;

  return (
    <Dialog open={open} onOpenChange={(next) => pending || onOpenChange(next)}>
      <DialogContent>
        <form onSubmit={form.handleSubmit((data) => onRename(data.name))}>
          <DialogHeader>
            <DialogTitle>Rename campaign</DialogTitle>
          </DialogHeader>
          <FieldGroup className="py-4">
            <Field data-invalid={!!error}>
              <FieldLabel htmlFor="campaign-name">Name</FieldLabel>
              <Input id="campaign-name" aria-invalid={!!error} {...form.register("name")} />
              <FieldError errors={[error]} />
            </Field>
          </FieldGroup>
          <DialogFooter>
            <Button type="submit" disabled={pending}>
              {pending && <Spinner data-icon="inline-start" />}
              Save
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
