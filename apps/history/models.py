from django.db import models
from django.contrib.auth.models import User
from apps.flights.models import Flight

class UserHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='flight_history')
    flight = models.ForeignKey(Flight, on_delete=models.CASCADE)
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-viewed_at']
        verbose_name = 'Historique'
        verbose_name_plural = 'Historiques'

    def __str__(self):
        return f"{self.user.username} - {self.flight.flight_number} - {self.viewed_at.strftime('%Y-%m-%d %H:%M')}"