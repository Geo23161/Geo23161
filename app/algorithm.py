from app.models import *
from django.utils import timezone
from django.db.models import Q
from random import randint, choice
from django.db.models import Count
import random

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
        #set_love()
        pass
    except Exception as e :
        log['set_love'] = e
    
    try :
        #set_match()
        pass
    except Exception as e :
        log["set_macth"] = e 
    return log

def deactivate_anonymous() :
    for room in RoomMatch.objects.filter(is_proposed = True) :
        room.is_proposed = False
        room.save()
    PerfectLovDetails.objects.get_or_create(key="anonym:general:off", value = timezone.now().isoformat())
    
def get_possibles_users(user : User, r_excep = [] ) :
    excludes = [user.pk]
    for room in user.rooms.all() :
        if not (room.users.count() > 1) :
            continue
        excludes.append(the_other(room, user).pk)
    res = User.objects.exclude(pk__in = excludes + r_excep).exclude(birth = None)
    return res if IS_DEV else res.exclude(sex = user.sex)

def get_profils_by_me_v2(user : User, ex_excepts : list[int], excep : list[int]) :
    users = get_possibles_users(user, excep + ex_excepts)

def get_rooms(user : User) :
    return [
        the_other(room, user).pk for room in user.rooms.all()
    ]



def get_profils_by_me(user : User, excep : list[int]) :
    ex_excepts = [ pk for pk in user.get_excepts() if not pk in excep]
    """if not user.rooms.all().count() :
        find_prevision(user, excep)"""
    poss = get_possibles_users(user, excep + ex_excepts)
    likes = user.like.all().intersection(poss).order_by('?')[:random.randint(0, 2)]
    hazards = [ u  for u in poss.exclude(pk__in = [p.pk for p in likes]).order_by('-created_at')[:50]]
    random.shuffle(hazards)
    hazards = hazards[:random.randint(1, int(DEFAULT_NUMBER/2))]
    if Prevision.objects.filter(user = user, status = 'pending').exists() : likes = User.objects.filter(pk = 0)
    stars = poss.exclude(pk__in = [l.pk for l in likes] + [u.pk for u in hazards]).annotate(likes__count = Count('likes')).order_by('-likes__count')[:DEFAULT_NUMBER - ( likes.count() + len( hazards))]
    
    finals =[
                u for u in likes if u.get_profil()
            ] + [
                u for u in stars if u.get_profil()
            ] + [
                u for u in hazards if u.get_profil()
            ]
    rooms = get_rooms(user)
    last = [ pk for pk in ex_excepts if not pk in rooms ]
    random.shuffle(last)
    if (len(finals) < DEFAULT_NUMBER) :
        finals =finals + [
                User.objects.get(pk = pk) for pk in last[:DEFAULT_NUMBER - len(finals)] if User.objects.filter(pk = pk).exists()
            ]
    random.shuffle(finals)
    return finals, poss.exclude(pk__in = [l.pk for l in finals] ).exclude(mood = user.mood).annotate(likes__count = Count('likes')).order_by('-likes__count')

def the_other(room, user) :
    return room.users.all().exclude(pk = user.pk).first() if room.users.count() > 1 else user

def check_all_matches() :
    now = timezone.now()
    rooms = RoomMatch.objects.all()
    for room in rooms :
        last_message = room.messages.all().order_by('-created_at').first() if room.messages.all().count() else None
        if last_message :
            if (now - last_message.created_at) > timezone.timedelta(days=4) :
                
                PerfectLovDetails.objects.create(key = 'del:room:' + str(room.pk), value = room.slug)
                room.delete()
                if room.groups.count() :
                    for gr in room.groups.all() :
                        for user in room.users.all().intersection(gr.users.all()) :
                            pass
                            #Notif.objects.create(typ = 'delete_room', text = g_v('notif:delete:groom').format(gr.get_oth_name(user)), photo = gr.creator.get_profil(), user = user )
                else :
                    for user in room.users.all() :
                        Notif.objects.create(typ = 'delete_room', text = g_v('notif:delete:room').format(the_other(room, user).prenom), photo = the_other(room, user).get_profil(), user = user )
    
            

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

def find_anonyms(user : User) :
    i_likes = user.like.all().exclude(pk__in = get_rooms(user))
    like_me =  user.likes.all().exclude(pk__in = get_rooms(user))
    astro = find_by_astro(user)
    inter = find_by_interests(user)
    def build_coommon(target : User) :
        commons = []
        astroed =  target in [u['user'].pk for u in astro]
        interested = [u for u in inter if u['user'].pk == target.pk][0]['cred'] if target in [u for u in inter] else []
        
        commons.append("L'un de vous a kiffé le profil de l'autre")
        if astroed :
            commons.append("Vos signes astrologiques sont compatibles")
        if len(interested) :
            commons.append(f"Vous êtes tous deux passionnés par {', '.join(interested[:3])+ ('...' if len(interested) > 3 else '.')}")
        return commons
    poss = like_me.union(i_likes)
    common_inter = poss.union(User.objects.filter(pk__in=[u['user'].pk for u in inter]))
    common_astro = poss.union(User.objects.filter(pk__in=[u['user'].pk for u in astro]))
    common_inter_astro = common_inter.intersection(common_astro)
    if common_inter_astro.count() :
        for target in common_inter_astro :
            if not target.anonym_out() :
                return target, build_coommon(target)
        
    if common_inter.count() :
        for target in common_inter :
            if not target.anonym_out() :
                return target, build_coommon(target)
            
    if common_astro.count() :
        for target in common_astro :
            if not target.anonym_out() :
                return target, build_coommon(target)
    """ if poss.count() :
        for target in common_astro :
            if not target.anonym_out() :
                return target, build_coommon(target) """
    return None, []
    
def set_anonyms(user : User) :
    if user.rooms.all().filter(created_at__gt = timezone.now() - timezone.timedelta(hours = 22), created_at__lt = timezone.now(), is_proposed = True).count() :
        return
        
    count = user.rooms.filter(is_proposed = True).count()
    anonym_conv = json.loads(g_v('anonym:conv'))
    if user.cur_abn :
        abn = user.cur_abn.get_typ()['name']
    else :
        abn = 'free'
    if count < anonym_conv[abn] :
        for i in range(anonym_conv[abn] - count) :
            target, commons = find_anonyms(user)
            if not target :
                break
            task = Taches.objects.filter(niveau = 0).first()
            niv = Niveau.objects.create(cur_task = task.pk)
            niv.taches.add(task)
            room_match = RoomMatch.objects.get_or_create(slug = room_slug(user, target))[0]
            room_match.niveau = niv
            room_match.is_proposed = True
            room_match.anonymous_obj = json.dumps({
                'commons' : commons,
                'has_seen' : False
            })
            room_match.save()
            room_match.users.add(user)
            room_match.users.add(target)
            channel_layer = get_channel_layer()
            for use in room_match.users.all() :
                async_to_sync(channel_layer.group_send)(f"{use.pk}m{use.pk}", {
                    'type' : 'new_room',
                    'result' : RoomSerializer(room_match).data
                })
                notif = Notif.objects.create(typ = 'new_anonym', text = "Vous avez une nouvelle proposition de discussion anonyme. Découvrez vos points communs.", photo = use.get_profil(), user  = the_other(room_match, user=use), urls = json.dumps([f"/af/{room_match.pk}"]))
            user.set_history(target.pk)
            target.set_history(user.pk)

            return True
    else :
        return False

def est_entre_vendredi_lundi(datetime_obj):
    if IS_DEV : return True
    # Récupérer le jour de la semaine (0 pour lundi, 6 pour dimanche)
    jour_semaine = datetime_obj.weekday()

    # Récupérer l'heure actuelle
    heure_actuelle = datetime_obj.hour

    # Vérifier si le jour de la semaine est vendredi (4) et l'heure est après 17h
    # ou si le jour de la semaine est samedi (5) ou dimanche (6)
    if (jour_semaine == 4 and heure_actuelle >= 17) or (5 <= jour_semaine <= 6):
        return True
    elif jour_semaine == 0 and heure_actuelle < 0:
        # Si c'est lundi et que l'heure est avant minuit
        return True
    return False

def get_emergency(user : User) :
    users = []
    anonym_conv = json.loads(g_v('anonym:conv'))
    for us in get_possibles_users(user) :
        if us.cur_abn :
            abn = us.cur_abn.get_typ()['name']
        else :
            abn = 'free'
        cats_com = us.cats.all().intersection(user.cats.all())
        if us.rooms.filter(is_proposed = True).count() < anonym_conv[abn] or  cats_com.count() :
            users.append(us)
    all_users = User.objects.filter(pk__in = [u.pk for u in users]).annotate(likes__count = Count('likes')).order_by('-likes__count')
    return all_users


def find_proposed(group : UserGroup, is_first = False) :
    excepts = [g.pk for g in group.proposeds.all()] + [g.pk for g in group.rooms.all()] + [group.pk]
    choice = UserGroup.objects.exclude(pk__in = excepts).exclude(creator__sex = group.creator.sex).order_by('?').first()
    return choice

def find_prevision(user : User, excep : list[int]) :
    
    if Prevision.objects.filter( created_at__lt = timezone.now() , created_at__gt = timezone.now() - timezone.timedelta(days = 1), user = user ).exists() :
        return
    ex_excepts = [ pk for pk in user.get_excepts() if not pk in excep]
    poss = get_possibles_users(user, excep + ex_excepts )
    if not ( user.likes.all().intersection(poss).count()) :
        if user.rooms.filter(created_at__gt = timezone.now() - timezone.timedelta(days = 6), created_at__lt = timezone.now(), is_proposed = False).count() :
            return
        compats = find_by_interests(user) + find_by_astro(user)
        all_poss = [ c['user'] for c in compats if (not c['user'].pk in excep ) and c['user'].rooms.all().filter(created_at__gt = timezone.now() - timezone.timedelta(days = 6), created_at__lt = timezone.now(), is_proposed = False).count() < 4 and not(not c['user'].get_profil()) ]
        if not len(all_poss) :
            all_poss = [ u for u in poss if not u.rooms.all().filter(created_at__gt = timezone.now() - timezone.timedelta(days = 6), created_at__lt = timezone.now(), is_proposed = False).count() ]
        print('thiis ', all_poss)
        if len(all_poss) :
            choice = random.choice(all_poss)
            prev = Prevision.objects.create(user = user, text = g_v('prev:sem:match').format(str(3*DEFAULT_NUMBER)), target = choice, swipes = 2 * DEFAULT_NUMBER )
    else :
        matches = user.likes.all().intersection(poss)
        if matches.count() :
            matches_interest = [ c['user'] for c in find_by_interests(user) if c['user'] in matches]
            typ = 'mutual'
            if len(matches_interest) :
                choice = random.choice(matches_interest)
                typ = 'inter'
            else :
                choice = random.choice(matches)
            times = 2
            prev = Prevision.objects.create(user = user, text = g_v(f'prev:{typ}:match').format(str((times + 1)*DEFAULT_NUMBER )), target = choice, swipes =  times* DEFAULT_NUMBER )
    
        
