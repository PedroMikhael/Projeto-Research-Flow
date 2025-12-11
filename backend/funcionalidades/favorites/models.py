from django.db import models
from django.contrib.auth.models import User

class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites')
    title = models.CharField(max_length=500)
    url = models.URLField(max_length=500, blank=True, null=True)
    authors = models.TextField(blank=True, null=True) # Storing as text (comma separated or JSON) simplification
    year = models.IntegerField(blank=True, null=True)
    abstract = models.TextField(blank=True, null=True)
    citation_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.user.username})"
