from django.urls import path
from . import views

urlpatterns=[
path("",views.dashboard,name="dashboard"),
path("patients/",views.patient_list,name="patients"),
path("patients/",views.patient_list,name="patient_list"),
path("patients/add/",views.add_patient,name="add_patient"),
path("patients/<str:patient_id>/",views.patient_detail,name="patient_detail"),
path("patients/<str:patient_id>/edit/",views.edit_patient,name="edit_patient"),
path("patients/<str:patient_id>/delete/",views.delete_patient,name="delete_patient"),
path("procedures/",views.procedures,name="procedures"),
path("procedures/<str:patient_id>/",views.procedure_timeline,name="procedure_timeline"),
path("procedures/<str:patient_id>/confirm/<int:step_index>/",views.confirm_step,name="confirm_step"),
path("procedures/<str:patient_id>/undo/<int:step_index>/",views.undo_step,name="undo_step"),
path("procedures/<str:patient_id>/reminder/<int:step_index>/",views.send_reminder,name="send_reminder"),
path("protocols/",views.protocols,name="protocols"),
path("protocols/<str:protocol_type>/",views.protocol_detail,name="protocol_detail"),
path("login/",views.login,name="login"),
path("register/",views.register,name="register"),
path("logout/",views.logout_view,name="logout"),
]