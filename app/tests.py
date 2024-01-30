from django.test import TestCase
from .algorithm import *

# Create your tests here.

ABON_ALL = [
    {
        'typ' : 'free',
        'amount': 0,
        'keys' : [
            "Jusqu'à 30 swipes par jour",
            "Seulement une discussion par jour",
            "Profil non vérifié",
            "Une discussion anonyme par semaine",
        ],
        'sub' : "Profitez gratuitement des fonctionnalité basiques de Celibapps"
    },
    {
        'typ' : 'silver',
        'amount': 200,
        'keys' : [
            "Vérification de profil",
            "Jusqu'à 03 discussion par jour",
            "Jusqu'à 50 swipes par jour",
            "03 conversations anonymes chaque semaine",
        ],
        'sub' : "Obtenez plus de visibilité en vérifiant votre profil grâce au ticket silver"
    },
    {
        'typ' : 'silver_plus',
        'amount': 600,
        'keys' : [
            "Vérification de profil",
            "Jusqu'à 06 discussions par jour",
            "Jusqu'à 100 swipes par jour",
            "06 conversations anonymes chaque semaine",
        ],
        'sub' : "Accordez-vous plus de chances avec le ticket Silver Plus."
    },
    {
        'typ' : 'golden',
        'amount': 1450,
        'keys' : [
            "Vérification de profil",
            "Jusqu'à 15 discussion par jour",
            "Voir ceux qui aiment mon profil",
            "Jusqu'à 250 swipes par jour",
            "10 conversations anonymes chaque semaine",
        ],
        'sub' : "Prenez de l'avance sur les autres grâce au ticket Golden"
    },
    {
        'typ' : 'vip',
        'amount': 4000,
        'keys' : [
            "Vérification de profil",
            "Discussions illimitées chaque jour",
            "Swipes illimités chaque jour",
            "Voir ceux qui aiment mon profil",
            "Ecrire à n'importe qui même sans matcher",
            "Conversation anonyme illimitée chaque semaine",
        ],
        'sub' : "Passez en mode illimité avec le ticket VIP."
    }
]

FREE_TYP = {
    'name' : 'free',
    'limit' : 30,
    'level' : 0,
    'amount' : 0,
    'features' : []
}

SILVER_TYP = {
    'name' : 'silver',
    'limit' : 50,
    'level' : 1,
    'amount' : 200,
    'features' : []
}

SILVERplus_TYP = {
    'name' : 'silver_plus',
    'limit' : 100,
    'level' : 2,
    'amount' : 600,
    'features' : []
}

GOLDEN_TYP = {
    'name' : 'golden',
    'limit' : 250,
    'level' : 3,
    'amount' : 1450,
    'features' : ["likes_me"]
}

VIP_TYP = {
    'name' : 'vip',
    'limit' : 1000000,
    'level' : 3,
    'amount' : 4000,
    'features' : ["likes_me", "chat_all"]
}

DAY_DISCUSS = {
    'free' : 1,
    'silver' : 3,
    'silver_plus' : 6,
    'golden' : 15,
    'vip' : 1000
}

ANONYM_CONV = {
    'free' : 1,
    'silver' : 3,
    'silver_plus' : 6,
    'golden' : 10,
    'vip' : 50
}

GS_LIMITS = {
    'free' : {
        'swipe' : 3,
        'discuss' : 1
    },
    'silver' : {
        'swipe' : 8,
        'discuss' : 3
    },
    'silver_plus' : {
        'swipe' : 18,
        'discuss' : 8
    },
    'golden' : {
        'swipe' : 50,
        'discuss' : 15
    },
    'vip' : {
        'swipe' : 100,
        'discuss' : 50
    }
}

def test_anonym(email) :
    u = User.objects.get(email__icontains = email)
    set_anonyms(u)

"{0} partage le même mood que vous: {1}. Ecrivez-lui"
