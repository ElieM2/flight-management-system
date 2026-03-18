from django.db import models


class Airport(models.Model):
    name = models.CharField(max_length=150)
    iata_code = models.CharField(max_length=3, unique=True)
    icao_code = models.CharField(max_length=4, unique=True)
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Airport'
        verbose_name_plural = 'Airports'

    def __str__(self):
        return f"{self.name} ({self.iata_code})"