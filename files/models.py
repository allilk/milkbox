from django.db import models
from django.core.validators import int_list_validator
from django.contrib.postgres.fields import JSONField, ArrayField
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    gdrive_auth = JSONField(default=dict,blank=True)
    def __str__(self):
        return self.user.username

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.userprofile.save()

class cachedFile(models.Model):
    name = models.CharField(max_length=256)
    file_id = models.CharField(max_length=64)
    parents = models.CharField(max_length=64)
    mimetype = models.CharField(max_length=48)
    file_size = models.CharField(max_length=8)
    byte_size = models.CharField(max_length=512, null=True)
    modified_date = models.DateField(null=True)
    modified_time = models.TimeField(null=True)
    users = ArrayField(models.IntegerField(), null=True)
    tags = ArrayField(models.CharField(max_length=1024), null=True)
    def __str__(self):
        return self.name

class cachedSharedDrive(models.Model):
    name = models.CharField(max_length=256)
    drive_id = models.CharField(max_length=64)
    users = ArrayField(models.IntegerField(), null=True)
    def __str__(self):
        return self.name