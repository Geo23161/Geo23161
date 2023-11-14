from app.models import *
from django.utils import timezone
from django.db.models import Q
from random import randint, choice
from django.db.models import Count

def daily_tasks() :
    log = {
        'check_match' : "",
        "check_abon" : "",
        "set_macth" : "",
        "set_love" : ""
    }
    try :
        check_all_matches()
    except Exception as e :
        log['check_match'] = e
    try :
        check_abon()
    except Exception as e :
        log['check_abon'] = e
    try :
        set_love()
    except Exception as e :
        log['set_love'] = e
    
    try :
        #set_match()
        pass
    except Exception as e :
        log["set_macth"] = e 
    return log
    
def get_possibles_users(user : User, r_excep = [] ) :
    excludes = [user.pk]
    for room in user.rooms.all() :
        excludes.append(the_other(room, user).pk)
    res = User.objects.exclude(pk__in = excludes + r_excep)
    return res if IS_DEV else res.exclude(sex = user.sex)

def get_profils_by_me_v2(user : User, ex_excepts : list[int], excep : list[int]) :
    users = get_possibles_users(user, excep + ex_excepts)

def get_rooms(user : User) :
    return [
        the_other(room, user).pk for room in user.rooms.all()
    ]


def get_profils_by_me(user : User, excep : list[int]) :
    ex_excepts = [ pk for pk in user.get_excepts() if not pk in excep]
    poss = get_possibles_users(user, excep + ex_excepts)
    likes = user.like.all().intersection(poss).order_by('?')[:int(DEFAULT_NUMBER/2)]
    stars = poss.exclude(pk__in = [l.pk for l in likes]).annotate(likes__count = Count('likes')).order_by('-likes__count')[:DEFAULT_NUMBER - len(likes)]
    finals = [
        u for u in likes
    ] + [
        u for u in stars
    ]
    rooms = get_rooms(user)
    last = [ pk for pk in ex_excepts if not pk in rooms ]
    random.shuffle(last)
    if (len(finals) < DEFAULT_NUMBER) : 
        finals = finals + [
            User.objects.get(pk = pk) for pk in last[:DEFAULT_NUMBER - len(finals)]
        ]
    random.shuffle(finals)
    return finals

def the_other(room, user) :
    return room.users.all().exclude(pk = user.pk).first()

def check_all_matches() :
    now = timezone.now()
    rooms = RoomMatch.objects.all()
    for room in rooms :
        last_message = room.messages.all().order_by('-created_at').first() if room.messages.all().count() else None
        if last_message :
            if (now - last_message.created_at) > timezone.timedelta(days=14) :
                for user in room.users.all() :
                    Notif.objects.create(typ = 'delete_room', text = g_v('notif:delete:room').format(the_other(room, user).prenom), photo = the_other(room, user).get_profil(), user = user )
                PerfectLovDetails.objects.create(key = 'del:room:' + str(room.pk), value = room.slug)
                room.delete()

def check_abon() :
    now = timezone.now()
    for user in User.objects.exclude(cur_abn = None) :
        print(now - user.cur_abn.created_at > timezone.timedelta(days=32))
        if now - user.cur_abn.created_at > timezone.timedelta(days=32) and user.cur_abn.status != 'free' :
            abn = Abon.objects.create(typ = g_v('typ:' + 'free'), debut = timezone.now(), user = user, status = 'free')
            verifs = Verif.objects.filter(user = user)
            user.cur_abn = abn
            if True :
                essentials = user.get_essentials()
                now = timezone.now()
                day_string = f"{now.year}:{now.month}:{now.day}"
                essentials["all_swipe"][day_string] = 0
                user.essentials = json.dumps(essentials)
            user.save()
            Notif.objects.create(typ = 'expired_abon', text=g_v('notif:expired:abon'), user = user, urls = json.dumps(["/param?target=activ_abn"]))


def set_love() :
    now = timezone.now()
    for user in User.objects.all() :
        matches = [
            the_other(r, user).pk for r in user.rooms.all()
        ]
        if user.last_like_notif :
            is_good = now - user.last_like_notif > timezone.timedelta(days=7)

            if (is_good or (not user.last_like_notif)) and user.likes.exclude(pk__in = matches).count() > 0 :
                Notif.objects.create(typ = 'new_like', text = g_v('notif:new:like').format(user.get_likes_prenoms(), "ont" if len(user.get_txt_likes()) > 1 else "a" ) , user = user)


def set_match() :
    now = timezone.now()
    for user in User.objects.all() :
        rest = user.rooms.all().filter(created_at__lt = now, created_at__gt = (now - timezone.timedelta(days=7)))
        if rest.count() < 1 :
            set_match_one(user, rest)

def set_match_one(user : User, rest) :
    m_interests = find_by_interests(user)
    m_astro = find_by_astro(user) if user.birth else []
    m_random = find_randomly(user)
    dic = {
        'i' : m_interests,
        'a' : m_astro,
        'r' : m_random
    }
    l = ['i','i','i','i','i', 'a', 'a']
    conti = True
    done= []
    choic = ''

    times = 1 - rest.count()
    channel_layer = get_channel_layer()
    for i in range(0, times) :
        choic = choice(l)
        if len(dic[choic]) == 0 :
            choic = "i" if choic == 'a' else  'a'
            if len(dic[choic]) == 0 :
                has_hasard= rest.filter(why__icontains="hasard").exists() 
                if has_hasard :
                    return
                else :
                    choic = 'r'
        if choic != "" :
            my_ma = dic[choic][0]
            dic[choic] = [
                d for d in dic[choic] if d['user'].pk != my_ma['user'].pk
            ]
            target = my_ma['user']
            if not (target.get_profil() and user.get_profil()) :
                return
            task = Taches.objects.filter(niveau = 0).first()
            niv = Niveau.objects.create(cur_task = task.pk)
            niv.taches.add(task)
            room_match = RoomMatch.objects.get_or_create(slug = room_slug(user, target))[0]
            room_match.niveau = niv
            room_match.is_proposed = True
            room_match.why = g_v(f"why:{choic}") if choic != 'i' else g_v(f"why:{choic}").format(choice(my_ma['cred']).name)
            room_match.save()
            room_match.users.add(user)
            room_match.users.add(target)
            for use in room_match.users.all() :
                async_to_sync(channel_layer.group_send)(f"{use.pk}m{use.pk}", {
                    'type' : 'new_room',
                    'result' : RoomSerializer(room_match).data
                })
                notif = Notif.objects.create(typ = 'new_match', text = g_v('new:match:notif').format(use.prenom, room_match.why.lower()), photo = use.get_profil(), user  = the_other(room_match, use), urls = json.dumps([f"/profil/{use.pk}", f"/room/{room_match.slug}"]))



def find_by_interests(user : User) :
    listes = []
    mycats = [
        c.pk for c in user.cats.all()
    ]
    for us in get_possibles_users(user=user) :
        cred = us.cats.filter(pk__in = mycats).count()
        if cred : 
            listes.append({
                'user' : us,
                'cred' : [
                    c for c in us.cats.filter(pk__in = mycats)
                ]
            })
    listes.sort(key= lambda e : len(e["cred"]), reverse=True)
    return listes

def find_by_astro(user : User) :
    compatibilites = {
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
    listes = []
    for us in get_possibles_users(user=user) :
        my_compat = compatibilites[user.get_sign()]
        if us.birth :
            if us.get_sign() in my_compat.keys() :
                listes.append({
                    'user' : us,
                    'cred' : my_compat[us.get_sign()]
                })
    listes.sort(key= lambda e : e['cred'], reverse= True)
    return listes

def find_randomly(user : User) :
    listes = [
        {'user' : usr, 'cred' : randint(1, 1000) } for usr in get_possibles_users(user=user)
    ]
    listes.sort(key= lambda e : e['cred'], reverse= True)
    return listes

def check_special(user : User) :
    can_benef = True
    state = 'vip'
    if user.get_status() in ['golden', "vip"] :
        can_benef = False
    for i in range(0, 3) :
        my_rooms = [
            r.pk for r in user.rooms.all()
        ]
        messages = Message.objects.filter(room__pk__in = my_rooms, created_at__gt = (timezone.now() - timezone.timedelta(days=7 + (7*i))), created_at__lt = timezone.now() - timezone.timedelta(days=7 * i))
        rooms = [
            m.room.pk for m in messages
        ]
        rooms = [
            r for r in RoomMatch.objects.filter(pk__in = rooms) if the_other(r, user).get_status() in ['golden', 'vip']
        ]
        if len(rooms) < 3 :
            can_benef = False
        else :
            for r in rooms :
                if the_other(r, user).get_status() == 'golden' :
                    state = 'golden'
    if can_benef :
        return True, state
    else :
        return False, ''


def set_special_abo(user : User) :
    can_benef, state = check_special(user)
    if can_benef :
        abn = Abon.objects.create(typ = g_v('typ:' + state), debut = timezone.now(), user = user, status = state)
        verifs = Verif.objects.filter(user = user)
        user.cur_abn = abn
        if True :
            essentials = user.get_essentials()
            now = timezone.now()
            day_string = f"{now.year}:{now.month}:{now.day}"
            essentials["all_swipe"][day_string] = 0
            user.essentials = json.dumps(essentials)
        user.save()
        Notif.objects.create(typ = 'expired_abon', text=g_v('abon:special'), user = user, urls = json.dumps(["/param?target=activ_abn"]))

def set_all_user_spe() :
    users = User.objects.all()
    for user in users :
        set_special_abo(user)