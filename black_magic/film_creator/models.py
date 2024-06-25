from django.db import models


# Create your models here.
class Actor(models.Model):
    actor_tmdb_id = models.IntegerField(max_length=15, unique=True)
    actor_imdb_id = models.CharField(max_length=15, primary_key=True)
    name = models.CharField(max_length=100)
    gender = models.IntegerField(max_length=1)
    birthday = models.DateTimeField()
    movie_credits = models.CharField()
    picture = models.URLField()  # Assuming pictures are stored as URLs

class Film(models.Model):
    film_imdb_id = models.CharField(max_length=15, primary_key=True)
    title = models.CharField(max_length=100)
    release_date = models.DateTimeField()
    genre = models.CharField()
    plot = models.TextField()
    plot_words = models.TextField()
    keyword_list = models.TextField()
    worldwide_gross = models.IntegerField()

class Role(models.Model):
    film_imdb_id = models.CharField(max_length=15, primary_key=True)
    actor_tmdb_id = models.CharField(max_length=15)
    actor_name = models.CharField(max_length=50)
    lead = models.IntegerField(max_length=1)
