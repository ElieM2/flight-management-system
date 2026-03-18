from django.db import models


class Aircraft(models.Model):
    AIRCRAFT_STATUS_CHOICES = [
        ('active', 'Active'),
        ('maintenance', 'Maintenance'),
        ('inactive', 'Inactive'),
    ]

    airline = models.ForeignKey(
        'airlines.Airline',
        on_delete=models.CASCADE,
        related_name='aircraft'
    )
    model = models.CharField(max_length=100)
    registration_number = models.CharField(max_length=50, unique=True)
    aircraft_type = models.CharField(max_length=50)
    capacity = models.PositiveIntegerField()
    status = models.CharField(
        max_length=20,
        choices=AIRCRAFT_STATUS_CHOICES,
        default='active'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['registration_number']
        verbose_name = 'Aircraft'
        verbose_name_plural = 'Aircraft'

    def __str__(self):
        return f"{self.registration_number} - {self.model}"