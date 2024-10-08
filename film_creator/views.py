from django.shortcuts import render

from django.views.generic import TemplateView
from .models import Actor, Role, Film, User, UserProfile
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
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.contrib.auth.decorators import login_required


class HomeView(TemplateView):
    template_name = 'home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.request.user.is_authenticated:
            context['user'] = self.request.user
            # Retrieve the user profile.html if it exists
            # user_profile = UserProfile.objects.filter(user=self.request.user).first()
            # context['user_profile'] = user_profile
        else:
            context['user'] = None
            context['user_profile'] = None

        return context


class CreateView(TemplateView):
    template_name = 'create.html'


class LoginView(TemplateView):
    template_name = 'login.html'


class SignupView(TemplateView):
    template_name = 'signup.html'


class ProfileView(TemplateView):
    template_name = 'profile.html'


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
        result = identify_plot_differences(original_plot, original_genre, edited_plot)
        # Return the result back to the frontend as JSON
        return result


def identify_plot_differences(original_plot, original_genre, edited_plot):
    prompt_text = f'''
    Here is the reference data you will need to complete the task:
    - "original_plot": {original_plot}
    - "original_genre": {original_genre}
    - "edited_plot": {edited_plot}

    The task is as follows:

    1. **Correct the "edited_plot":**
       - Review the "edited_plot" for any punctuation, grammar, or spelling errors.
       - Make the necessary corrections and use this corrected version as the new "edited_plot" referred to below.

   
    2. **Highlight the differences between the "original_plot" and the "edited_plot":**
        - **Sentence-Level Differences (Essence or Progression):**
            - Compare the "edited_plot" to the "original_plot" and focus on any **changes that impact the meaning or flow** of the story. 
            - If the **essence** of a sentence (its core idea) or its **progression** (the way the plot unfolds) is altered, highlight that entire sentence in **green (#2cd6ae)**.  
            - **Examples of essence or progression changes:** 
                - A new event is introduced or an existing event is removed.
                - Characters act differently or with new motivations.
                - Significant plot points are added, modified, or removed.
                
        - **Character-Level Differences by Index:**
            - After identifying sentence-level changes, go through both plots and find **individual character differences** by comparing them index by index.  
            - Highlight these differences in **orange (#ff7900)**.  
            - **Note:** If a character difference occurs within a sentence already highlighted in green (because its essence or progression was altered), do not separately highlight that ASCII character in orange.
        
        - **Create the "highlighted_plot":**
            - Using the "edited_plot" as the base, create a new version called **"highlighted_plot"**.
            - Apply the following highlights:
                - Sentences with differences in essence or progression should be wrapped in `<span>` elements with a **green color (#2cd6ae)**.
                - Individual character differences should be wrapped in `<span>` elements with an **orange color (#ff7900)**, unless they are already part of a green-highlighted sentence.
          
    3. **Format the "highlighted_plot":**
       - Return the "highlighted_plot" in **well-structured paragraphs** using HTML:
           - **Ensure** that the entire text is divided into logical paragraphs using <p> elements.
           - Each paragraph should contain related sentences, and breaks should occur where appropriate, mimicking natural paragraph structure.
           - Then encapsulate the highlighted differences with <span> elements using the color #2cd6ae. For example: `<span style="color:#2cd6ae;">highlighted text</span>`.
           - **Ensure** that both the paragraph structure and the highlighting are applied simultaneously.

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
    print(f'response_text: {type(response_text), response_text}\n\n')

    response_text = re.sub(r'\\', '', response_text)
    highlighted_plot = re.findall(r'"highlighted_plot":\s*"(.*?)",.*"explanation', response_text, re.DOTALL)[0]
    explanation_of_difference = re.findall(r'"explanation_of_difference":\s*"([^"]*)".*?"genre"', response_text, re.DOTALL)[0]
    genre = re.findall(r'"genre":\s*"(.*?)"', response_text, re.DOTALL)[0]

    print(f'highlighted_plot: {highlighted_plot}')
    print(f'explanation_of_difference: {explanation_of_difference}')
    print(f'genre: {genre}')

    return JsonResponse({"highlighted_plot": highlighted_plot, "explanation_of_difference": explanation_of_difference,
                         "genre": genre})


def get_all_actor_names(request):
    if request.method == 'GET':
        # Retrieve all actor names
        actors = Actor.objects.all().values('tmdb_id', 'name')

        # Optional: you can print the number of actors retrieved for debugging
        print("len(actors):", len(actors))

        return JsonResponse({'actors': list(actors)})

    return JsonResponse({'error': 'Invalid request method'}, status=400)


def get_actor_details(request):
    if request.method == 'POST':
        # Parse the incoming JSON data
        data = json.loads(request.body)
        actor_tmdb_id = data.get('actor_tmdb_id')
        print("actor_tmdb_id: ", actor_tmdb_id)
        actor_name = data.get('actor_name')
        print("actor_name: ", actor_name)
    try:
        actor = Actor.objects.get(name=actor_name, tmdb_id=actor_tmdb_id)
        actor_details = {
            'name': actor.name,
            'picture_url': actor.picture,
        }
        return JsonResponse(actor_details)
    except Actor.DoesNotExist:
        return JsonResponse({'error': 'Actor not found'}, status=404)


def check_username_is_unique(request):
    if request.method == 'POST':
        # Parse the incoming JSON data
        data = json.loads(request.body)
        username = data.get('username')
        print('Received username:', username)
        print(User.objects.filter(username=username).exists())
        if User.objects.filter(username=username).exists():
            return JsonResponse({'isUnique': False})
        else:
            return JsonResponse({'isUnique': True})


def complete_signup(request):
    print('Received complete_signup request...')
    if request.method == 'POST':
        username = request.POST.get('username')
        password_first = request.POST.get('password1')
        password_confirmation = request.POST.get('password2')
        email_first = request.POST.get('email1')
        email_confirmation = request.POST.get('email2')

        # Basic validation
        if password_first != password_confirmation:
            messages.error(request, "Passwords do not match.")

        if email_first != email_confirmation:
            messages.error(request, "Emails do not match.")

        try:
            user = User.objects.create_user(username=username, password=password_first, email=email_first)
            user.save()
            print('User created successfully.')
            print(user)
            login(request, user)
            return redirect(reverse('home'))
        except ValidationError as e:
            messages.error(request, str(e))
