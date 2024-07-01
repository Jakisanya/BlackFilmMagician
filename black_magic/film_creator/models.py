from django.db import models

# Create your models here.
class Actor(models.Model):
    objects = models.Manager()
    tmdb_id = models.IntegerField(max_length=15, primary_key=True)
    imdb_id = models.CharField(max_length=15)
    name = models.CharField(max_length=100)
    gender = models.IntegerField(max_length=1)
    birthday = models.DateTimeField()
    movie_credits = models.CharField()
    picture = models.URLField()

class Film(models.Model):
    objects = models.Manager()
    imdb_id = models.CharField(max_length=15, primary_key=True)
    title = models.CharField(max_length=150)
    release_date = models.DateTimeField()
    genre = models.CharField()
    plot = models.TextField()
    plot_words = models.TextField()
    keyword_list = models.TextField()
    worldwide_gross = models.IntegerField()

class Role(models.Model):
    objects = models.Manager()
    film_imdb_id = models.ForeignKey(Film, on_delete=models.CASCADE)
    actor_tmdb_id = models.CharField(max_length=15)
    film_title = models.CharField(max_length=150)
    actor_name = models.CharField(max_length=50)
    lead = models.IntegerField(max_length=1)

