from django.shortcuts import render

# Create your views here.

from django.views.generic import TemplateView
from .models import Actor
import random

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

        # Fetch all actors and select three at random
        actors = list(Actor.objects.all())
        selected_actors = random.sample(actors, 3) if len(actors) >= 3 else actors
        context['actors'] = selected_actors

        return context

    def create(request):
        books = Book.objects.all()  # Retrieve all books from the database
        return render(request, 'create.html', {'books': books})
