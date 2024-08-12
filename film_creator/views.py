from django.shortcuts import render

from django.views.generic import TemplateView
from .models import Actor, Role, Film
import random
from django.http import JsonResponse
from openai import OpenAI
from django.core.serializers import serialize
from django.http import JsonResponse, HttpResponseBadRequest
import json
from django.conf import settings
import re
import os
import difflib


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

    # Determine how many actors to return: 1, 2, or 3
    max_actors_to_select = 3
    num_actors_to_select = random.randint(1, max_actors_to_select)

    # Randomly select the actors
    selected_actors = random.sample(actors, num_actors_to_select)

    # Prepare the data to be sent as JSON
    actors_data = [{'name': actor.name, 'picture': actor.picture, 'tmdb_id': actor.tmdb_id} for actor in
                   selected_actors]
    return {'new_actors': actors_data, 'new_actors_data': selected_actors}


def parse_film_details(details_string):
    film_details_list = details_string.split("\n")
    print(f'Film Details List: {film_details_list}\n\n')

    title = film_details_list[1].strip()
    genre = film_details_list[4].strip()
    plot_end_index = next((i for i, s in enumerate(film_details_list) if "Reason" in s), None)
    plot = "\n".join(film_details_list[7:plot_end_index])
    reasoning = "\n".join(film_details_list[plot_end_index + 1:])

    # Remove sources
    source_pattern = r'【\d+:\d+†source】'
    plot = re.sub(source_pattern, '', plot)
    reasoning = re.sub(source_pattern, '', reasoning)

    # Remove asterisks
    if '*' in reasoning:
        reasoning = re.sub(r'\*', '', reasoning)

    # Create the dictionary
    film_data_dict = {
        "title": title,
        "genre": genre,
        "plot": plot,
        "reasoning": reasoning
    }

    print(f'Film Details Dictionary: {film_data_dict}\n\n')

    json_data_str = json.dumps(film_data_dict, indent=4)

    return json_data_str, film_data_dict


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
    client = OpenAI(api_key=os.getenv('BMFILMS_API_KEY'))

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
            tools=[{"type": "file_search"}],
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
        # print(f'thread_message: {thread_message}\n\n\n\n')

        run = client.beta.threads.runs.create_and_poll(
            thread_id=thread.id,
            assistant_id=assistant.id
        )

        if run.status == 'completed':
            messages = client.beta.threads.messages.list(
                thread_id=thread.id
            )
        else:
            print(run.status)

        film_details = messages.data[0].content[0].text.value
        print(f'Film details: {film_details}\n\n')

        parsed_film_details_json_str, parsed_film_details_dict = parse_film_details(film_details)

        if len(actor_names) == 3:
            parsed_film_details_file = (f'film_creator/api_response_archive/{actor_names[0]}_{actor_names[1]}_'
                                        f'{actor_names[2]}.json')
        if len(actor_names) == 2:
            parsed_film_details_file = (f'film_creator/api_response_archive/{actor_names[0]}_{actor_names[1]}.json')
        if len(actor_names) == 1:
            parsed_film_details_file = (f'film_creator/api_response_archive/{actor_names[0]}.json')

        with open(parsed_film_details_file, 'w') as details_file:
            details_file.write(parsed_film_details_json_str)
    
    return JsonResponse({"lead_actor_info": lead_actor_info_list, "gpt_film_details": parsed_film_details_dict})


def highlight_plot_differences_for_quill(original, edited):
    # Create a SequenceMatcher object
    matcher = difflib.SequenceMatcher(None, original, edited)

    result_text = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'replace':
            # Highlight differences from text2 (this is where text1 and text2 differ)
            result_text.append(f'<span style="color: red;">{edited[j1:j2]}</span>')
        elif tag == 'delete':
            # Highlight deletions (parts of text1 that are missing in text2)
            result_text.append(f'<span style="color: red;">{original[i1:i2]}</span>')
        elif tag == 'insert':
            # Highlight insertions (parts of text2 that are new)
            result_text.append(f'<span style="color: #2cd6ae;">{edited[j1:j2]}</span>')
        elif tag == 'equal':
            # Keep the matching parts as is
            result_text.append(edited[j1:j2])

    return ''.join(result_text)


def update_text(request):
    if request.method == 'POST':
        try:
            # Load JSON data from the request body
            data = json.loads(request.body)
            original_text = data.get('original_text')
            new_text = data.get('new_text')

            # Check if both texts are provided
            if original_text is None or new_text is None:
                return HttpResponseBadRequest("Missing original_text or new_text")

            # Generate the highlighted HTML
            highlighted_html = highlight_plot_differences_for_quill(original_text, new_text)

            return JsonResponse({'highlighted_html': highlighted_html})

        except json.JSONDecodeError:
            return HttpResponseBadRequest("Invalid JSON data")
        except Exception as e:
            # Log the exception for debugging
            print(f"An error occurred: {e}")
            return HttpResponseBadRequest("An error occurred")
    else:
        return HttpResponseBadRequest("Invalid request method")
