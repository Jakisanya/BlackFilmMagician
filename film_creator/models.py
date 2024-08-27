import uuid

from django.db import models
from django.contrib.auth.models import User


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


class FilmCreation(models.Model):
    id = models.IntegerField(primary_key=True)
    creator_id = models.ForeignKey(User, on_delete=models.CASCADE)
    film_card_id = models.IntegerField(null=False, blank=False)
    title = models.CharField(max_length=150, null=False, blank=False)
    genre = models.CharField(max_length=50, null=False, blank=False)
    lead_actor_1 = models.ForeignKey(Actor, null=True, blank=True, on_delete=models.SET_NULL,
                                     related_name='lead_actor_1')
    lead_actor_2 = models.ForeignKey(Actor, null=True, blank=True, on_delete=models.SET_NULL,
                                     related_name='lead_actor_2')
    lead_actor_3 = models.ForeignKey(Actor, null=True, blank=True, on_delete=models.SET_NULL,
                                     related_name='lead_actor_3')
    plot = models.TextField(null=False)
    model_reasoning = models.TextField(null=False)
    last_edited = models.DateTimeField()
    date_created = models.DateTimeField(auto_now_add=True)
    version_control_id = models.IntegerField(null=False, blank=False)
    no_of_suggestions_received = models.IntegerField()
    no_of_suggestions_accepted = models.IntegerField()


class Badge(models.Model):
    id = models.IntegerField(primary_key=True)
    data = models.TextField()


class FilmCreationCard(models.Model):
    id = models.IntegerField(primary_key=True)
    film_creation_id = models.ForeignKey(FilmCreation, on_delete=models.CASCADE)
    badge_id = models.ForeignKey(Badge, on_delete=models.DO_NOTHING)
    free_text = models.CharField(max_length=200)


class FilmCreationSuggestion(models.Model):
    id = models.IntegerField(primary_key=True)
    suggestor_user_id = models.ForeignKey(User, on_delete=models.CASCADE)
    film_creation_id = models.ForeignKey(FilmCreation, on_delete=models.CASCADE)
    film_creation_card_id = models.ForeignKey(FilmCreationCard, on_delete=models.DO_NOTHING)
    date_submitted = models.DateTimeField(auto_now_add=True)
    accepted = models.BooleanField(default=False)
    accepted_date = models.DateTimeField()
    rejected_date = models.DateTimeField()


class Suggestion(models.Model):
    id = models.IntegerField(primary_key=True)
    film_creation_id = models.ForeignKey(FilmCreation, on_delete=models.CASCADE)
    film_creation_suggestion_id = models.ForeignKey(FilmCreationSuggestion, on_delete=models.CASCADE)
    suggestor_user_id = models.ForeignKey(User, on_delete=models.CASCADE)
    is_film = models.BooleanField(default=False)
    is_title = models.BooleanField(default=False)
    is_genre = models.BooleanField(default=False)
    is_plot = models.BooleanField(default=False)
    is_actor = models.BooleanField(default=False)
    is_model_reasoning = models.BooleanField(default=False)
    title_suggestion = models.CharField(max_length=150)
    genre_suggestion = models.CharField(max_length=50)
    plot_suggestion = models.TextField()
    lead_actor_1_removal = models.BooleanField(default=False)
    lead_actor_2_removal = models.BooleanField(default=False)
    lead_actor_3_removal = models.BooleanField(default=False)
    lead_actor_1_suggestion = models.ForeignKey(Actor, null=True, blank=True, on_delete=models.SET_NULL,
                                                related_name='lead_actor_1_suggestions')
    lead_actor_2_suggestion = models.ForeignKey(Actor, null=True, blank=True, on_delete=models.SET_NULL,
                                                related_name='lead_actor_2_suggestions')
    lead_actor_3_suggestion = models.ForeignKey(Actor, null=True, blank=True, on_delete=models.SET_NULL,
                                                related_name='lead_actor_3_suggestions')
    lead_actor_1_suggestion_reason = models.TextField(max_length=100, null=True, blank=True)
    lead_actor_2_suggestion_reason = models.TextField(max_length=100, null=True, blank=True)
    lead_actor_3_suggestion_reason = models.TextField(max_length=100, null=True, blank=True)


class SuggestionCard(models.Model):
    id = models.IntegerField(primary_key=True)
    suggestion_id = models.OneToOneField(Suggestion, on_delete=models.CASCADE)
    type = models.CharField(max_length=20)


class Comments(models.Model):
    id = models.IntegerField(primary_key=True)
    content = models.TextField(null=False, blank=False)
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)
    film_creation_id = models.OneToOneField(FilmCreation, on_delete=models.CASCADE)
    parent_id = models.ForeignKey('self', null=True, blank=True, related_name='replies', on_delete=models.CASCADE)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()


class LiveDocument(models.Model):
    id = models.IntegerField(primary_key=True)
    title = models.CharField(max_length=255)
    content = models.TextField()
    current_version = models.OneToOneField('DocumentVersion', on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f'{self.title} (Current Version)'


class DocumentVersion(models.Model):
    live_document = models.ForeignKey(LiveDocument, on_delete=models.CASCADE, related_name='versions')
    version = models.PositiveIntegerField()
    title = models.CharField(max_length=100)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, related_name='created_document_versions', on_delete=models.SET_NULL, null=True)
    updated_by = models.ForeignKey(User, related_name='updated_document_versions', on_delete=models.SET_NULL, null=True)

    def save(self, *args, **kwargs):
        if not self.id:
            latest_version = DocumentVersion.objects.filter(live_document=self.live_document).order_by('version').last()
            self.version = (latest_version.version + 1) if latest_version else 1
        super().save(*args, **kwargs)
        self.live_document.current_version = self
        self.live_document.save()

    def __str__(self):
        return f'{self.live_document.title} (Version {self.version})'


class UserContributionStats(models.Model):
    id = models.IntegerField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='contribution_stats')
    no_of_film_creations = models.PositiveIntegerField()
    no_of_film_suggestions = models.PositiveIntegerField()
    no_of_suggestions_accepted = models.PositiveIntegerField()
    no_of_suggestions_rejected = models.PositiveIntegerField()

