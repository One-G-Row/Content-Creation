from django.urls import path
from ...posts import views

urlpatterns = [
	path('ai/generate/', views.ai_generate, name='ai_generate'),
	path('social/linkedin/', views.post_to_linkedin, name='post_to_linkedin'),
	path('social/instagram/', views.post_to_instagram, name='post_to_instagram'),
]