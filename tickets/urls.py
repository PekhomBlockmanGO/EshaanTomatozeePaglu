from django.urls import path
from . import views

urlpatterns = [
    # New manual link: http://127.0.0.1:8000/report/
    path('report/', views.qr_complaint_view, name='manual_complaint'),
    
    # Original QR link: http://127.0.0.1:8000/q/random-token-here/
    path('q/<str:token>/', views.qr_complaint_view, name='qr_complaint'),

]