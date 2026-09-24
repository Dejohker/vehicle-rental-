"""Serve bundled catalogue illustrations as static assets, not public documents."""
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.storage import FileSystemStorage
from django.templatetags.static import static


class CatalogueMediaStorage(FileSystemStorage):
    def bundled_path(self, name):
        if not name or not str(name).startswith('vehicles/'):
            return None
        root = (settings.BASE_DIR / 'media' / 'vehicles').resolve()
        path = (root / str(name).removeprefix('vehicles/')).resolve()
        if path.is_relative_to(root) and path.is_file() and path.suffix.lower() in {'.png', '.jpg', '.jpeg', '.webp', '.gif'}:
            return path
        return None

    def exists(self, name):
        return super().exists(name) or self.bundled_path(name) is not None

    def url(self, name):
        if not settings.DEBUG and self.bundled_path(name):
            return static('fleet/' + str(name).removeprefix('vehicles/'))
        return super().url(name)

    def _save(self, name, content):
        if settings.ON_RENDER and not __import__('os').environ.get('DJANGO_MEDIA_ROOT'):
            raise ValidationError('Uploads require persistent storage. Configure DJANGO_MEDIA_ROOT on a mounted disk first.')
        return super()._save(name, content)
