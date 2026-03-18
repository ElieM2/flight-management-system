from django.db import models


class Airline(models.Model):
    name = models.CharField(max_length=150, unique=True)
    iata_code = models.CharField(max_length=2, unique=True)
    icao_code = models.CharField(max_length=3, unique=True)
    country = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Airline'
        verbose_name_plural = 'Airlines'

    def __str__(self):
        return f"{self.name} ({self.iata_code})"