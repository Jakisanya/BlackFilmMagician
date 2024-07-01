# film_creator/management/commands/populate_data.py
from django.core.management.base import BaseCommand
from django.db import connection
from black_magic.film_creator.models import Actor, Film, Role


class Command(BaseCommand):
    help = 'Populate the database with initial data from existing tables'

    def handle(self, *args, **kwargs):
        with connection.cursor() as cursor:
            cursor.execute('SELECT "TMDb_ID" as "actor_tmdb_id", "IMDb_ID" as "actor_imdb_id", "Name" as "name", '
                           '"Gender" as "gender", "Birthday" as "birthday", "Movie_Credits" as "movie_credits", "Image" '
                           'as "actor_picture" FROM public.actor_model;')
            actors_data = cursor.fetchall()

            cursor.execute('SELECT "Film_IMDb_ID" as "film_imdb_id", "Title" as "title", "Release_Date" as "release_date", '
                           '"Genre" as "genre", "Plot" as "plot", "Plot_Words" as "plot_words", "Keyword_List" as '
                           '"keyword_list", "Worldwide_Gross" as "worldwide_gross" FROM public.film_model;')
            films_data = cursor.fetchall()

            cursor.execute('SELECT "Actor_TMDb_ID" as "actor_tmdb_id",  "Film_IMDb_ID" as "film_imdb_id", "Title" as '
                           '"title", "Actor_Name" as "name", "Lead_Actor" as "lead_actor" FROM public.role_model;')
            roles_data = cursor.fetchall()

        # Create Actor instances
        for actor_tmdb_id, actor_imdb_id, name, gender, birthday, movie_credits, picture in actors_data:
            Actor.objects.get_or_create(
                actor_tmdb_id=actor_tmdb_id,
                defaults={'actor_imdb_id': actor_imdb_id,
                          'name': name,
                          'gender': gender,
                          'birthday': birthday,
                          'movie_credits': movie_credits,
                          'picture': picture}
            )

        # Create Film instances
        for imdb_id, title, release_date, genre, plot, plot_words, keyword_list, worldwide_gross in films_data:
            Film.objects.get_or_create(
                film_imdb_id=imdb_id,
                defaults={'imdb_id': imdb_id, 'title': title, 'release_date': release_date, 'genre': genre, 'plot': plot,
                          'plot_words': plot_words, 'keyword_list': keyword_list, 'worldwide_gross': worldwide_gross}
            )

        # Create Role instances
        for actor_tmdb_id, film_imdb_id, title, actor_name, lead_actor in roles_data:
            actor = Actor.objects.get(actor_tmdb_id=actor_tmdb_id)
            film = Film.objects.get(film_imdb_id=film_imdb_id)
            Role.objects.get_or_create(
                actor_tmdb_id=actor_tmdb_id,
                defaults={'actor_tmdb_id': actor_tmdb_id, 'film_imdb_id': film_imdb_id, 'title': title,
                          'actor_name': actor_name, 'lead_actor': lead_actor}
            )

        self.stdout.write(self.style.SUCCESS('Successfully populated the database with initial data'))
