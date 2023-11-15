from django.urls import path
from .views import *
from fcm_django.api.rest_framework import FCMDeviceAuthorizedViewSet
from rest_framework.routers import DefaultRouter
from django.urls.conf import include

router = DefaultRouter()
router.register('devices', FCMDeviceAuthorizedViewSet)
urlpatterns = [
    path('submit_img/', submit_img, name="submit_img"),
    path('register_user/', register_user, name = "register_user"),
    path('get_profils/<str:typ_rang>/', get_profils, name= "get_profils"),
    path('get_likes_dis/', get_likes_dis, name="get_likes_dis"),
    path('get_user/', get_user, name="get_user"),
    path('ping/', ping, name="ping"),
    path('delete_img/', delete_img, name="delete_img"),
    path('replace_profil/', replace_profil, name="replace_profil"),
    path('get_profile/<int:pk>/', get_profile, name="get_profile"),
    path('get_mylikes/', get_mylikes, name="get_mylikes"),
    path('get_new_photos/', get_new_photos, name="get_new_photos"),
    path('delete_room/<int:pk>/', delete_room, name="delete_room"),
    path('next_niveau/<int:pk>/', next_niveau, name='next_niveau'),
    path('create_message/', create_message, name="create_message"),
    path('delete_message/<int:pk>/', delete_message, name = 'delete_message'),
    path('set_info/', set_info, name="set_info"),
    path('set_password/', set_password, name="set_password"),
    path('get_cats/', get_cats, name="get_cats"),
    path('set_cats/', set_cats, name="set_cats"),
    path('search_place/<str:name>/', search_place, name="search_place"),
    path('set_place/', set_place, name="set_place"),
    path('set_verif/', set_verif, name="set_verif"),
    path('get_abons/', get_abons, name="get_abons"),
    path('set_abon/', set_abon, name="set_abon"),
    path('get_contact/', get_contact, name="get_contact"),
    path('only_verified/', only_verified, name="only_verified"),
    path('create_room/', create_room, name="create_room"),
    path('get_state/', get_state, name="get_state"),
    path('send_code/', create_code, name="create_code"),
    path('daily/', daily_tasks, name="daily_tasks"),
    path('get_command/', get_command, name="get_command"),
    path('get_favorites/<str:typ>/', get_favorites, name='get_favorites'),
    path('want_lov/<int:pk>/', want_lov, name="want_lov"),
    path('set_quart/', set_quart, name="set_quart"),
    path('get_pdetails/<str:key>/', get_pdetails, name="get_pdetails"),
    path('', include(router.urls)),
]