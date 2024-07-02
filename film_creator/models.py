from django.db import models


# Create your models here.
class Actor(models.Model):
    DoesNotExist = None
    objects = models.Manager()
    tmdb_id = models.IntegerField(primary_key=True)
    imdb_id = models.CharField(max_length=15)
    name = models.CharField(max_length=100)
    gender = models.IntegerField()
    birthday = models.DateField(null=True, blank=True)
    movie_credits = models.CharField()
    picture = models.URLField()


class Film(models.Model):
    DoesNotExist = None
    objects = models.Manager()
    imdb_id = models.CharField(max_length=15, primary_key=True)
    title = models.CharField(max_length=150)
    release_date = models.DateField()
    genre = models.CharField()
    plot = models.TextField()
    plot_words = models.TextField()
    keyword_list = models.TextField()
    worldwide_gross = models.BigIntegerField(null=True, blank=True)


class Role(models.Model):
    objects = models.Manager()
    film = models.ForeignKey(Film, on_delete=models.CASCADE, related_name='actor_roles', null=True, blank=True)
    actor = models.ForeignKey(Actor, on_delete=models.CASCADE, related_name='roles', null=True, blank=True)
    film_title = models.CharField(max_length=150)
    actor_name = models.CharField(max_length=50)
    lead = models.IntegerField()
