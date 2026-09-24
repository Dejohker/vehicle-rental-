"""Attach generated project assets without replacing uploaded fleet photos."""
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from PIL import Image

from vehicles.models import Vehicle


class Command(BaseCommand):
    help = 'Validate and attach generated PNGs to matching demo cars with no image.'

    @transaction.atomic
    def handle(self, *args, **options):
        attached = 0
        missing = 0
        for car in Vehicle.objects.filter(registration_number__startswith='DEMO-'):
            if car.image:
                continue
            relative = Path('vehicles/ai-showcase') / f'{car.registration_number.lower()}.png'
            path = Path(settings.MEDIA_ROOT) / relative
            if not path.is_file():
                path = settings.BASE_DIR / 'media' / relative
            if not path.is_file():
                missing += 1
                continue
            with Image.open(path) as asset:
                asset.verify()
            car.image = relative.as_posix()
            car.save(update_fields=['image'])
            attached += 1
        self.stdout.write(self.style.SUCCESS(f'Attached {attached} images; {missing} demo cars still need images. Existing images preserved.'))
