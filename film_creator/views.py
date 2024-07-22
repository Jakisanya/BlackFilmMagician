from django.shortcuts import render

# Create your views here.

from django.views.generic import TemplateView
from .models import Actor, Role, Film
import random
from django.http import JsonResponse
import openai

openai.api_key = 'your_openai_api_key'


class HomeView(TemplateView):
    template_name = 'home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Home Page'
        context['message'] = 'Welcome to the Home Page'
        return context

class CreateView(TemplateView):
    template_name = 'create.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create Page'
        context['message'] = 'Get creating!'

        # Get all unique actor IDs from roles where lead is 1
        actor_ids = list(Role.objects.filter(lead=1).values_list('actor', flat=True).distinct())
        actors = list(Actor.objects.filter(tmdb_id__in=actor_ids))
        print(f'len(actors): {len(actors)}')
        selected_actors = random.sample(actors, 3) if len(actors) >= 3 else actors
        context['actors'] = selected_actors
        print(selected_actors[1])
        return context

def fetch_new_actors(request):
    # Get all unique actor IDs from roles where lead is 1
    actor_ids = list(Role.objects.filter(lead=1).values_list('actor', flat=True).distinct())
    actors = list(Actor.objects.filter(tmdb_id__in=actor_ids))
    selected_actors = random.sample(actors, 3) if len(actors) >= 3 else actors

    # Prepare the data to be sent as JSON
    actors_data = [{'name': actor.name, 'picture': actor.picture, 'tmdb_id': actor.tmdb_id} for actor in
                   selected_actors]
    print(actors_data)
    return JsonResponse({'new_actors': actors_data, 'new_actors_data': selected_actors})

def generate_gpt_film_details(request):
    new_actors = fetch_new_actors(request)

    actor_ids = []
    actor_names = []
    for new_actor in new_actors:
        actor_ids.append(new_actor['tmdb_id'])
        actor_names.append(new_actor['name'])

    new_actor_roles = Role.objects.filter(actor__in=actor_ids, actor_name__in=actor_names)

    Film.objects.filter(imdb_id__in=)
    reference_data = [{"actor_name": new_actor.actor_name, "movie_credits": []} for new_actor in new_actor_roles]

    plots_and_keywords = "\n".join(
        [f"Title: {title}\nPlot: {plot}\nKeywords: {keywords}" for title, plot, keywords in film_data]
    )

    # Query to find roles for the specific actor and actor_names

    prompt = (f"Create a film title and plot for a new movie starring the following lead actors {', '.join(actor_names)}. "
              f"Use the following data as reference:"
              f"1. Details about each actor: {actor_details}\n"
              f"2. The plots of all of the films that the actors have starred in: {plots}\n"
              f"3. Keywords that help categorise all of the films that the actors have starred in: {keywords}\n\n"
              f"Here's how I want you to use the reference data:"
              f"Factor in all information about each actor, specifically, their age and gender, when creating their "
              f"character. For all of the films that each actor has acted in, gain an understanding of the genre of film"
              f" they are most suited to. The plot should clearly outline a film that sits in a single genre but still "
              f"be suited to all of the actors to the highest degree. The film title should creatively convey what the "
              f"film is about.\n\n"
              f"In addition to the film title and plot, provide 5 detailed bullet points explaining how the film has "
              f"been created - making reference to the reference data used. The last bullet point should always explain "
              f"how the title was created.")

    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        max_tokens=300,
        n=1,
        stop=None,
        temperature=0.7,
    )

    return response.choices[0].text.strip()

    actor_names = ["Actor1", "Actor2", "Actor3"]
    film_data = extract_film_data(actor_names)
    film_details = generate_film_details(actor_names, film_data)

    print(film_details)