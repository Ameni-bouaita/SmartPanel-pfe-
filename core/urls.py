from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, signup, signin, LoginView 
from rest_framework_simplejwt.views import TokenRefreshView
from django.contrib.auth import views as auth_views  # Importing views for password reset
from .views import activate_email
from .views import submit_answer 
from .views import leaderboard, weekly_leaderboard  # ✅ Make sure leaderboard is imported
from .views import PanelistDetailView
from .views import test_send_reminder_email
from rest_framework_simplejwt.views import TokenObtainPairView
from .views import list_users, delete_user, create_admin, create_form_view , add_questions_view, add_sections_view, protected_view, create_campaign, panelist_signup, announcer_signup, list_interests, panelist_me, announcer_me, request_reset_password, reset_password, verify_reset_code

# Setting up the router for ViewSets
router = DefaultRouter()
router.register(r'users', UserViewSet)

urlpatterns = [
    # Routes for authentication and token management
    path('api/signup/', signup, name='signup'),
    path('api/signin/', signin, name='signin'),
    path('api/token/', LoginView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Routes for password reset functionality
    path('api/password_reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('api/password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('api/reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('api/reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
    
    # Route for email activation
    path('activate/<int:uid>/<str:token>/', activate_email, name='activate_email'),

    path('api/submit_answer/', submit_answer, name='submit_answer'),
   # path('api/submit_response/', submit_response, name='submit_response'),

    path('api/leaderboard/', leaderboard, name='leaderboard'),
    path('api/weekly_leaderboard/', weekly_leaderboard, name='weekly_leaderboard'),  # ✅ Weekly leaderboard

    path('panelist/<int:pk>/', PanelistDetailView.as_view(), name='panelist-detail'),
    path('test-send-reminder-email/', test_send_reminder_email, name='test_send_reminder_email'),

    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),

    path('admin/users/', list_users, name="admin-list-users"),
    path('admin/users/delete/<int:user_id>/', delete_user, name="admin-delete-user"),

    path('admin/create/', create_admin, name="admin-create"),


    path('form/create/', create_form_view, name='create_form'),
    path('form/<int:form_id>/sections/', add_sections_view, name='add_sections'),
    path('section/<int:section_id>/questions/', add_questions_view, name='add_questions'),
    path('api/interests/', list_interests, name='list_interests'),


    path('api/protected/', protected_view, name='protected-view'),  # Ajoute cette ligne
    path('api/campaigns/', create_campaign, name='create_campaign'),  # Ajoutez cette route
    path('api/panelist/signup/', panelist_signup, name='panelist_signup'),
    path('api/announcer/signup/', announcer_signup, name='announcer_signup'),

    path('api/panelist/me/', panelist_me, name='panelist_me'),
    path('api/announcer/me/', announcer_me, name='announcer_me'),


    path('api/request-reset-password/', request_reset_password, name='request_reset_password'),
    path('api/verify-reset-code/', verify_reset_code, name='verify_reset_code'),
    path('api/reset-password/', reset_password, name='reset_password'),


    # Include the routes for ViewSets (e.g., for users)
    path('api/', include(router.urls)),
]
