from django.shortcuts import render

# Create your views here.

from django.views.generic import TemplateView
from .models import Actor, Role, Film
import random
from django.http import JsonResponse

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
    actors_data = [{'name': actor.name, 'picture': actor.picture.url, 'tmdb_id': actor.tmdb_id} for actor in
                   selected_actors]
    return JsonResponse({'new_actors': actors_data})
