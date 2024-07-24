from django.shortcuts import render

# Create your views here.

from django.views.generic import TemplateView
from .models import Actor, Role, Film
import random
from django.http import JsonResponse
import openai
from django.core.serializers import serialize
import json

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
    lead_actors = fetch_new_actors(request)

    lead_actor_info = lead_actors['new_actors_data']

    actor_ids = []
    actor_names = []
    for actor in lead_actors:
        actor_ids.append(actor['new_actors']['tmdb_id'])
        actor_names.append(actor['new_actors']['name'])

    lead_actor_roles = Role.objects.filter(actor__in=actor_ids, actor_name__in=actor_names)

    actor_film_ids = []
    for role in lead_actor_roles:
        actor_film_ids.append(role.film)

    lead_actor_films = Film.objects.filter(imdb_id__in=actor_film_ids)

    # Convert the querysets to lists of dictionaries
    lead_actor_info_list = json.loads(serialize('json', lead_actor_info))
    lead_actor_roles_list = json.loads(serialize('json', lead_actor_roles))
    lead_actor_films_list = json.loads(serialize('json', lead_actor_films))

    # Convert the lists of dictionaries to JSON strings
    lead_actor_info_json = json.dumps(lead_actor_info_list, indent=4)
    lead_actor_roles_json = json.dumps(lead_actor_roles_list, indent=4)
    lead_actor_films_json = json.dumps(lead_actor_films_list, indent=4)

    # Query to find roles for the specific actor and actor_names
    prompt = (f"Create a film title and plot for a new movie starring the following lead actors {', '.join(actor_names)}. "
              f"Use the following data as reference:"
              f"1. Lead Actor Info: {lead_actor_info_json}\n"
              f"2. Lead Actor Roles: {lead_actor_roles_json}\n"
              f"3. Lead Actor Films: {lead_actor_films_json}\n\n" 
              
              f"Here's how I want you to use the reference data:"
              f"Cross reference the data presented in 'Lead Actor Info', 'Lead Actor Roles', and 'Lead Actor Films' to "
              f"help categorise and gain an understanding of each actor and to help create a synergous and cohesive "
              f"new film idea.\n"
              f"1. Use 'Lead Actor Info' to get information about each actor. Within 'Lead Actor Info', factor in "
              f"their age from 'birthday' and their 'gender', when creating their character and role in the new film.\n"
              f"2. Use 'Lead Actor Roles' to understand the roles each actor has played. Within 'Lead Actor Roles', "
              f"find the lead actor in 'actor', the 'film', and if they were 'lead' to decide whether to weigh the "
              f"data for that film more heavily if they were lead than if they were not when building their character "
              f"and role in the new film.\n"
              f"3. Use 'Lead Actor Films' to see the films each actor has been in. Within 'Lead Actor Films', use "
              f"'genre', 'plot', 'plot_words', 'keyword_list' to gain an understanding of the genre of film they are "
              f"most suited to. Use the information to find a single genre that is most suited to all of the lead "
              f"actors in the new film. The new plot should clearly outline a film that sits in this single genre and "
              f"is suited to all of the actors to the highest degree. Also use the information to help create the new"
              f"film title and plot. The film title should creatively convey what the film is about. The plot should be"
              f"clear, descriptive, and less than 500 words. It should specifically mention each lead actor and their "
              f"character and role in the film. Use the style of writing of the plots of highest grossing films to "
              f"gain an understanding of how to write the new plot. The gross figure is referenced in "
              f"'worldwide_gross'. \n"
              f"4. In addition to the film title and plot, provide 5 detailed bullet points explaining how the film "
              f"has been created - making reference to the reference data used. The last bullet point should always "
              f"explain how the title was created, i.e., the inspiration behind the title.")

    print(f"Prompt: {prompt}\n\n")

    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        max_tokens=300,
        n=1,
        stop=None,
        temperature=0.7,
    )

    film_details = response.choices[0].text.strip()

    print(f'Film details: {film_details}')

    return JsonResponse({"lead_actor_info": lead_actor_info, "lead_actor_roles": lead_actor_roles,
                         "lead_actor_films": lead_actor_films, "gpt_film_details": film_details})
