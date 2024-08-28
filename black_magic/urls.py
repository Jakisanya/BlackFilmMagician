"""black_magic URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.contrib.auth.views import LoginView
from django.urls import path
from film_creator.views import (HomeView, CreateView, LoginView, SignupView, generate_gpt_film_details, identify_plot_differences_view,
                                get_all_actor_names, get_actor_details)

urlpatterns = [
    path("admin/", admin.site.urls),
    path('', HomeView.as_view(), name='home'),
    path('create/', CreateView.as_view(), name='create'),
    path('login/', LoginView.as_view(), name='login'),
    path('signup/', SignupView.as_view(), name='signup'),
    path('generate_gpt_film_details/', generate_gpt_film_details, name='generate_gpt_film_details'),
    path('identify-plot-differences/', identify_plot_differences_view, name='identify_plot_differences'),
    path('get-all-actor-names/', get_all_actor_names, name='get_actor_names'),
    path('get-actor-details/', get_actor_details, name='get_actor_details')
]
