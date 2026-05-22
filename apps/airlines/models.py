from django.core.exceptions import ValidationError
from django.db import models


class Airline(models.Model):
    name = models.CharField(max_length=150, unique=True)
    iata_code = models.CharField(max_length=2, unique=True)
    icao_code = models.CharField(max_length=3, unique=True)
    country = models.CharField(max_length=100)

    country_code = models.CharField(
        max_length=2,
        blank=True,
        null=True,
        verbose_name="Country code",
        help_text="ISO 3166-1 alpha-2 country code, for example: FR, DE, US, TR."
    )

    logo = models.ImageField(
        upload_to="airline_logos/",
        blank=True,
        null=True,
        verbose_name="Airline logo"
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Airline"
        verbose_name_plural = "Airlines"
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["iata_code"]),
            models.Index(fields=["icao_code"]),
            models.Index(fields=["country"]),
            models.Index(fields=["country_code"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.iata_code})"

    def clean(self):
        errors = {}

        if self.iata_code:
            self.iata_code = self.iata_code.upper().strip()
            if len(self.iata_code) != 2:
                errors["iata_code"] = "IATA code must contain exactly 2 characters."

        if self.icao_code:
            self.icao_code = self.icao_code.upper().strip()
            if len(self.icao_code) != 3:
                errors["icao_code"] = "ICAO code must contain exactly 3 characters."

        if self.country_code:
            self.country_code = self.country_code.upper().strip()
            if len(self.country_code) != 2:
                errors["country_code"] = "Country code must contain exactly 2 characters."

        if self.name:
            self.name = self.name.strip()

        if self.country:
            self.country = self.country.strip()

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def logo_initials(self):
        if self.iata_code:
            return self.iata_code.upper()

        if self.icao_code:
            return self.icao_code[:2].upper()

        if self.name:
            parts = self.name.split()
            initials = "".join(part[0] for part in parts[:2])
            return initials.upper()

        return "AL"

    @property
    def display_country(self):
        if self.country and self.country.strip().lower() != "unknown":
            return self.country
        return "—"

    @property
    def has_country_flag(self):
        return bool(self.country_code)

    @property
    def flag_url(self):
        if not self.country_code:
            return ""

        return f"https://flagcdn.com/w40/{self.country_code.lower()}.png"