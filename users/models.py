import random
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings

def random_color():
    return random.choice(settings.COLORS)

class User(AbstractUser):
    email = models.EmailField(unique=True)
    color = models.CharField(max_length=20, default=random_color)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.username
