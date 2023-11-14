from django.test import TestCase

# Create your tests here.

ABON_ALL = [
    {
        'typ' : 'free',
        'amount': 0,
        'keys' : [
            "Jusqu'à 05 swipes(personnes proposées) par jour",
            "Seulement une discussion par jour",
            "Profil non vérifié"
        ],
        'sub' : "Utilisez gratuitement l'application et profitez des fonctionnalité basiques."
    },
    {
        'typ' : 'silver',
        'amount': 200,
        'keys' : [
            "Vérification de profil",
            "Jusqu'à 03 discussiond par jour",
            "Jusqu'à 10 swipes(personnes proposées) par jour"
        ],
        'sub' : "Obtenez plus de visibilité en vérifiant votre profil grâce à l'offre silver"
    },
    {
        'typ' : 'silver_plus',
        'amount': 600,
        'keys' : [
            "Vérification de profil",
            "Jusqu'à 05 discussions par jour",
            "Jusqu'à 50 swipes(personnes proposées) par jour"
        ],
        'sub' : "Accordez-vous plus de chances grâce a l'offre Silver Plus."
    },
    {
        'typ' : 'golden',
        'amount': 1450,
        'keys' : [
            "Vérification de profil",
            "Jusqu'à 15 discussion par jour",
            "Voir ceux qui aiment mon profil",
            "Jusqu'à 150 swipes(personnes proposées) par jour"
        ],
        'sub' : "Prenez de l'avance sur les autres en activant l'offre Golden"
    },
    {
        'typ' : 'vip',
        'amount': 4000,
        'keys' : [
            "Vérification de profil",
            "Discussions illimitées chaque jour",
            "Swipes(personnes proposées) illimités chaque jour",
            "Voir ceux qui aiment mon profil",
            "Ecrire à n'importe qui même sans matcher"
        ],
        'sub' : "Passez en mode illimité avec l'offre VIP."
    }
]

FREE_TYP = {
    'name' : 'free',
    'limit' : 5,
    'level' : 0,
    'amount' : 0,
    'features' : []
}

SILVER_TYP = {
    'name' : 'silver',
    'limit' : 10,
    'level' : 1,
    'amount' : 200,
    'features' : []
}

SILVERplus_TYP = {
    'name' : 'silver_plus',
    'limit' : 50,
    'level' : 2,
    'amount' : 600,
    'features' : []
}

GOLDEN_TYP = {
    'name' : 'golden',
    'limit' : 150,
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
    'silver_plus' : 5,
    'golden' : 15,
    'vip' : 1000
}