from django.core.exceptions import ValidationError
from django.db import models


class Aircraft(models.Model):
    AIRCRAFT_STATUS_CHOICES = [
        ("active", "Active"),
        ("maintenance", "Maintenance"),
        ("inactive", "Inactive"),
    ]

    airline = models.ForeignKey(
        "airlines.Airline",
        on_delete=models.CASCADE,
        related_name="aircraft",
    )
    model = models.CharField(max_length=100)
    registration_number = models.CharField(max_length=50, unique=True)
    aircraft_type = models.CharField(max_length=50)
    capacity = models.PositiveIntegerField()
    status = models.CharField(
        max_length=20,
        choices=AIRCRAFT_STATUS_CHOICES,
        default="active",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["registration_number"]
        verbose_name = "Aircraft"
        verbose_name_plural = "Aircraft"
        indexes = [
            models.Index(fields=["registration_number"]),
            models.Index(fields=["model"]),
            models.Index(fields=["aircraft_type"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.registration_number} - {self.model}"

    def clean(self):
        errors = {}

        if self.registration_number:
            self.registration_number = self.registration_number.upper().strip()

        if self.model:
            self.model = self.model.strip()

        if self.aircraft_type:
            self.aircraft_type = self.aircraft_type.strip()

        if self.capacity is not None and self.capacity <= 0:
            errors["capacity"] = "Capacity must be greater than zero."

        if errors:
            raise ValidationError(errors)