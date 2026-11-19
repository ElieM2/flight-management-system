import os

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.demo import demo_readonly_group_name


class Command(BaseCommand):
    help = "Create or update the read-only demo account from DEMO_USERNAME and DEMO_PASSWORD."

    def handle(self, *args, **options):
        username = os.getenv("DEMO_USERNAME", "").strip()
        password = os.getenv("DEMO_PASSWORD", "").strip()

        if not username or not password:
            self.stdout.write(
                self.style.WARNING(
                    "DEMO_USERNAME or DEMO_PASSWORD is not set; skipping demo user."
                )
            )
            return

        if username.lower() in {"admin", "root", "superuser"}:
            raise CommandError("DEMO_USERNAME cannot be a privileged account name.")

        User = get_user_model()
        user, created = User.objects.get_or_create(
            username=username,
            defaults={"email": f"{username}@example.com"},
        )
        user.set_password(password)
        user.is_staff = False
        user.is_superuser = False
        user.is_active = True
        if hasattr(user, "is_staff"):
            user.is_staff = False
        user.save()

        group, _ = Group.objects.get_or_create(name=demo_readonly_group_name())
        user.groups.add(group)

        action = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{action} read-only demo user '{username}'."))
