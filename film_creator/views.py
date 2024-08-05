from django.shortcuts import render

# Create your views here.

from django.views.generic import TemplateView
from .models import Actor, Role, Film
import random
from django.http import JsonResponse
from openai import OpenAI
from django.core.serializers import serialize
import json
from django.conf import settings

class HomeView(TemplateView):
    template_name = 'home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Home Page'
        context['message'] = 'Welcome to the Home Page'
        return context


class CreateView(TemplateView):
    template_name = 'create.html'


def fetch_new_actors():
    # Get all unique actor IDs from roles where lead is 1
    actor_ids = list(Role.objects.filter(lead=1).values_list('actor', flat=True).distinct())
    actors = list(Actor.objects.filter(tmdb_id__in=actor_ids))
    selected_actors = random.sample(actors, 3) if len(actors) >= 3 else actors

    # Prepare the data to be sent as JSON
    actors_data = [{'name': actor.name, 'picture': actor.picture, 'tmdb_id': actor.tmdb_id} for actor in
                   selected_actors]
    return {'new_actors': actors_data, 'new_actors_data': selected_actors}


def generate_gpt_film_details(request):
    lead_actors = fetch_new_actors()

    lead_actor_info = lead_actors['new_actors_data']

    actor_ids = []
    actor_names = []
    for actor in lead_actors['new_actors']:
        actor_ids.append(actor['tmdb_id'])
        actor_names.append(actor['name'].upper())

    print(f'actor_ids: {actor_ids}, actor_names: {actor_names}')
    lead_actor_roles = Role.objects.filter(actor__in=actor_ids, actor_name__in=actor_names)

    actor_film_ids = []
    for role in list(lead_actor_roles):
        actor_film_ids.append(role.film.imdb_id)

    lead_actor_films = Film.objects.filter(imdb_id__in=actor_film_ids)

    # Convert the querysets to lists of dictionaries
    lead_actor_info_list = [{'name': actor.name, 'picture': actor.picture, 'tmdb_id': actor.tmdb_id} for actor in
                            lead_actor_info]
    lead_actor_roles_list = json.loads(serialize('json', lead_actor_roles))
    lead_actor_films_list = json.loads(serialize('json', lead_actor_films))

    # Convert the lists of dictionaries to JSON strings
    lead_actor_info_json = json.dumps(lead_actor_info_list, indent=4)
    lead_actor_roles_json = json.dumps(lead_actor_roles_list, indent=4)
    lead_actor_films_json = json.dumps(lead_actor_films_list, indent=4)

    # Define file paths where you want to save the JSON data
    lead_actor_info_file = 'film_creator/LeadActorInfo.json'
    lead_actor_roles_file = 'film_creator/LeadActorRoles.json'
    lead_actor_films_file = 'film_creator/LeadActorFilms.json'

    # Create 3 JSON files locally
    with open(lead_actor_info_file, 'w') as file:
        file.write(lead_actor_info_json)

    with open(lead_actor_roles_file, 'w') as file:
        file.write(lead_actor_roles_json)

    with open(lead_actor_films_file, 'w') as file:
        file.write(lead_actor_films_json)

    # Upload files to openai client
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    with open(lead_actor_info_file, 'rb') as file:
        response = client.files.create(
            file=file,
            purpose='assistants'
        )
    info_file_id = response.id

    with open(lead_actor_roles_file, 'rb') as file:
        response = client.files.create(
            file=file,
            purpose='assistants'
        )
    roles_file_id = response.id

    with open(lead_actor_films_file, 'rb') as file:
        response = client.files.create(
            file=file,
            purpose='assistants'
        )
    films_file_id = response.id

    # Query to find roles for the specific actor and actor_names
    with open('film_creator/chatgpt filmai prompt.txt', 'r') as file:
        prompt = file.read()

        assistant = client.beta.assistants.create(
            name="Film Magician",
            description="You are a film creator. You create detailed film ideas from reference data. This includes a "
                        "film title, plot, genre and reasoning as why how the idea has been formed.",
            model="gpt-4o-mini",
            tools=[{"type": "file_search"}]
        )

        thread = client.beta.threads.create()

        thread_message = client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=[
                {
                    "type": "text",
                    "text": prompt,
                }
            ],
            attachments=[
                {"file_id": info_file_id, "tools": [{"type": "file_search"}]},
                {"file_id": roles_file_id, "tools": [{"type": "file_search"}]},
                {"file_id": films_file_id, "tools": [{"type": "file_search"}]}
            ]
        )
        print(f'thread_message: {thread_message}')

        run = client.beta.threads.runs.create_and_poll(
            thread_id=thread.id,
            assistant_id=assistant.id,
        )

        if run.status == 'completed':
            messages = client.beta.threads.messages.list(
                thread_id=thread.id
            )
            print(messages)
        else:
            print(run.status)

        film_details = messages
        print(f'Film details: {film_details}')

    return JsonResponse({"lead_actor_info": lead_actor_info_list, "gpt_film_details": film_details})
