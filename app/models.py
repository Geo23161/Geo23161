from django.db import models
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
import json
import io 
from rest_framework import serializers
from django.utils import timezone
from datetime import datetime, timedelta
from cloudinary.models import CloudinaryField
from django.db.models.signals import pre_save, post_save, m2m_changed
from django.dispatch import receiver
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from colorthief import ColorThief
from fcm_django.models import FCMDevice
from firebase_admin.messaging import Message as FCMMess , Notification, AndroidNotification, WebpushConfig, WebpushFCMOptions, AndroidConfig, APNSConfig, APNSPayload, Aps
import sys
from PIL import Image as Pil
import requests
from io import BytesIO
import random

if sys.version_info < (3, 0):
    from urllib2 import urlopen
else:
    from urllib.request import urlopen

DEFAULT_ESSENTIALS = {
    'all_swipe' : {},
    'seen_tofs' : [],
    'already_seens' : []
}
DEFAULT_NUMBER = 7
IS_DEV = True
ANONYM_MAX = 3

def calculer_age(date_naissance):
    # Obtenez la date actuelle
    date_actuelle = timezone.now()

    # Calculez la différence entre la date actuelle et la date de naissance
    difference = date_actuelle - date_naissance

    # Extrait l'année de la différence
    age = difference.days // 365

    return age

def semaine_unique():
    date_actuelle = timezone.now()
    return f"sem:{date_actuelle.year}:{date_actuelle.isocalendar()[1]}"

COMPATIBILITY_ASTRO = {
            "Bélier": {"Lion": 80, "Sagittaire": 70, "Verseau": 60, "Cancer": 50, "Balance": 40},
            "Taureau": {"Vierge": 80, "Capricorne": 70, "Cancer": 60, "Poissons": 50, "Lion": 40},
            "Gémeaux": {"Balance": 80, "Verseau": 70, "Lion": 60, "Sagittaire": 50, "Poissons": 40},
            "Cancer": {"Scorpion": 80, "Poissons": 70, "Vierge": 60, "Taureau": 50, "Bélier": 40},
            "Lion": {"Bélier": 80, "Sagittaire": 70, "Balance": 60, "Gémeaux": 50, "Scorpion": 40},
            "Vierge": {"Taureau": 80, "Capricorne": 70, "Cancer": 60, "Scorpion": 50, "Gémeaux": 40},
            "Balance": {"Gémeaux": 80, "Verseau": 70, "Lion": 60, "Sagittaire": 50, "Cancer": 40},
            "Scorpion": {"Cancer": 80, "Poissons": 70, "Vierge": 60, "Capricorne": 50, "Lion": 40},
            "Sagittaire": {"Bélier": 80, "Lion": 70, "Balance": 60, "Verseau": 50, "Vierge": 40},
            "Capricorne": {"Vierge": 80, "Taureau": 70, "Scorpion": 60, "Poissons": 50, "Bélier": 40},
            "Verseau": {"Gémeaux": 80, "Balance": 70, "Lion": 60, "Sagittaire": 50, "Taureau": 40},
            "Poissons": {"Cancer": 80, "Scorpion": 70, "Vierge": 60, "Capricorne": 50, "Gémeaux": 40}
    }


# Create your models here.

def room_slug(user1, user2, is_group = False) :
    ordered = sorted([user1.pk, user2.pk])
    return ("" if not is_group else "g") + f"{ordered[0]}m{ordered[1]}"

def the_other(room, user) :
    return room.users.all().exclude(pk = user.pk).first()

def set_niveau(room ) :
    pl = PerfectLovDetails.objects.filter(key = 'launcher:' + str(room.pk))
    if pl.exists() :
        taches = room.niveau.taches.all().filter(niveau = room.niveau.level)
        tot = 0
        used = [ t.pk for t in room.niveau.taches.all()]
        for tache in taches :
            tot += tache.coef
        print('tots ', tot)
        if tot < 100 :
            new_task = Taches.objects.filter(niveau = room.niveau.level).exclude(pk__in= used).order_by('?').first()
            if new_task :
                room.niveau.cur_task = new_task.pk
                room.niveau.taches.add(new_task)
                room.niveau.save()
            else :
                tot += 100
        elif tot >= 100 :
            print(0)
            lvvl = room.niveau.level
            room.niveau.level += 1
            room.niveau.save()
            room.niveau.help_dets = g_v(f'help:niv:{lvvl + 1}')
            new_task = Taches.objects.filter(niveau = room.niveau.level).exclude(pk__in= used).order_by('?').first().pk
            room.niveau.cur_task = new_task
            room.niveau.taches.add(new_task)
            room.niveau.save()
        pl.delete()

    return NiveauSerializer(room.niveau).data

def signe_astrologique(date_naissance):
    # Récupérer le mois et le jour de la date de naissance
    mois = date_naissance.month
    jour = date_naissance.day

    # Dates de début et de fin pour chaque signe astrologique
    dates_signes = [
        (1, 20, 2, 18, "Verseau"),
        (2, 19, 3, 20, "Poissons"),
        (3, 21, 4, 19, "Bélier"),
        (4, 20, 5, 20, "Taureau"),
        (5, 21, 6, 20, "Gémeaux"),
        (6, 21, 7, 22, "Cancer"),
        (7, 23, 8, 22, "Lion"),
        (8, 23, 9, 22, "Vierge"),
        (9, 23, 10, 22, "Balance"),
        (10, 23, 11, 21, "Scorpion"),
        (11, 22, 12, 21, "Sagittaire"),
        (12, 22, 1, 19, "Capricorne")
    ]

    # Trouver le signe astrologique correspondant à la date de naissance
    for mois_debut, jour_debut, mois_fin, jour_fin, signe in dates_signes:
        if (mois == mois_debut and jour >= jour_debut) or (mois == mois_fin and jour <= jour_fin):
            return signe

    # Si aucune correspondance n'a été trouvée, retourner None
    return None

def g_v(key : str) :
    return PerfectLovDetails.objects.get(key = key).value

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError(('The Email must be set'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()

        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError(('Superuser must have is_staff'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(('superuser must have is_superuser set to True'))
        return self.create_user(email, password, **extra_fields)

class Cat(models.Model) :
    name = models.CharField(max_length=150, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class StyleWord(models.Model) :
    masculin = models.CharField(max_length = 150, null = True, blank = True)
    feminin = models.CharField(max_length = 150, null = True, blank = True)
    pluriels = models.CharField(max_length = 150, null = True, blank = True)
    created_at = models.DateTimeField(auto_now_add = True)

class Emoji(models.Model) :
    emoji = models.CharField(max_length = 10, null = True, blank = True)
    created_at = models.DateTimeField(auto_now_add = True)

class Mood(models.Model) :
    name = models.TextField(null = True, blank = True)
    created_at = models.DateTimeField(auto_now = True)


class User(AbstractBaseUser, PermissionsMixin) :
    prenom = models.CharField(max_length=150, null=True, blank=True)
    email = models.EmailField(unique=True)
    sex = models.CharField(null=True, blank=True, max_length=10)
    birth = models.DateTimeField(null=True, blank=True)
    searching = models.TextField(null=True, blank=True)
    quart = models.TextField(null=True, blank=True)
    cur_abn = models.OneToOneField("Abon", related_name="is_cur_for", on_delete=models.CASCADE, null=True, blank=True)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    objects = CustomUserManager()
    likes = models.ManyToManyField("User", related_name='like', null=True, blank=True)
    super_likes = models.ManyToManyField("User", related_name='super_like', null=True, blank=True)
    dislikes = models.ManyToManyField("User", related_name='dislike', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last = models.DateTimeField(null=True, blank=True, default=timezone.now())
    essentials = models.TextField(null=True, blank=True)
    seens_photos = models.TextField(null=True, blank=True)
    cats = models.ManyToManyField(Cat, related_name="users", null=True, blank=True)
    place = models.TextField(null=True, blank=True)
    only_verified = models.BooleanField(default=True)
    last_like_notif = models.DateTimeField(null=True, blank=True)
    anonym_history = models.TextField(null = True, blank = True)
    exil_post = models.TextField(null = True, blank = True)
    mood = models.ForeignKey(Mood, on_delete = models.CASCADE, related_name = "users", null = True, blank = True)

    def get_mood(self) :
        return MoodSerializer(self.mood).data
    
    def get_age(self) :
        try :
            return str(calculer_age(self.birth)) 
        except :
            return "25"
        
    def get_des(self) :
        return json.loads(self.searching)

    def get_exils(self) :
        return json.loads(self.exil_post) if self.exil_post else []

    def set_exiles(self, id) :
        try :
            exiles = json.loads(self.exil_post)
        except :
            exiles = []
        exiles.append(id)
        self.exil_post = exiles
        self.save()

    def anonym_out(self) :
        anonym_conv = json.loads(g_v('anonym:conv'))
        count = self.rooms.filter(is_proposed = True).count()
        if self.cur_abn :
            abn = self.cur_abn.get_typ()['name']
        else :
            abn = 'free'
        return count < anonym_conv[abn]
        
    def set_history(self, pk) :
        try :
            history = json.loads(self.anonym_history)
            history[semaine_unique()]
            print(self.anonym_history)
        except :
            history = {
                semaine_unique() : []
            }
        history[semaine_unique()].append(pk)
        self.anonym_history = json.dumps(history)
        self.save()

    def get_anonyms(self) :
        return json.loads(self.anonym_history) if self.anonym_history else None
    
    def set_excepts(self, excepts) :
        dets, created = PerfectLovDetails.objects.get_or_create(key = f'user:{self.pk}:excepts')
        if not dets.value :
            dets.value = json.dumps(excepts)
            dets.save()
        else :
            old_ex = json.loads(dets.value)
            new_ex = excepts + old_ex
            without_rep = []
            for pk in new_ex :
                if not pk in without_rep :
                    without_rep.append(pk)
            dets.value = json.dumps(without_rep)
            dets.save()
        
    def get_excepts(self) :
        dets, created = PerfectLovDetails.objects.get_or_create(key = f'user:{self.pk}:excepts')
        try :
            vals = json.loads(dets.value)
        except :
            vals = [

            ]
        return vals

    def get_txt_likes(self) :
        matches = [
            the_other(r, self).pk for r in self.rooms.all()
        ]
        return [
            user.prenom for user in self.likes.exclude(pk__in = matches).all().order_by("?")
        ][:3]

    def get_likes_prenoms(self) :
        matches = [
            the_other(r, self).pk for r in self.rooms.all()
        ]
        return ', '.join( [
            user.prenom for user in self.likes.exclude(pk__in = matches).all() 
        ][:3]) + '...'

    def get_status(self) :
        return 'free' if not self.cur_abn else self.cur_abn.status

    def get_tofs(self) :
        return json.loads(self.seens_photos)

    def get_essentials(self) :
        try :
            return json.loads(self.essentials)
        except :
            defau = json.dumps(DEFAULT_ESSENTIALS)
            self.essentials = defau
            self.save()
            return DEFAULT_ESSENTIALS
    
    def set_essentials(self, essentials) :

        self.essentials = json.dumps(essentials)
        self.save()

    def is_online(self, minu = 3) :
        last = self.last
        now = timezone.now()
        return (now.timestamp() - last.timestamp()) < minu*60

    def get_likes(self) :
        return [ u.pk for u in self.likes.all() ]
    
    def get_dislikes(self) :
        return [ u.pk for u in self.dislikes.all() ]

    def get_quart(self) :
        return json.loads(self.quart) if self.quart else json.loads(self.place)
    
    def get_profil(self) :
        return self.photos.filter(is_profil = True).first()
    
    def get_picture(self) :
        p = self.get_profil().get_picture()
        lis = p.split("/upload/")
        return "/upload/q_auto/".join(lis) if len(lis) > 1 else ""
    
    def get_sign(self) :
        return signe_astrologique(self.birth)
    
class PaymentPortal(models.Model) :
    user = models.ForeignKey(User, related_name = "my_payments", on_delete = models.CASCADE)
    amount = models.IntegerField(default=50)
    transref = models.CharField(max_length = 50)
    typ = models.CharField(max_length = 20)
    code = models.IntegerField(default = 1)
    abn = models.CharField(max_length= 150)


class Prevision(models.Model) :
    user = models.ForeignKey(User, on_delete = models.CASCADE, null = True, blank = True, related_name="previsions")
    text = models.TextField(null = True, blank = True)    
    target = models.ForeignKey(User, on_delete = models.CASCADE, null = True, blank = True, related_name="target_previsions")
    swipes = models.IntegerField(default = 14)
    actual_swipe = models.IntegerField(default = 0)
    status = models.CharField(max_length=150, default="pending")
    created_at = models.DateTimeField(auto_now = True)

class UserGroup(models.Model) :
    creator = models.ForeignKey(User, related_name="groups_created", null = True, blank = True, on_delete=models.CASCADE)
    users = models.ManyToManyField(User, related_name="my_groups")
    likes = models.ManyToManyField("UserGroup", related_name="like")
    created_at = models.DateTimeField(auto_now_add = True)
    code = models.CharField(max_length=150, null = True, blank = True)
    rooms = models.ManyToManyField("RoomMatch", related_name="groups", null = True, blank = True)
    matches = models.ManyToManyField("UserGroup", related_name="is_matches", null= True, blank = True)
    sem_match = models.ForeignKey("UserGroup", on_delete=models.PROTECT, related_name="is_sem_for", null = True, blank = True)
    proposeds = models.ManyToManyField("UserGroup", related_name="is_proposed", null= True, blank = True)
    def quit_group(self, us : User) :
        self.users.remove(us)
        for ro in self.rooms.all() :
            ro.users.remove(us)
        return [r.slug for r in self.rooms.all()]
    


    def get_creator(self) :
        return self.creator.pk
    
    def get_name(self) :
        return " ".join([u.prenom + f"{',' if self.users.all()[self.users.all().count() - 1].pk != u.pk else ''}" for u in self.users.all()])
    
    def get_oth_name(self, use : User) :
        return " ".join([u.prenom + f"{',' if self.users.all().exclude(pk = use.pk)[self.users.all().exclude(pk = use.pk).count()-1].pk == u.pk else ''}" for u in self.users.all().exclude(pk = use.pk)])

class Reaction(models.Model) :
    actor = models.ForeignKey(User, related_name = "reactions", on_delete = models.CASCADE, null = True, blank = True)
    target = models.ForeignKey(User, related_name = "provoked", on_delete = models.CASCADE, null = True, blank = True)
    emoji = models.ForeignKey(Emoji, related_name = "reactions", on_delete = models.CASCADE, null = True, blank = True)
    word = models.ForeignKey(StyleWord, related_name = "reactions", on_delete = models.CASCADE, null = True, blank = True)
    created_at = models.DateTimeField(auto_now_add = True)

    def get_emoji(self) :
        return None if not self.emoji else self.emoji.emoji
    
    def get_word(self) :
        return None if not self.word else {'masculin' : self.word.masculin, 'feminin' : self.word.feminin}

class Verif(models.Model) :
    piece = models.ImageField(upload_to="pieces/")
    created_at = models.DateTimeField(auto_now = True)
    status = models.CharField(max_length=10, default='pending')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="verifs", null=True, blank=True)

    def __str__(self) -> str:
        return self.user.email
    
    def get_piece(self) :
        return self.piece.url

class Photos(models.Model) :
    name = models.CharField(max_length=150, null=True, blank=True)
    file = models.ImageField(upload_to="photos/", max_length=500)
    is_profil = models.BooleanField(default=False)
    user = models.ForeignKey(User, related_name="photos", null=True, blank=True, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now=True)
    color = models.CharField(max_length = 100, null = True, blank = True)
    def get_picture(self) :
        url = self.file.url
        if not "https://" in url :
            url= self.file.url
        return url

    def set_color(self) :
        fd = urlopen(self.get_picture())
        f = io.BytesIO(fd.read())
        color_thief = ColorThief(f)
        color = f"rgb{color_thief.get_color(quality=1)}"
        self.color = color
        self.save()
        return color
    
class PerfectLovDetails(models.Model) :
    key = models.CharField(max_length=150, null=True, blank=True)
    value = models.TextField(null=True, blank=True)

    def __str__(self) -> str:
        return self.key
    

class DistanceObj(models.Model) :
    user = models.ForeignKey(User, related_name="distance_obj", null=True, blank=True, on_delete=models.CASCADE)
    distances = models.TextField(null=True, blank=True)

class Abon(models.Model) :
    typ = models.TextField(null=True, blank=True)
    debut = models.DateTimeField(null=True, blank=True)
    is_on = models.BooleanField(default=True)
    for_days = models.IntegerField(default=30)
    user = models.ForeignKey(User, related_name="abns", null=True, blank=True, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=150, null=True, blank=True)
    verif = models.ForeignKey(Verif, related_name="abns", null=True, blank=True, on_delete=models.CASCADE)
    def get_typ(self) :
        return json.loads(self.typ)
    
    def check_on(self) :
        now = timezone.now()
        if self.debut + timedelta(days=self.for_days) > now :
            self.is_on = False
            self.save()
    
class Taches(models.Model) :
    niveau = models.IntegerField(default=0)
    content = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    coef = models.IntegerField(default=20)
    seens = models.ManyToManyField(User, related_name="taches", null=True, blank=True)

class Niveau(models.Model) :
    level = models.IntegerField(default=0)
    taches = models.ManyToManyField(Taches, null=True, blank=True, related_name="niveaux")
    cur_task = models.IntegerField(default=0, null = True, blank=True)
    help_dets = models.TextField(default=json.dumps(["L'assistant de conversation",  "Il s'agit d'une IA dont le principal rôle est de vous proposer des sujets de discussions, des questions, des rendez-vous... Plus vous discutez, plus son niveau augmente et plus ils vous raprochent par ses propositions."]) )
    def get_task(self) :
        return Taches.objects.get(pk = self.cur_task)
    def get_help(self) :
        return json.loads(self.help_dets)
        

class RoomMatch(models.Model) :
    users = models.ManyToManyField(User, related_name="rooms", null=True, blank=True)
    slug = models.CharField(max_length=150, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    niveau = models.OneToOneField(Niveau, related_name="room", on_delete=models.CASCADE, null=True, blank=True)
    is_proposed = models.BooleanField(default=False)
    why = models.TextField(default='Vous avez mutuellement kiffé vos photos de profil.')
    anonymous_obj = models.TextField(null = True, blank = True)
    is_categorized = models.BooleanField(default=False)

    def is_match(self) :
        return (UserGroup.objects.get(pk = self.get_groups()[0]) in UserGroup.objects.get(pk = self.get_groups()[len(self.get_groups()) -1]).matches.all()) if self.groups.count() else False

    def get_groups(self) :
        return [g.pk for g in self.groups.all()] if self.groups.count() else 0

    def get_anonymous(self) :
        return json.loads(self.anonymous_obj) if self.anonymous_obj else None
    def next_niveau(self) :
        return set_niveau(self)

    def __str__(self) -> str:
        try :
            us = [u for u in self.users.all()]
            return f"{us[0].prenom}+{us[1].prenom}"
        except :
            return f"Room{self.pk}"


class Image(models.Model) :
    name = models.CharField(max_length=150, null=True, blank=True)
    image = models.ImageField(upload_to='messages/images/')
    details = models.TextField(null=True, blank=True)
    
    def get_details(self) :
        return [] if not self.details else json.loads(self.details)
    def set_details(self, dets) :
        self.details = json.dumps(dets)
        self.save()
    def get_image(self) :
        return self.image.url
    
    def get_preview(self):
        lis = self.get_image().split("/upload/")
        return "/upload/q_1/".join(lis) if len(lis) > 1 else ""
    
    def add_elt(self, elt ) :
        dets = self.get_details().append(elt)
        return dets

    def set_size(self) :
        res = requests.get(self.get_preview())
        img = Pil.open(BytesIO(res.content))
        width, height = img.size
        self.set_details(self.add_elt(width))
        self.set_details(self.add_elt(height))
    

class Audio(models.Model) :
    name = models.CharField(max_length=150, null=True, blank=True)
    audio = CloudinaryField(resource_type='', null=True, blank=True)
    details = models.TextField(null=True, blank=True)
    
    def get_details(self) :
        return [] if not self.details else json.loads(self.details)

    def get_audio(self) :
        return self.audio.url

class Video(models.Model) :
    name = models.CharField(max_length=150, null=True, blank=True)
    video = CloudinaryField(resource_type='video', null=True, blank=True)
    image = models.ImageField(upload_to='messages/images/')
    details = models.TextField(null=True, blank=True)
    
    def get_preview(self) :
        lis = self.image.url.split("/upload/")
        return "/upload/q_auto:eco/".join(lis) if len(lis) > 1 else ""

    def get_details(self) :
        return [] if not self.details else json.loads(self.details)

    def get_video(self) :
        return self.video.url
    
    def add_elt(self, elt ) :
        dets = self.get_details().append(elt)
        return dets

    def set_size(self) :
        res = requests.get(self.get_preview())
        img = Pil.open(BytesIO(res.content))
        width, height = img.size
        self.set_details(self.add_elt(width))
        self.set_details(self.add_elt(height))

    def set_details(self, dets) :
        self.details = json.dumps(dets)
        self.save()

class Message(models.Model) :
    room = models.ForeignKey(RoomMatch, related_name="messages", on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    step = models.CharField(max_length=150, default='sent')
    text = models.TextField(null=True, blank=True)
    image = models.OneToOneField(Image, related_name='message', on_delete=models.CASCADE, null=True, blank=True)
    audio = models.OneToOneField(Audio, related_name="message", on_delete=models.CASCADE, null=True, blank=True)
    video = models.OneToOneField(Video, related_name="message", on_delete=models.CASCADE, null=True, blank=True)
    functional = models.TextField(null = True, blank = True)
    user = models.IntegerField(default=0)
    old_pk = models.BigIntegerField(default=0)
    reply = models.TextField(null = True, blank =True)
    

    def get_reply(self) :
        rep = json.loads(self.reply) if self.reply else None
        return rep      

    def get_room(self) :
        return self.room.pk 
    
class Transaction(models.Model) :
    trans_id = models.CharField(max_length=150, null=True, blank=True)
    abn = models.ForeignKey(Abon, null=True, blank=True, on_delete=models.CASCADE, related_name="transactions")
    created_at = models.DateTimeField(auto_now=True)  



def state_messag(room, user : User) :
    rm = RoomMatch.objects.filter(pk = room)
    if not rm.exists() : return 'deleted'
    abn = user.cur_abn
    day_dis = json.loads(g_v('day:discuss'))
    limit = day_dis[abn.status]
    now = timezone.now()
    day_messages = Message.objects.filter(created_at__gt = timezone.datetime(now.year, now.month, now.day))
    rms = []
    for mes in day_messages :
        if not mes.get_room() in rms :
            rms.append(mes.get_room())
    if not room in rms :
        rms.append(room)
    if len(rms) > limit :
        return 'limited'
    rm = rm.first()
    if (not user.cur_abn.verif) and rm.users.exclude(pk= user.pk).first().only_verified :
        return 'verified'
    return 'on'
    
def handle_mess_perm(room, user, old_pk) :
    state = state_messag(room, user)
    channel_layer = get_channel_layer()
    slug = g_v('del:room:' + str(room)) if state == 'deleted' else RoomMatch.objects.get(pk = room).slug
    if state in ['limited', 'verified', 'deleted'] : 
        async_to_sync(channel_layer.group_send)( slug, {
                'type' : 's_m',
                'result' : {
                    'state' : state,
                    'target' : user.pk,
                    'old_pk' : old_pk
                }
        })
    Message.objects.filter(old_pk = old_pk).delete()
        

class Notif(models.Model) :
    typ = models.CharField(max_length=150, null=True, blank=True)
    text = models.TextField(null=True, blank=True)
    photo = models.ForeignKey(Photos, related_name="notifs", on_delete=models.CASCADE, null=True, blank=True)
    user = models.ForeignKey(User, related_name='notifs', null=True, blank=True, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    urls = models.TextField(null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.user}:{self.typ}"
    
    def get_photo(self) :
        return self.photo.get_picture() if self.photo else None

    def get_urls(self) :
        return json.loads(self.urls)

class InvitCode(models.Model) :
    code = models.CharField(max_length=150, null=True, blank=True)
    for_abon = models.CharField(max_length=150, default="silver")
    creator= models.IntegerField(null=True, blank=True)
    quota = models.IntegerField(default=5)
    def get_creator(self) :
        return User.objects.get(pk = self.creator)

class UserCode(models.Model) :
    user = models.OneToOneField(User, related_name="code", on_delete=models.CASCADE, null=True, blank=True)
    state = models.CharField(default='waiting', max_length=150)
    reason = models.TextField(null=True, blank=True)
    code = models.ForeignKey(InvitCode, related_name="users", on_delete=models.CASCADE, null=True, blank=True)
    
    
class Post(models.Model) :
    user = models.ForeignKey(User, on_delete = models.CASCADE, related_name="posts", null = True, blank = True)
    is_anonymous = models.BooleanField(default = False)
    text = models.TextField(null = True, blank = True)
    image = models.FileField(upload_to="posts/", null=True, blank=True)
    likes = models.ManyToManyField(User, related_name="like_posts", blank=True)
    origin = models.ForeignKey("Post", on_delete = models.CASCADE, related_name="comments", null = True, blank =True)
    created_at = models.DateTimeField(auto_now_add = True)
    seens = models.ManyToManyField(User, related_name="seen_posts", blank=True)

    def get_likes(self) :
        return self.likes.count()
    
    def get_seens(self) :
        return self.seens.count()
    
    def get_comments(self) :
        return self.comments.count()
    
    def get_image(self) :
        return self.image.url if self.image else None

#########################"Serializers"{{{{{{{{{{{{{{{}}}}}}}}}}}}}}}
    
class MoodSerializer(serializers.ModelSerializer) :
    class Meta :
        model = Mood
        fields = ('id', 'name')

class ReactionSerializer(serializers.ModelSerializer) :
    class Meta :
        model = Reaction
        fields = ('id', 'get_emoji', 'get_word')
    
class PostUserSerializer(serializers.ModelSerializer) :
    class Meta :
        model = User
        fields = ('id', 'prenom', "get_picture", "created_at" )

class PostSerializer(serializers.ModelSerializer) :
    user = PostUserSerializer()
    class Meta :
        model = Post
        fields = ('id', 'user', 'text', 'get_image', "get_likes", "get_comments", "created_at", "is_anonymous")

    def to_representation(self, instance):
        request = self.context.get('request')
        representation = super().to_representation(instance)
        if request :
            representation['i_like'] = request.user in instance.likes.all()
            representation['i_comment'] = request.user in instance.comments.all()

        return representation

class VerifSerializer(serializers.ModelSerializer) :
    class Meta :
        model = Verif
        fields = ('id', 'get_piece', 'created_at', 'status')

class CatSerializer(serializers.ModelSerializer) :
    class Meta :
        model = Cat
        fields = ('id', 'name')

class PhotoSerializer(serializers.ModelSerializer) :
    class Meta :
        model = Photos
        fields = ('id', 'name', 'is_profil', 'get_picture', 'color')

class AbonSerializer(serializers.ModelSerializer) :
    verif = VerifSerializer()
    class Meta :
        model = Abon
        fields = ('id', 'get_typ', 'debut', 'is_on', 'for_days', 'verif', 'status', 'created_at')

class UserSerializer(serializers.ModelSerializer) :
    get_profil = PhotoSerializer()
    photos = PhotoSerializer(many = True)
    cur_abn = AbonSerializer()
    cats = CatSerializer(many = True)
    class Meta :
        model = User
        fields = ('id', 'get_profil', 'photos', 'prenom', 'email', 'birth', 'sex', 'searching', 'quart', 'get_sign', 'cur_abn', 'get_likes', 'cats', 'only_verified', 'get_status', 'get_des')

class UserProfilSerializer(serializers.ModelSerializer) :
    get_profil = PhotoSerializer()
    photos = PhotoSerializer(many = True)

    class Meta :
        model = User
        fields = ('id', 'get_profil', 'photos', 'prenom', 'get_sign', 'get_status', 'last', 'get_age', 'get_des')

    def to_representation(self, instance : User):
        request = self.context.get('request')
        representation = super().to_representation(instance)
        if request :
            representation['i_like'] = request.user in instance.like.all()
            representation['commons'] = [{'id' : c.pk, 'name' : c.name} for c in instance.cats.all().intersection(request.user.cats.all())]
            if not (len(representation['commons']) and request.user.rooms.filter(is_proposed = False).count()) :
                compats = COMPATIBILITY_ASTRO[instance.get_sign()]
                if request.user.get_sign() in compats.keys() :
                    representation['commons'] = [{'id' : 0, 'name' : 'sign'}]

            if Reaction.objects.filter(actor__pk = instance.pk, target__pk = request.user.pk).exists() :
                representation['reaction'] = ReactionSerializer(Reaction.objects.filter(actor__pk = instance.pk, target__pk = request.user.pk).first()).data
            representation['reaction'] = MoodSerializer(instance.mood).data
            if Prevision.objects.filter(user = request.user, target = instance, status = 'pending') :
                representation['has_room'] = False
            else :
                representation['has_room'] = instance.rooms.all().filter(created_at__gt = timezone.now() - timezone.timedelta(days = 6), created_at__lt = timezone.now()).count()
            
        return representation

class EmojiSerializer(serializers.ModelSerializer) :
    class Meta :
        model = Emoji
        fields = ('id', 'emoji')

class StyleWord(serializers.ModelSerializer) :
    class Meta :
        model = StyleWord
        fields = ('id', 'masculin', 'feminin')

class TacheSerializer(serializers.ModelSerializer) :

    class Meta :
        model = Taches
        fields = ('id', 'niveau', 'content')

class NiveauSerializer(serializers.ModelSerializer) :
    get_task = TacheSerializer()
    class Meta :
        model = Niveau
        fields = ('id', 'level', 'get_task', 'get_help')

class SimpleUserSerializer(serializers.ModelSerializer) :

    class Meta :
        model = User
        fields = ('id', 'prenom', 'get_picture', 'last', 'get_status', 'get_des')

class RoomSerializer(serializers.ModelSerializer) :
    users = SimpleUserSerializer(many = True)
    niveau = NiveauSerializer()
    class Meta :
        model = RoomMatch
        fields = ('id', 'users', 'slug', 'created_at', 'niveau', 'is_proposed', 'why', 'get_anonymous', 'get_groups', 'is_match')

class ImageSerializer(serializers.ModelSerializer) :
    class Meta :
        model = Image
        fields = ('id', 'name', 'get_image', 'get_preview', 'get_details')

class AudioSerializer(serializers.ModelSerializer) :
    class Meta :
        model = Audio
        fields = ('id', 'name', 'get_audio', 'get_details')

class VideoSerializer(serializers.ModelSerializer) :
    class Meta :
        model = Video
        fields = ('id', 'name', 'get_video', 'get_details', 'get_preview')

class MessageSerializer(serializers.ModelSerializer) :
    image = ImageSerializer()
    audio = AudioSerializer()
    video = VideoSerializer()
    class Meta :
        model = Message
        fields = ('id', 'get_room', 'created_at', 'step', 'text', 'image', 'audio', 'video' ,'user', 'old_pk', 'get_reply', 'functional' )

class NotifSerializer(serializers.ModelSerializer) :
    class Meta :
        model = Notif
        fields = ('id', 'typ', "text", "get_photo", "created_at", "get_urls")


class GroupSerializer(serializers.ModelSerializer) :
    users = UserProfilSerializer(many = True)
    class Meta :
        model = UserGroup
        fields = ('id', 'users', 'get_creator', 'get_name')
    
    def to_representation(self, instance : UserGroup):
        request = self.context.get('request')
        representation = super().to_representation(instance)
        my_groups = request.user.my_groups.all()
        representation['like_us'] = [ g.pk for g in instance.likes.all() if g in my_groups ]

        return representation 

class ChatGroupSerializer(serializers.ModelSerializer) :
    users = SimpleUserSerializer(many = True)
    rooms = RoomSerializer(many = True)
    class Meta :
        model = UserGroup
        fields = ('id', 'get_name', 'get_creator', 'code', 'users', 'rooms')


###################################Signaux#################################
"""
@receiver(post_save, sender = RoomMatch)
def send_new_room(sender, instance : RoomMatch, **kwargs):
    channel_layer = get_channel_layer()
    if kwargs['created'] :
        print('GET it herreeee')
        for user in instance.users.all() :
            async_to_sync(channel_layer.group_send)(f"{user.pk}m{user.pk}", {
                'type' : 'new_room',
                'result' : RoomSerializer(instance).data
            })
"""

@receiver(post_save, sender = Post)
def sen_message(sender, instance : Post, **kwargs):
    channel_layer = get_channel_layer()
    print(not instance.origin)
    if kwargs['created'] and not instance.origin :
        async_to_sync(channel_layer.group_send)('celibapps', {
                'type' : 'new_post',
                'result' : 0,
        })

@receiver(post_save, sender = Message)
def send_message(sender, instance : Message, **kwargs):
    channel_layer = get_channel_layer()
    if kwargs['created'] :

        async_to_sync(channel_layer.group_send)(instance.room.slug, {
                'type' : 'new_message',
                'result' : MessageSerializer(instance).data,
                'other' : [
                    u.pk for u in instance.room.users.all() if u.only_verified
                ]
        })
        oth_user = instance.room.users.exclude(pk = instance.user).first()
        try :

            devices = FCMDevice.objects.filter(user__pk = oth_user.pk)
            user = User.objects.get(pk = instance.user)
            for device in devices :
                urls = ['/chat']
                device.send_message(
                    message = FCMMess(notification=Notification(title= "Nouveau Message", body= User.objects.get(pk = instance.user).prenom + " vous a laissé de nouveaux messages"),
                    )
                    
                )
                """ android = AndroidConfig(notification = AndroidNotification(click_action="FCM_PLUGIN_ACTION")),
                    webpush = WebpushConfig(fcm_options = WebpushFCMOptions(link= g_v('base:url') + ("" if not len(urls) else urls[-1]) )),
                    apns = APNSConfig(payload = APNSPayload(aps = Aps(category = "GENERAL"))) """
        except Exception as e :
            now = timezone.now()
            p = PerfectLovDetails.objects.create(key = f'reportof:{now.year}-{now.month}-{now.day}::{now.hour}-{now.minute}-{now.second}', value = e)
            print(e)
    else :
        async_to_sync(channel_layer.group_send)(instance.room.slug, {
                'type' : 'messsage_update',
                'result' : [instance.step, instance.pk, instance.get_reply()]
        })

@receiver(post_save, sender = PerfectLovDetails)
def send_lancher(sender, instance : PerfectLovDetails, **kwargs):
    channel_layer = get_channel_layer()
    if 'anonym:off:room:' in instance.key :
        room = RoomMatch.objects.get(pk = int(instance.key.split(':')[-1]))
        if not instance.value : return 
        val = json.loads(instance.value)
        if len(val) < 2 :
            async_to_sync(channel_layer.group_send)(room.slug, {
                'type' : 'offnonym',
                'result' : { 'room' : room.slug, 'val' : val}
            })
        else :
            room.is_proposed = False
            room.anonymous_obj = None
            room.save()
            async_to_sync(channel_layer.group_send)(room.slug, {
                'type' : 'anonym_on',
                'result' : room.slug
            })
            instance.delete()
        
    if 'launcher:' in instance.key  :
        launcher = json.loads(instance.value)
        room = RoomMatch.objects.get(pk = launcher['id'])
        if not launcher['validator'] :
            async_to_sync(channel_layer.group_send)(room.slug, {
                'type' : 'launcher_send',
                'result' : launcher
            })
        else :
            if launcher['validator'] < 0 :
                instance.delete()
                async_to_sync(channel_layer.group_send)(room.slug, {
                    'type' : 'refuse_la',
                    'result' : launcher
                })
            elif launcher['validator'] > 0 :
                new_ = room.next_niveau()
                async_to_sync(channel_layer.group_send)(room.slug, {
                    'type' : 'new_niveau',
                    'result' : new_,
                    'other' : room.slug
                })

def get_notif_title(typ : str) :
    if typ == 'delete_room' :
        return "Match supprimé"
    elif typ == "expired_abon" :
        return "Ticket expiré"
    elif typ == "new_like" :
        return "De nouveaux likes"
    elif typ == "new_match" :
        return "Nouveau Match"
    elif typ == "new_abon" :
        return "Nouveau ticket activé"
    else :
        return "Notification"
@receiver(post_save, sender=Notif)
def send_push_notif( sender, instance : Notif, created, **kwargs ) :
    if created :
        if not instance.urls : 
            return None
        channel_layer = get_channel_layer()
        try :
            async_to_sync(channel_layer.group_send)(f"{instance.user.pk}m{instance.user.pk}", {
                'type' : 'new_notif',
                'result' : NotifSerializer(instance).data
            })
            devices = FCMDevice.objects.filter(user = instance.user)
            for device in devices :
                if not instance.urls : 
                    return None
                urls = json.loads(instance.urls)
                device.send_message(
                        message = FCMMess(notification=Notification(title=get_notif_title(instance.typ), body= instance.text, image=instance.get_photo() if instance.photo else None)
                        )
                )
        except Exception as e :
            now = timezone.now()
            p = PerfectLovDetails.objects.create(key = f'reportof:{now.year}-{now.month}-{now.day}::{now.hour}-{now.minute}-{now.second}', value = e)
            print(e)
def cred_for_interest(user : User, me : User) :
    my_cats = [
        c.pk for c in me.cats.all()
    ]
    return len([
        c.pk for c in user.cats.all() if c.pk in my_cats
    ])

def get_random_interest(user : User, me : User) :
    my_cats = [
        c.pk for c in me.cats.all()
    ]

    return random.choice([
        c for c in user.cats.all() if c.pk in my_cats
    ])


def cred_for_astro(user: User, me : User) :
    my_sign = me.get_sign()
    my_compat = COMPATIBILITY_ASTRO[my_sign]
    y_sign = user.get_sign()
    return my_compat[y_sign] if y_sign in list(my_compat.keys()) else 0

def get_the_match(user : User, me : User) :
    chs = ['i','i','i','i','i', 'a', 'a']
    ch = random.choice(chs)
    for i in [1,2] :
        cred = (cred_for_interest if ch == 'i' else cred_for_astro)(user, me)
        if cred :
            return ch
        else :
            ch = 'i' if ch == 'a' else 'i'
    return 'nada'

def can_match(user : User) :
    now = timezone.now()
    rest = user.rooms.all().filter(is_categorized = True).filter(created_at__lt = now, created_at__gt = (now - timezone.timedelta(days=10)))
    return rest.count() < 5

def search_match(**kwargs) :
    if kwargs['action'] == 'post_add' and kwargs['reverse'] :
        pks = list(kwargs['pk_set'])
        target = User.objects.get(pk = pks[0])
        user = kwargs['instance']
        if RoomMatch.objects.filter(slug = room_slug(user, target)).exists() :
            return
        if not (can_match(target) and can_match(user)) :
            return None
        choic = get_the_match(target, user)
        channel_layer = get_channel_layer()
        print(choic)
        if choic != 'nada' :
            if not (target.get_profil() and user.get_profil()) :
                return
            task = Taches.objects.filter(niveau = 0).first()
            niv = Niveau.objects.create(cur_task = task.pk)
            niv.taches.add(task)
            room_match = RoomMatch.objects.get_or_create(slug = room_slug(user, target))[0]
            room_match.niveau = niv
            room_match.is_categorized = True
            room_match.why = g_v(f"why:{choic}") if choic != 'i' else g_v(f"why:{choic}").format(get_random_interest(target, user).name)
            room_match.save()
            room_match.users.add(user)
            room_match.users.add(target)
            for use in room_match.users.all() :
                async_to_sync(channel_layer.group_send)(f"{use.pk}m{use.pk}", {
                    'type' : 'new_room',
                    'result' : RoomSerializer(room_match).data
                })
                notif = Notif.objects.create(typ = 'new_match', text = g_v('new:match:notif').format(use.prenom, room_match.why.lower()), photo = use.get_profil(), user  = the_other(room_match, use), urls = json.dumps([f"/profil/{use.pk}", f"/room/{room_match.slug}"]))

def get_channel_store(userId) :
    if not PerfectLovDetails.objects.filter(key = 'channel_store:' + str(userId)).exists() :
        PerfectLovDetails.objects.create(key = 'channel_store:' + str(userId), value = json.dumps([]))
    return json.loads(PerfectLovDetails.objects.get(key = 'channel_store:' + str(userId)).value)

def set_channel_store(userId, vals) :
    dets = PerfectLovDetails.objects.get(key = 'channel_store:' + str(userId))
    dets.value = json.dumps(vals)
    dets.save()

""" 
@receiver(m2m_changed, sender = User.likes.through)
def set_match_for_me(sender, **kwargs) :

    if kwargs['action'] == 'post_add' and kwargs['reverse'] :
        pks = list(kwargs['pk_set'])
        target = User.objects.get(pk = pks[0])
        user = kwargs['instance']
        print('can_match ', can_match(target) and can_match(user))
        if not (can_match(target) and can_match(user)) :
            return None
        choic = get_the_match(target, user)
        channel_layer = get_channel_layer()
        print(choic)
        if choic != 'nada' :
            if not (target.get_profil() and user.get_profil()) :
                return
            task = Taches.objects.filter(niveau = 0).first()
            niv = Niveau.objects.create(cur_task = task.pk)
            niv.taches.add(task)
            room_match = RoomMatch.objects.get_or_create(slug = room_slug(user, target))[0]
            room_match.niveau = niv
            room_match.is_proposed = True
            room_match.why = g_v(f"why:{choic}") if choic != 'i' else g_v(f"why:{choic}").format(get_random_interest(target, user).name)
            room_match.save()
            room_match.users.add(user)
            room_match.users.add(target)
            for use in room_match.users.all() :
                async_to_sync(channel_layer.group_send)(f"{use.pk}m{use.pk}", {
                    'type' : 'new_room',
                    'result' : RoomSerializer(room_match).data
                })
                notif = Notif.objects.create(typ = 'new_match', text = g_v('new:match:notif').format(use.prenom, room_match.why.lower()), photo = use.get_profil(), user  = the_other(room_match, use), urls = json.dumps([f"/profil/{use.pk}", f"/room/{room_match.slug}"]))

 """


""" @receiver(post_save, sender = User)
def send_online(sender, instance : User, **kwargs):
    print("user => ",instance) """
