from django.core.exceptions import ValidationError
from django.db import models


class Airport(models.Model):
    name = models.CharField(max_length=150)
    iata_code = models.CharField(max_length=3, unique=True)
    icao_code = models.CharField(max_length=4, unique=True)

    city = models.CharField(max_length=100, blank=True, default="")
    country = models.CharField(max_length=100, blank=True, default="")

    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Airport"
        verbose_name_plural = "Airports"
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["iata_code"]),
            models.Index(fields=["icao_code"]),
            models.Index(fields=["city"]),
            models.Index(fields=["country"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.iata_code})"

    def clean(self):
        errors = {}

        if self.iata_code:
            self.iata_code = self.iata_code.upper().strip()
            if len(self.iata_code) != 3:
                errors["iata_code"] = "IATA code must contain exactly 3 characters."

        if self.icao_code:
            self.icao_code = self.icao_code.upper().strip()
            if len(self.icao_code) != 4:
                errors["icao_code"] = "ICAO code must contain exactly 4 characters."

        if self.latitude is not None and not (-90 <= float(self.latitude) <= 90):
            errors["latitude"] = "Latitude must be between -90 and 90."

        if self.longitude is not None and not (-180 <= float(self.longitude) <= 180):
            errors["longitude"] = "Longitude must be between -180 and 180."

        if self.name:
            self.name = self.name.strip()

        self.city = self.city.strip()
        self.country = self.country.strip()

        if errors:
            raise ValidationError(errors)