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


def identify_plot_differences_view(request):
    if request.method == 'POST':
        # Parse the incoming JSON data
        data = json.loads(request.body)
        original_plot = data.get('original_plot', '')
        print(f'Original Plot: {original_plot}\n\n')
        edited_plot = data.get('edited_plot', '')
        print(f'Edited Plot: {edited_plot}\n\n')
        original_genre = data.get('original_genre', '')
        print(f'Original Genre: {original_genre}\n\n')

        # Call the existing identify_plot_differences function
        result = JsonResponse(identify_plot_differences(original_plot, original_genre, edited_plot), safe=False)
        # Return the result back to the frontend as JSON
        return result
    else:
        return JsonResponse({"error": "Invalid request method"}, status=400)


def identify_plot_differences(original_plot, original_genre, edited_plot):
    prompt_text = f'''
    Here is the reference data you will need to complete the task:
    - "original_plot": {original_plot}
    - "original_genre": {original_genre}
    - "edited_plot": {edited_plot}

    The task is as follows:

    1. **Correct the "edited_plot":**
       - Review the "edited_plot" for any punctuation, grammar, or spelling errors.
       - Make the necessary corrections and use this corrected version as the new "edited_plot".

    2. **Highlight the differences between the "original_plot" and the "edited_plot":**
       - Compare the corrected "edited_plot" to the "original_plot" and identify the sentences that differ.
       - Create a new plot called "highlighted_plot" with the differences highlighted in green (#2cd6ae).

    3. **Format the "highlighted_plot":**
       - Return the "highlighted_plot" in HTML format with the correct color codes.
       - Ensure the plot is formatted with paragraphs using <p> elements.

    4. **Explain the differences:**
       - Provide a brief explanation of how the new plot differs from the original, focusing on changes in meaning.

    5. **Determine the genre:**
       - If the "highlighted_plot" no longer matches the genre of the "original_plot," provide the new genre.
       - If the "highlighted_plot" still matches the genre of the "original_plot," return the original genre.

    6. **Output:**
       - Return the information in JSON format with the following keys: 
         - "highlighted_plot"
         - "explanation_of_difference"
         - "genre"
    '''

    client = OpenAI(api_key=os.getenv('BMFILMS_API_KEY'))

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": prompt_text}
        ],
        response_format={"type": "json_object"}
    )

    response_text = completion.choices[0].message.content
    print(f'response_text: {response_text}\n\n')

    return response_text

###  - Sentences that are not in the "original_plot" and change the essence or progression of the plot should be highlighted in green (#2cd6ae).
### Sentences that modify a sentence from the "original_plot" but do not significantly change the meaning should be highlighted in orange (#FF7900). If the modification is only a word or phrase, highlight just that word or phrase in orange (#FF7900). ###