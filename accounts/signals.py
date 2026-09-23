from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import CustomerProfile


@receiver(post_save, sender=User)
def ensure_customer_profile(sender, instance, created, **kwargs):
    if created and not instance.is_staff:
        CustomerProfile.objects.get_or_create(user=instance)
