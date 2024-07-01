from django.urls import path
from sop import views



urlpatterns = [
   path('form/get/', views.get_sop_form_by_department, name='get_sop_form'),
   path('form/create/', views.create_sop_question_by_department, name='create_sop_form'),
   path('form/update/', views.update_sop_question, name='update_sop_question'),
   path('form/delete/', views.delete_sop_question, name='delete_sop_question'),
   path('form/submit/', views.submit_question_reponse, name='submit_question_reponse'),
]
