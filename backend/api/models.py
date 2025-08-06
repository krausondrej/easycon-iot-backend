from django.db import models

# Create your models here.
class Device(models.Model):
    name = models.CharField(max_length=100)
    serial_number = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.serial_number})"