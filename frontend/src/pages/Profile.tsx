
import { useState } from "react";
import { PageHeader } from "@/components/app/AppShell";
import { Badge2, Card, Field } from "@/components/app/shared";
import { ROLE_LABEL, useApp } from "@/lib/app-store";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { UserCircle } from "lucide-react";

function ProfilePage() {
  const { user, updateProfile } = useApp();
  const [name, setName] = useState(user?.name ?? "");
  const [savingName, setSavingName] = useState(false);

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [savingPassword, setSavingPassword] = useState(false);

  return (
    <div>
      <PageHeader title="My Profile" subtitle="Your account details and access level" />

      <div className="grid gap-3 p-3 xl:grid-cols-2">
        <Card title="Account" subtitle="Details tied to your operator login">
          <div className="flex items-center gap-3 p-4">
            <span className="grid size-12 place-items-center rounded-full bg-primary/15 text-primary">
              <UserCircle className="size-7" />
            </span>
            <div>
              <p className="text-sm font-medium">{user?.name}</p>
              <p className="font-mono text-[0.65rem] text-muted-foreground">{user?.email}</p>
            </div>
          </div>
          <div className="border-t border-border">
            <Field label="Role">
              <Badge2 tone={user?.role === "admin" ? "primary" : "muted"}>
                {user ? ROLE_LABEL[user.role] : "—"}
              </Badge2>
            </Field>
            <Field label="Account status">
              <Badge2 tone="success">active</Badge2>
            </Field>
          </div>
        </Card>

        <Card title="Update name" subtitle="Shown across the console and in audit logs">
          <form
            className="space-y-3 p-4"
            onSubmit={async (e) => {
              e.preventDefault();
              if (!name.trim()) return;
              setSavingName(true);
              try {
                await updateProfile({ name: name.trim() });
                toast.success("Name updated");
              } catch (err: any) {
                toast.error("Could not update name", { description: err.message });
              } finally {
                setSavingName(false);
              }
            }}
          >
            <div className="space-y-1.5">
              <Label htmlFor="name">Full name</Label>
              <Input id="name" value={name} onChange={(e) => setName(e.target.value)} />
            </div>
            <Button type="submit" size="sm" disabled={savingName || !name.trim() || name.trim() === user?.name}>
              {savingName ? "Saving…" : "Save name"}
            </Button>
          </form>
        </Card>

        <Card title="Change password" subtitle="You'll need your current password to confirm" className="xl:col-span-2">
          <form
            className="grid gap-3 p-4 sm:grid-cols-3"
            onSubmit={async (e) => {
              e.preventDefault();
              if (newPassword.length < 6) {
                toast.error("New password must be at least 6 characters");
                return;
              }
              if (newPassword !== confirmPassword) {
                toast.error("New password and confirmation do not match");
                return;
              }
              setSavingPassword(true);
              try {
                await updateProfile({ current_password: currentPassword, new_password: newPassword });
                toast.success("Password updated");
                setCurrentPassword("");
                setNewPassword("");
                setConfirmPassword("");
              } catch (err: any) {
                toast.error("Could not update password", { description: err.message });
              } finally {
                setSavingPassword(false);
              }
            }}
          >
            <div className="space-y-1.5">
              <Label htmlFor="current-password">Current password</Label>
              <Input
                id="current-password"
                type="password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                autoComplete="current-password"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="new-password">New password</Label>
              <Input
                id="new-password"
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                autoComplete="new-password"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="confirm-password">Confirm new password</Label>
              <Input
                id="confirm-password"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                autoComplete="new-password"
              />
            </div>
            <div className="sm:col-span-3">
              <Button type="submit" size="sm" disabled={savingPassword || !currentPassword || !newPassword}>
                {savingPassword ? "Updating…" : "Update password"}
              </Button>
            </div>
          </form>
        </Card>
      </div>
    </div>
  );
}

export default ProfilePage;
