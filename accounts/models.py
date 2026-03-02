from django.db import models
class EmergencyContact(models.Model):
    phone_number = models.CharField(max_length=15)
    def __str__(self):
        return self.phone_number