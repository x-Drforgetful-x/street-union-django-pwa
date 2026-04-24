from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = "Force create/reset admin user"

    def handle(self, *args, **kwargs):
        User = get_user_model()

        username = "admin"
        email = "c.m.lawrence00@gmail.com"
        password = "Admin@12345"

        # DELETE existing admin if exists
        User.objects.filter(username=username).delete()

        # CREATE fresh admin
        User.objects.create_superuser(
            username=username,
            email=email,
            password=password
        )

        self.stdout.write(self.style.SUCCESS("Admin user RESET successfully."))
