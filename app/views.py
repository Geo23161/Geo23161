from django.shortcuts import render
from .models import *
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
import datetime 
from haversine import haversine, Unit
import threading
from rest_framework.permissions import IsAuthenticated
import random
import requests
from .core import Kkiapay
from django.utils import timezone
from django.db import transaction
from .algorithm import daily_tasks, set_match_one, get_possibles_users, get_profils_by_me, set_anonyms, est_entre_vendredi_lundi, get_emergency, find_proposed, find_prevision
from django.http import JsonResponse
from random import choice
from dateutil import parser
from django.db.models import Count
import string
from .qosic import launch_payment as l_p, get_status, asyncio
import time

def generate_random_string(length=8):
    characters = string.ascii_letters + string.digits
    random_string = ''.join(random.choice(characters) for _ in range(length))
    if UserGroup.objects.filter(code = random_string).exists() :
        return generate_random_string()
    else :
        return random_string

DEFAULT_ESSENTIALS = {
    'all_swipe' : {},
    'seen_tofs' : [],
    'already_seens' : []
}
    


def the_other(room, user) :
    return room.users.all().exclude(pk = user.pk).first()

def send_by_thread(func):
    proc = threading.Thread(target=func)
    proc.start()

def launch_payment(abn, sim, numero, user) :
    qos = json.dumps(g_v('qos:global'))
    resp = requests.post(qos['full_uri'], {
        'msisdn' : numero,
        'amount' : abn['amount'],
        'firstname' : user.prenom,
        'transref' : abn['ref']
    })

def getKkiapay():
    return Kkiapay(g_v('kkiapay0'+ (":sand" if IS_DEV else "")), g_v('kkiapay1'+ (":sand" if IS_DEV else "")), g_v('kkiapay2'+ (":sand" if IS_DEV else "")), sandbox= IS_DEV)
    


# Create your views here.

def set_distance(user : User) :
    dObj = DistanceObj.objects.get_or_create(user = user)[0]
    ls = []
    for u in User.objects.all().exclude(pk = user.pk) :
        try :
            dis = {
                'pk': u.pk,
                'dis' : haversine((u.get_quart()['lat'], u.get_quart()['lng']), (user.get_quart()['lat'], user.get_quart()['lng'])) if u.quart else 10000
            }
            
        except Exception as e :
            dis = {
                'pk' : u.pk,
                'dis' : 10000
            }
        if dis['dis'] < 500 :
            ls.append(dis)
    ls = sorted(ls, key= lambda e : e['dis'])
    dObj.distances = json.dumps(ls)
    dObj.save()

def add_user_distance(user : User) :
    users = User.objects.all().exclude(pk = user.pk)
    dObj = DistanceObj.objects.get_or_create(user = user)[0]
    for us in users :
        distance = haversine((us.get_quart()['lat'], us.get_quart()['lng']), (user.get_quart()['lat'], user.get_quart()['lng']))
        if dObj.distances :
            dObj.distances += f"/{us.pk}:{distance}"
        else : dObj.distances = f"/{us.pk}:{distance}"
    dObj.save()

""" def get_profils_by_me(user : User, excepts : list[int]) :
    users = [ us.pk for us in user.likes.all().order_by('?') if us.pk not in excepts]
    other_users = [us.pk for us in User.objects.all().exclude(pk__in = (users + excepts))]
    random.shuffle(users)
    final_likes = users[:int(DEFAULT_NUMBER/2)]
    finals = final_likes + other_users[:(DEFAULT_NUMBER - len(final_likes))]
    return User.objects.filter(pk__in = finals) """

def get_profils_by_proximity(user : User, excepts : list[int]) :
    dObj = DistanceObj.objects.get_or_create(user = user)[0]
    try :
        dis_lis = json.loads(dObj.distances)
    except :
        dis_lis = []
    uss = []
    for lis in dis_lis :
        if lis['pk'] not in excepts :
            uss.append(User.objects.get(pk = lis['pk']))
    return uss[:DEFAULT_NUMBER]


@api_view(['POST'])
def submit_img(request) :
    file = request.FILES.get('file')
    photo = Photos.objects.create(name = 'anonymous', file= file, is_profil = False)
    if request.user.is_authenticated :
        photo.user = request.user
        photo.save()
    def set_color_dom() :
        photo.set_color()
        if not photo.color :
            photo.set_color()
    send_by_thread(set_color_dom)
    return Response({
        'done' : True,
        'result' : {
            'pk' : photo.pk,
            'url' : photo.get_picture(),
            'obj' : PhotoSerializer(photo).data
        }
    })

@api_view(['POST'])
def register_user(request) :
    prenom = request.data.get('prenom')
    email = request.data.get('email')

    if User.objects.filter(email = email).exists() :
        return Response({
            'done': False,
            'reason': 'already'
        })

    password = request.data.get('password')
    sex = request.data.get('sex')
    birth = request.data.get('birth')
    img_pk = request.data.get('img_pk')
    searching = request.data.get('searching')
    quart = request.data.get('quart')
    pquart = json.loads(request.data.get('pquart'))
    cats = json.loads(request.data.get('cats'))
    if not img_pk :
        return Response({
            'done' : False,
        })

    user = User.objects.create_user(prenom = prenom, email = email, password=password, sex = sex, searching = searching, quart = quart)
    user.birth = datetime.datetime.strptime(birth, "%Y-%m-%dT%H:%M:%S")
    user.place = json.dumps(pquart)
    user.essentials = json.dumps(DEFAULT_ESSENTIALS)
    user.save()
    for cat in cats :
        user.cats.add(Cat.objects.get(pk = cat['id']))
    
    photo = Photos.objects.get(pk = img_pk)
    photo.user = user
    photo.is_profil= True
    photo.save()

    def add_to_user() :
        set_distance(user)
        #set__next(user, [])
        #set_match_one(user, RoomMatch.objects.none())
    send_by_thread(add_to_user)
    return Response({
        'done' : True,
        'result' : UserSerializer(user).data
    })

def set__next(user : User, excep : list[int]) :
    ex_excepts = user.get_excepts()
    profss = get_profils_by_me(user, ex_excepts, excep)[0]
    store = PerfectLovDetails.objects.get_or_create(key = f"next:for:{user.pk}")[0]
    store.value = json.dumps([
        u.pk for u in profss
    ])
    store.save()


def get__next(user : User, ex_excepts : list[int], excep : list[int]) :
    next_profs = PerfectLovDetails.objects.filter(key = f"next:for:{user.pk}")
    if not next_profs.exists()  :
        profs = get_profils_by_me(user, ex_excepts, excep)[0]
    else :
        profs = [ User.objects.get(pk = pk) for pk in json.loads(next_profs.first().value)]
    if not len(profs) :
        profs = [u for u in get_possibles_users(user, excep).order_by('?')[:DEFAULT_NUMBER]]
    return profs

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def get_profils(request, typ_rang) :
    excepts = json.loads(request.data.get('excepts'))
    excepts.append(request.user.pk)
    date_string = request.data.get('date_string')
    for u in User.objects.filter(birth = None) :
        excepts.append(u.pk)
    all_profs = get_profils_by_me(request.user, excepts)
    profils = all_profs[0] if typ_rang == 'for_you' else get_profils_by_proximity(user=request.user, excepts=excepts)
    if (request.user.rooms.filter(created_at__gt = timezone.now() - timezone.timedelta(days=10)).count() == 0) :
        emergs = get_emergency(request.user).exclude(pk__in=excepts)[:random.randint(1,3)]
        profils = list(emergs) + profils[:DEFAULT_NUMBER - len(emergs)]
        random.shuffle(profils)
    request.user.set_excepts([
        p.pk for p in profils
    ])
    datetime_obj = parser.parse(date_string)
    
    profs = UserProfilSerializer(profils, context = {'request' : request}, many = True).data
    plaisirs = [ p for p in profs if len([c for c in p['commons'] if c['id']]) or (p['reaction'] == request.user.mood) ]
    random.shuffle(plaisirs)
    iplaisirs = plaisirs[:random.randint(3,5)]
    profils = [ p for p in profils if not p.pk in [f['id'] for f in plaisirs]] + [ User.objects.get(pk = g['id']) for g in iplaisirs]
    if len(profils) < DEFAULT_NUMBER :
        profils = profils + list(all_profs[1][:DEFAULT_NUMBER - len(profils)])
    RESP = {
        'done' : True,
        'result' : UserProfilSerializer(profils, context = {'request' : request}, many = True).data,
        'other' : DEFAULT_NUMBER,
        'allowed' : est_entre_vendredi_lundi(datetime_obj),
        'mood' : request.user.get_mood()
    }
    if Prevision.objects.filter(user = request.user, status = 'pending').exists() :
        prev = Prevision.objects.filter(user = request.user, status = 'pending').first()
        if (timezone.now() - prev.created_at) > timezone.timedelta(days=1) :
            prev.delete()
            return 
        r_prev = json.loads(request.data.get('prev'))
        if not r_prev :
            r_prev = {
                'id' : prev.id,
                'target' : prev.target.pk,
                'text' : prev.text,
                'status' : prev.status,
                'actual_swipe' : prev.actual_swipe
            }
        
        if r_prev['id'] == prev.pk :
            print(r_prev['actual_swipe'] >= prev.swipes, "test")
            if r_prev['status'] == 'done' :
                prev.status = 'done'
                prev.save()
            elif r_prev['status'] == 'pending' and r_prev['actual_swipe'] <= (prev.swipes + DEFAULT_NUMBER) :
                nprofils = [ u for u in profils if u.pk != r_prev['target'] ] 
                oth = None
                print(len(nprofils) == len(profils))
                if len(nprofils) == len(profils) and len(nprofils) :
                    random.shuffle(nprofils)
                    oth = nprofils[-1]
                    profils = nprofils[:-1]
                else :
                    random.shuffle(nprofils)
                    profils = nprofils
                choice = random.randint(0, 1)
                print('choice', (bool(choice) or r_prev['actual_swipe']  > prev.swipes))
                if (bool(choice) or r_prev['actual_swipe']  > prev.swipes) :
                    profils.append(User.objects.get(pk = r_prev['target']))
                elif bool(oth) : profils.append(oth)
                prev.actual_swipe += DEFAULT_NUMBER
                prev.save()
            elif r_prev['actual_swipe'] > (prev.swipes + DEFAULT_NUMBER *2 + 1):
                prev.status = 'missed'
                prev.save()
        random.shuffle(profils)
        print([(p.pk, p.prenom) for p in profils])
        RESP['prev'] = {
            'id' : prev.id,
            'target' : prev.target.pk,
            'text' : prev.text,
            'status' : prev.status,
            'actual_swipe' : prev.actual_swipe
        }
        RESP['result'] = UserProfilSerializer(profils, context = {'request' : request}, many = True).data
    else :
        find_prevision(request.user, excepts + [p.pk for p in profils])
    return Response(RESP)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def get_likes_dis(request) :
    return Response({
        'done' : True,
        'result' : {
            'likes' : request.user.get_likes(),
            'dislikes' : request.user.get_dislikes()
        } 
    })

@api_view(['GET', 'HEAD'])
@permission_classes([IsAuthenticated])
def ping(request):
    return Response({'done': True})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user(request) :
    now = datetime.datetime.now()
    if not PerfectLovDetails.objects.filter(key = f"dis:{now.year}:{now.month}:{now.day}").exists() :
        def set_all_dis() :
            for user in User.objects.all() :
                if user.quart : 
                    set_distance(user)
        send_by_thread(set_all_dis)
    return Response({
        'done' : True,
        'result' : UserSerializer(request.user).data
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def delete_img(request) :
    pk = int(request.data.get('pk'))
    photo = Photos.objects.get(pk = pk)
    if(request.user == photo.user) : photo.delete()
    
    return Response({
        'done' : True
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def replace_profil(request) :
    file = request.FILES.get('file')
    profil = Photos.objects.get(user = request.user, is_profil = True)
    profil.file = file
    profil.save()
    PerfectLovDetails.objects.filter(key=f'bad:profil:{request.user.pk}').delete()
    return Response({
        'done' : True,
        'result' : UserSerializer(request.user).data
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_profile(request, pk) :
    seens = json.loads(request.user.seens_photos) if request.user.seens_photos else []
    user = User.objects.get(pk = pk)
    for photo in user.photos.all() :
        seens.append(photo.pk)
    User.objects.filter(pk = request.user.pk).update(seens_photos = json.dumps(seens))
    return Response({
        'done' : True,
        'result': UserProfilSerializer(user).data
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def get_mylikes(request) :
    excp = json.loads(request.data.get('excepts'))
    likes = request.user.likes.all().exclude(pk__in = excp)
    return Response({
        'done' : True,
        'result' : UserProfilSerializer(likes, many = True).data
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_new_photos(request) :
    matches = []
    try :
        seens = json.loads(request.user.seens_photos)
    except :
        seens = []
    for room in request.user.rooms.filter(is_proposed = False) :
        if not (room.users.count() > 1) :
            continue
        print(room.users.all())
        d = {
            'id' : 0,
            'new' : 0,
            'tots': 0
        }
        user = room.users.exclude(pk = request.user.pk).first()
        if user.get_picture() :
            d['id'] = user.pk
            photos = user.photos.all()
            d['tots'] = photos.count()
            d['new'] = photos.filter(is_profil = False).exclude(pk__in = seens).count()
            matches.append(d)
    return Response({
        'done' : True,
        'result' : matches
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def delete_room(request, pk) :
    room = RoomMatch.objects.filter(pk = pk)
    is_group = request.GET.get('is_group')
    if room.exists() :
        room = room.first()
        channel_layer = get_channel_layer()
        slug = room.slug
        prenom = request.user.prenom
        if not is_group :
            PerfectLovDetails.objects.create(key = 'del:room:' + str(room.pk), value = room.slug)
            if request.user in room.users.all() :
                room.delete()
        else :
            room.users.remove(request.user)
            if [u.pk for u in room.groups.all()[0].users.all() ] == [u.pk for u in room.users.all()] or [u.pk for u in room.groups.all()[-1].users.all() ] == [u.pk for u in room.users.all()] :
                room.delete()
                PerfectLovDetails.objects.create(key = 'del:room:' + str(room.pk), value = room.slug)
        async_to_sync(channel_layer.group_send)(slug, {
            'type' : 'rmvu_from_r',
            'result' : {
                'user' : request.user.pk,
                'slug' : slug,
                'prenom' : prenom
            },
        })
        if not request.user.is_online(minu = 1) :
            channel_store = get_channel_store(request.user.pk)
            channel_store.append({
                'slug' : slug,
                'payload' :   {
                    'type' : 'rmvu_from_r',
                    'result' : {
                        'user' : request.user.pk,
                        'slug' : slug,
                        'prenom' : prenom
                    },
                }
            })
            set_channel_store(request.user.pk, channel_store)

        
    return Response({
            'done' : True,
            'result' :0,
        })
    
    
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def next_niveau(request, pk) :
    room = RoomMatch.objects.get(pk = id)
    taches = room.niveau.taches.all().filter(level = room.niveau.level)
    tot = 0
    used = [ t.pk for t in room.niveau.taches.all()]
    for tache in taches :
        tot += tache.coef
    if tot < 100 :
        new_task = Taches.objects.filter(niveau = room.niveau.level).exclude(pk__in= used).order_by('?').first()
        if new_task :
            room.niveau.cur_task = new_task
            room.niveau.taches.add(new_task)
            room.niveau.save()
        else :
            tot += 100
    if tot >= 100 :
        room.niveau.level += 1
        room.niveau.save()
        room.niveau.help_dets = g_v(f'help:niv:{room.niveau.level}')
        new_task = Taches.objects.filter(niveau = room.niveau.level).exclude(pk__in= used).order_by('?').first()
        room.niveau.cur_task = new_task
        room.niveau.taches.add(new_task)
        room.niveau.save()
    return Response({
        'done' : True,
        'result' : NiveauSerializer(room.niveau).data
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_message(request) :
    typ = request.POST.get('typ')
    message = json.loads(request.POST.get('message'))
    blob = request.FILES.get('blob')
    preview = request.FILES.get('preview')
    state = request.POST.get('state')
    reply = message['get_reply'] if "get_reply" in message.keys() else None 
    can_cont = True
    channel_layer = get_channel_layer()
    
    """ if not can_cont :
        new_state = state_messag(message['get_room'], request.user)
        if new_state == 'on' : can_cont = True 
        else :
            slug = g_v('del:room:' + str(message['get_room'])) if new_state == 'deleted' else RoomMatch.objects.get(pk = message['get_room']).slug
            async_to_sync(channel_layer.group_send)( slug, {
                    'type' : 's_m',
                    'result' : {
                        'state' : new_state,
                        'target' : request.user.pk,
                        'old_pk' : message['old_pk']
                    }
            }) """
    if can_cont :
        
        room = RoomMatch.objects.filter(pk = message['get_room'])
        if room.exists() :
            room = room.first()
            if request.user in room.users.all() :
                if typ == 'img' :
                    img = Image.objects.create(name = f"img:{request.user.pk}", image = blob, details = json.dumps(message['image']['get_details']))
                    messag = Message.objects.create(room = room, image = img, user = message['user'], old_pk = message['old_pk'] )
                elif typ == 'aud' :
                    aud = Audio.objects.create(name = f"aud:{request.user.pk}", audio = blob, details = json.dumps(message['audio']['get_details']))
                    messag = Message.objects.create(room = room, audio = aud, user = message['user'], old_pk = message['old_pk'] )
                elif typ == 'vid' :
                    video = Video.objects.create(name = f"vid:{request.user.pk}", video = blob, details = json.dumps(message['video']['get_details']), image = preview)
                    
                    messag = Message.objects.create(room = room, video = video, user = message['user'], old_pk = message['old_pk'] )
                if reply :
                    message.reply = reply
                    message.save()
            #handle_mess_perm(message['get_room'], request.user, message['old_pk'])
        else :
            
            async_to_sync(channel_layer.group_send)( f"{request.user.pk}m{request.user.pk}", {
                    'type' : 's_m',
                    'result' : {
                        'state' : 'deleted',
                        'target' : request.user.pk,
                        'old_pk' : message['old_pk']
                    }
            })

        return Response({
            'done' : True,
        })
    return Response({
        'done' : False
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def delete_message(request, pk) :
    message = Message.objects.filter(user = request.user.pk, pk = pk)
    if message.exists() :
        
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(message.first().room.slug, {
                'type' : 'd_m',
                'result' : pk
        })
        dets, has_created = PerfectLovDetails.objects.get_or_create(key = f"{message.first().get_room()}:delete")
        dets.value = json.dumps(([] if not dets.value else json.loads(dets.value)) + [pk])
        dets.save()
        message.delete()
        return Response({
            'done' : True
        })
    return Response({
            'done' : False
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def set_info(request) :
    email = request.data.get('email')
    sex = request.data.get('sex')
    prenom = request.data.get('prenom')
    searching = json.loads(request.data.get('searching'))
    user = request.user
    user.email = email
    user.sex = sex
    user.prenom = prenom
    user.searching = json.dumps(searching)
    user.save()
    """ 
    User.objects.filter(pk = request.user.pk).update(email = email, sex = sex, prenom = prenom)
    """ 
    return Response({
        'done' : True,
        'result' : UserSerializer(request.user).data
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def set_password(request):
    newpass = request.data.get('newpass')
    oldpass = request.data.get('oldpass')
    user = User.objects.get(email = request.user.email)
    if not user.check_password(oldpass):
        return Response({
            'done': False,
        })
    else:
        user.set_password(newpass)
        user.save()
        user.save()
        user.save()
        print(User.objects.get(email = request.user.email).check_password(newpass), newpass, oldpass)
        return Response({
            'done': True
        })
    
@api_view(['GET'])
def get_cats(request) :
    return Response({
        'done' : True,
        'result' : CatSerializer(Cat.objects.all(), many = True).data
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def set_cats(request) :
    pks =  json.loads(request.data.get('pks'))
    for cat in request.user.cats.all() : request.user.cats.remove(cat)
    for pk in pks : request.user.cats.add(Cat.objects.get(pk = pk))

    return Response({
        'done' : True,
        'result' : UserSerializer(request.user).data
    })


@api_view(["GET"])
def search_place(rqt, name):
    req = requests.get(
        f'https://maps.googleapis.com/maps/api/place/textsearch/json?key=AIzaSyDNoBJJXRj_p5miy5gSPGazRa4Mr-95D18&query={name}')
    results = json.loads(req.content)['results']
    return Response({
        'done': True,
        'result': results
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def set_place(request) :
    place = json.loads(request.data.get('place'))
    request.user.place = json.dumps(place)
    request.user.save()
    return Response({
        'done' : True
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def set_verif(request) :
    if not request.user.cur_abn.get_typ()['level'] :
        return Response({
            'done' : False
        })
    piece = request.FILES.get('piece')
    verif = Verif.objects.get_or_create(user = request.user)[0]
    verif.status = 'pending'
    verif.piece = piece
    verif.save()
    command = choice(json.loads(g_v("verif:coms")))
    return Response({
        'done' : True,
        'result' : VerifSerializer(Verif.objects.get(user = request.user)).data,
        'other' : command
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_abons(request) :
    return Response({
        'done' : True,
        'result' : json.loads(g_v('abons:all')),
        'is_dev' : True if IS_DEV else False,
        'api': g_v('kkiapay0'+ (":sand" if IS_DEV else ""))
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def set_abon(request) :
    transactionId = request.data.get('transactionId')
    state = request.data.get('state')
    abons_all = json.loads(g_v('abons:all'))
    abon = [abon for abon in abons_all if state == abon['typ']][0]
    kkia = getKkiapay()
    user = request.user
    if kkia.verify_transaction(transaction_id=transactionId).status == "SUCCESS" or state == 'free':
        Notif.objects.create(typ = "new_abon", text = g_v('notif:new:abon').format(state), user = user, urls = json.dumps(["/param?target=cur_abn"]))
        abn = Abon.objects.create(typ = g_v('typ:' + abon['typ']), debut = timezone.now(), user = request.user, status = abon['typ'])
        verifs = Verif.objects.filter(user = request.user)
        if verifs.exists() and state != 'free' :
            verif = verifs.first()
            Abon.objects.filter(pk = abn.pk).update(verif = verif)
        user.cur_abn = abn
        aboned_before = Abon.objects.filter(user = request.user).exclude(pk = abn.pk).exists()
        if state != 'free' or not aboned_before :
            essentials = request.user.get_essentials()
            now = timezone.now()
            day_string = f"{now.year}:{now.month}:{now.day}"
            essentials["all_swipe"][day_string] = 0
            user.essentials = json.dumps(essentials)
        user.save()
        set_anonyms(user)
        return Response({
            'done' : True,
            'result' : UserSerializer(User.objects.get(pk = request.user.pk)).data,
        })
    else :
        return Response({
            'done' : False
        })
    
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_contact(request) :
    return Response({
        'done' : True,
        'result' : {
            'whatsapp' : g_v('contact:whatsapp'),
            'privacy' : g_v('privacy:link'),
        }
})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def only_verified(request) :
    us= request.user
    us.only_verified = not us.only_verified
    us.save()
    us.save()
    return Response({
        'done' : True,
        'result' : us.only_verified
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_room(request) :
    author = User.objects.get(pk = int(request.data.get('author')))
    patner = User.objects.get(pk = int(request.data.get('patner')))
    channel_layer = get_channel_layer()
    if author.pk == request.user.pk :
        if not RoomMatch.objects.filter(slug = room_slug(author, patner)).exists() :
            task = Taches.objects.filter(niveau = 0).first()
            niv = Niveau.objects.create(cur_task = task.pk)
            niv.taches.add(task)
            target = User.objects.get(pk = patner.pk)
            room_match = RoomMatch.objects.get_or_create(slug = room_slug(author, target))[0]
            room_match.niveau = niv
            room_match.why = f"{request.user.prenom} pense que vous pouvez matcher."
            room_match.save()
            room_match.users.add(author)
            room_match.users.add(target)
            for use in room_match.users.all() :
                async_to_sync(channel_layer.group_send)(f"{use.pk}m{use.pk}", {
                    'type' : 'new_room',
                    'result' : RoomSerializer(room_match).data
                })
                if use.pk != request.user.pk : notif = Notif.objects.create(typ = 'new_match', text = g_v('new:match:notif').format(use.prenom, room_match.why), photo = use.get_profil(), user  = the_other(room_match, user=use), urls = json.dumps([f"/profil/{use.pk}", f"/room/{room_match.slug}"]))
        else :
            return Response({
                'done' : False,
                'reason' : 'existed'
            })
    return Response({
        'done' : False,
        'reason' : 'unknown'
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_state(request) :
    usercode = UserCode.objects.filter(user = request.user)
    if usercode.exists() :
        usercode = usercode.first()
        return Response({
            'done' : True,
            'result' : {
                'state' : usercode.state,
                'reason' : usercode.reason
            }
        })
    return Response({
        'done' : False
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_code(request) :
    code = request.data.get('code')
    i_code = InvitCode.objects.filter(code = code)
    if i_code.exists() :
        i_code = i_code.first()
        if i_code.users.count() < i_code.quota :
            usercode = UserCode.objects.create(user = request.user, reason = f'Il manque {i_code.quota - (i_code.users.count() - 1)} personnes{ "s" if (i_code.quota - i_code.users.count() - 1 > 1) else "" } pour la validation du code.', code = i_code)
            if i_code.users.count() == i_code.quota :
                for userc in i_code.users.all() :
                    userc.state = 'done'
                    userc.save()
                    user = userc.user
                    state = i_code.for_abon
                    abn = Abon.objects.create(typ = g_v('typ:' + i_code.for_abon), debut = timezone.now(), user = user, status = i_code.for_abon)
                    
                    verifs = Verif.objects.filter(user = user)
                    if verifs.exists() and state != 'free' :
                        verif = verifs.first()
                        Abon.objects.filter(pk = abn.pk).update(verif = verif)
                    user.cur_abn = abn
                    if state != 'free' :
                        essentials = user.get_essentials()
                        now = timezone.now()
                        day_string = f"{now.year}:{now.month}:{now.day}"
                        essentials["all_swipe"][day_string] = 0
                        user.essentials = json.dumps(essentials)
                        user.save()
            usercode = UserCode.objects.get(pk = usercode.pk)
            return Response({
                    'done' : True,
                    'result' : {
                        'usercode' : { 'status' : usercode.state, 'reason' : usercode.reason},
                        'user' : UserSerializer(User.objects.get(pk = request.user.pk)).data,
                        'for_abon' : i_code.for_abon
                    }
                })
    return Response({
            'done' : False
        })

@api_view(['GET'])
def start_task(request) :
    log = daily_tasks()
    return Response({
        'done' : True,
        'result' : log
    })

@api_view(['GET'])
def get_command(request) :

    return Response({
        'done' : True,
        'result' : choice(json.loads(g_v("verif:coms")))
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_favorites(request, typ) :
    if typ == 'i_likes' :
        return Response({
            'done' : True,
            'result' : UserProfilSerializer(request.user.like.all().order_by('?'), many = True).data
        })
    elif typ == 'likes_me' :
        return Response({
            'done' : True,
            'result' : UserProfilSerializer(request.user.likes.all().order_by('?'), many = True).data
        })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def want_lov(request, pk) :
    user = User.objects.get(pk = pk)
    olds = Notif.objects.filter(typ = 'want_lov:' + str(request.user.pk), created_at__gt = timezone.now() - timezone.timedelta(days=7), created_at__lt = timezone.now(), user = user)
    if olds.exists() :
        return Response({
            'done' : False,
            'result' : 0
        })
    Notif.objects.create(typ = 'want_lov:' + str(request.user.pk), text = g_v('notif:want_lov').format(request.user.prenom), photo = request.user.get_profil(), user = user, urls = json.dumps([f'/profil/{request.user.pk}']))
    return Response({
        'done' : True,
        'result' : 0
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def set_quart(request) :
    quart = request.data.get('quart')
    request.user.quart = quart
    request.user.save()
    return Response({
        'done' : True,
        'result' : json.loads(request.user.quart)
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def deactivate_anonym(request, id) :
    room = RoomMatch.objects.get(pk = id)
    if request.user in room.users.all() :
        refused = request.GET.get('refused')
        anonym_off = PerfectLovDetails.objects.get_or_create(key = "anonym:off:room:" + str(id))[0]
        lis = []
        try :
            lis = json.loads(anonym_off.value)
        except :
            pass
        if not request.user.pk in lis : lis.append(request.user.pk)
        anonym_off.value = json.dumps(lis if not refused else [])
        anonym_off.save()
        
        return Response({
            'done' : True,
            'result' : 0
        })
        

@api_view(['GET'])
def get_pdetails(request, key) :
    return Response({
        'done' : True,
        'result' : json.loads(g_v(key))
    })

def terms(request) :
    return render(request, "app/terms.html", {})

def bilan(request) :
    return render(request, "app/investors.html", {})

def politique(request) :
    return render(request, "app/politique.html", {})

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def get_posts(request) :
    excepts = json.loads(request.POST.get('excepts')) + request.user.get_exils()
    
    posts = Post.objects.exclude(pk__in = excepts).filter(origin = None).order_by('-created_at')
    def set_seens() :
        for p in posts[:15] :
            p.seens.add(request.user)
            p.save()
    set_seens()
    return Response({
        'done' : True,
        'result' : PostSerializer(posts[:15], context = {'request' : request}, many = True).data
    })

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def get_my_posts(request) :
    excepts = json.loads(request.POST.get('excepts'))
    posts = request.user.posts.all().exclude(pk__in = excepts).filter(origin = None).order_by('-created_at')
    def set_seens() :
        for p in posts[:15] :
            p.seens.add(request.user)
            p.save()
    set_seens()
    return Response({
        'done' : True,
        'result' : PostSerializer(posts[:15], context = {'request' : request}, many = True).data
    })

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def get_comments(request, id) :
    excepts = json.loads(request.POST.get('excepts'))
    posts = Post.objects.exclude(pk__in = excepts).filter(origin__pk = id).order_by('-created_at')
    def set_seens() :
        for p in posts[:15] :
            p.seens.add(request.user)
            p.save()
    set_seens()
    return Response({
        'done' : True,
        'result' : PostSerializer(posts[:15], context = {'request' : request}, many = True).data
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_post(request) :
    text = request.POST.get('text')
    image= request.FILES.get('image')
    origin = request.POST.get('origin')
    post = Post.objects.create(user = request.user, text = text, image = image )
    if origin :
        post.origin = Post.objects.get(pk = int(origin))
        post.save()
    return Response({
        'done' : True,
        'result' : PostSerializer(post, context = {'request' : request}).data
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def exile_post(request, id) :
    request.user.set_exiles(id)
    return Response({
        'done' : True,
        'result' : True
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def signaler_user(request, id) :
    post = int(request.GET.get('post'))
    signal_obj = PerfectLovDetails.objects.get_or_create(key = 'signal:obj')[0]
    try :
        users = json.loads(signal_obj.value)
    except :
        users = []
    users.append(User.objects.get(pk = id).email)
    signal_obj.value = json.dumps(users)
    signal_obj.save()
    request.user.set_exiles(post)
    return Response({
        'done' : True
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def likes_fact(request, id) :
    post = Post.objects.get(pk = id)
    if request.user in post.likes.all() :
        post.likes.remove(request.user)
    else :
        post.likes.add(request.user)
    return Response({
        'done' : True,
        'request' : request.user in post.likes.all()
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_interest(request) :
    match_obj = json.loads(request.data.get('match_obj'))
    notif = Notif.objects.create(typ = 'send_inter', text = g_v('new:inter:notif').format(request.user.prenom, match_obj['obj']), photo = request.user.get_profil(), user  = User.objects.get(pk = match_obj['user']), urls = json.dumps([f"/profil/{request.user.pk}", f"{json.dumps(match_obj)}"]))
    return Response({
        'done' : True
    })
    
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def set_text_cat(request) :
    match_obj = json.loads(request.data.get('match_obj'))
    text = request.data.get('text')
    notif = Notif.objects.get_or_create(typ = 'send_inter', text = g_v(f'new:{"inter" if match_obj["typ"] == "interest" else match_obj["typ"]}:notif').format(request.user.prenom, match_obj['obj']), photo = request.user.get_profil(), user  = User.objects.get(pk = match_obj['user']))[0]
    match_obj['user'] = request.user.pk
    notif.urls = json.dumps([f"/profil/{request.user.pk}", f"{json.dumps(match_obj)}[]{text}"])
    notif.save()
    return Response({
        'done' : True,
    })
    
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def super_like(request) :
    pk = int(request.data.get('pk'))
    user = User.objects.get(pk = pk)
    user.super_likes.add(request.user)
    notif = Notif.objects.get_or_create(typ = 'send_sl', text = g_v(f'new:sl:notif').format(request.user.prenom), photo = request.user.get_profil(), user  = User.objects.get(pk = pk))[0]
    notif.urls = json.dumps([f"/profil/{request.user.pk}", f"{json.dumps({'user' : request.user.pk, 'typ' : 'super-like', 'obj' : ''})}[]"])
    notif.save()
    return Response({
        'done' : True,
        'result' : 0
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def all_mood(request) :
    moods = Mood.objects.all().annotate(users__count = Count('users') ).order_by('-users__count')
    
    return Response({
        'done' : True,
        'result' : MoodSerializer(moods, many = True).data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def set_mood(request) :
    pk =  int(request.data.get('pk'))
    mood = None if not pk else Mood.objects.get(pk = pk)
    request.user.mood = mood
    request.user.save()
    return Response({
        'done' : True,
        'result' : MoodSerializer(mood).data if pk else {
            'id' : 0,
            'name' : "Aucune envie"
        }
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def get_groups(request) :
    likes_pk = []
    excepts = json.loads(request.data.get('excepts'))
    g_rooms = excepts + [g.pk for g in request.user.my_groups.all()] + [g.pk for g in UserGroup.objects.annotate(us_count = Count('users')).filter(us_count = 1)]  + [g.pk for g in UserGroup.objects.annotate(g_users = Count('users')).filter(g_users__lt = 2)] + ([] if IS_DEV else [g.pk for g in UserGroup.objects.filter(creator__sex = request.user.sex)])
    
    for group in request.user.my_groups.all() :
        likes_pk += [g.pk for g in group.likes.all()]
        g_rooms += ([g.pk for g in group.matches.all()] + [group.sem_match.pk if group.sem_match else 0])
    random.shuffle(likes_pk)
    famous_pk = [ g.pk for g in UserGroup.objects.exclude(pk__in = g_rooms).annotate(all_likes = Count('likes')).order_by('-all_likes')[:10] if not g.pk in likes_pk  ]
    news_pk = [ g.pk for g in UserGroup.objects.exclude(pk__in = g_rooms).order_by('-created_at')[:20] if not g.pk in famous_pk  if not g.pk in (famous_pk + likes_pk) ]
    random.shuffle(famous_pk)
    random.shuffle(news_pk)
    finals_pk = likes_pk[:random.randint(0, 3)]
    finals_pk += famous_pk[:random.randint(2, 4)]
    finals_pk = list(set(finals_pk))
    finals_pk += news_pk[:DEFAULT_NUMBER - len(finals_pk)]
    print(finals_pk)
    return Response({
        'done' : True,
        'result' : GroupSerializer(UserGroup.objects.filter(pk__in = finals_pk).order_by('?'), context = {'request' : request},  many = True).data
    })
    
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def get_group(request) :
    return Response({
        'done' : True,
        'result' : GroupSerializer(UserGroup.objects.get(pk = int(request.data.get('id'))), context = {'request' : request}).data
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def create_group(request) :
    agroup = request.user.my_groups.all().annotate(us_count = Count('users')).filter(us_count = 1)
    if agroup.exists() :
        return Response({
            'done' : True,
            'result' : 0
        })
    else :
        group = UserGroup.objects.create(creator = request.user, code = generate_random_string(6))
        group.users.add(request.user)
        room_us = RoomMatch.objects.create(slug = room_slug(group, group, is_group=True))
        task = Taches.objects.filter(niveau = 0).first()
        niv = Niveau.objects.create(cur_task = task.pk)
        niv.taches.add(task)
        room_us.niveau = niv
        room_us.save()
        room_us.users.add(request.user)
        room_us.groups.add(group)
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(f"{request.user.pk}m{request.user.pk}", {
            'type' : 'new_group',
            'result' : ChatGroupSerializer(group).data
        })
        return Response({
            'done' : True,
            'result' : group.code
        })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def join_group(request) :
    code = request.data.get('code')
    group = UserGroup.objects.filter(code = code)
    if not group.exists() : 
        return Response({
            'done' : False
        })
    if group.first().users.count() == 4 :
        return Response({
            'done' : False
        })

    """if request.user in group.first().users.all() :
        return Response({
            'done' : False
        })"""
    group = group.first()
    channel_layer = get_channel_layer()
    group.users.add(request.user)
    for room in group.rooms.all() :
        room.users.add(request.user)
        if room.users.count() > 1 and group.rooms.count() == 1 :
            group_proposed = find_proposed(group, True)
            if group_proposed :
                room_match = RoomMatch.objects.get_or_create(slug = room_slug(group_proposed, group, True))[0]
                task = Taches.objects.filter(niveau = 0).first()
                niv = Niveau.objects.create(cur_task = task.pk)
                niv.taches.add(task)
                room_match.niveau = niv
                room_match.save()
                for us in group.users.all() :
                    room_match.users.add(us)
                for us in group_proposed.users.all() :
                    room_match.users.add(us)
                room_match.groups.add(group, group_proposed)
            """ for use in room_match.users.all() :
                
                async_to_sync(channel_layer.group_send)(f"{use.pk}m{use.pk}", {
                    'type' : 'new_room',
                    'result' : RoomSerializer(room_match).data
                })
                notif = Notif.objects.create(typ = 'new_gmatch', text = g_v('new:gpmatch:notif').format( group.get_oth_name(use) if use in group.users.all() else group_proposed.get_oth_name()), user  = use, urls = json.dumps([ f"/groom/{room_match.slug}"])) """

    
    async_to_sync(channel_layer.group_send)(f"{request.user.pk}m{request.user.pk}", {
        'type' : 'new_group',
        'result' : ChatGroupSerializer(group).data
    })
    for use in group.users.all().exclude(pk = request.user.pk) :
        async_to_sync(channel_layer.group_send)(f"{use.pk}m{use.pk}", {
                        'type' : 'update_gusers',
                        'result' : ChatGroupSerializer(group).data
                    })
    
    return Response({
        'done' : True
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def quit_group(request) :
    group = UserGroup.objects.get(pk = int(request.data.get('pk')))
    slugs = group.quit_group(request.user)
    channel_layer = get_channel_layer()
    for use in group.users.all() :
        async_to_sync(channel_layer.group_send)(f"{use.pk}m{use.pk}", {
            'type' : 'rmvu_from_g',
            'result' : {
                'user' : request.user.pk,
                'slug' : group.pk,
                'prenom' : request.user.prenom
            },
        })
    return Response({
        'done' : True,
        'result' : slugs
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def readd_prev(request) :
    target = request.data.get('target')
    user : User = request.user
    excepts = user.get_excepts()
    user.set_excepts([pk for pk in excepts if pk != target])
    return Response({
        'done'  :True
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def enable_payment(request) :
    number = request.data.get('number')
    typ = request.data.get('typ')
    amount = request.data.get('amount')
    clientid = g_v('qosic:clientid')
    transref = request.data.get('transref')
    abn = request.data.get('abn')
    code = l_p(number, transref, typ, amount, clientid)
    if code == 1 :
        PaymentPortal.objects.create(number = number, typ = typ, amount = amount, transref = transref, code = 1, abn = abn)
        return Response({
            'done' : True,
            'result' : transref
        })
    else :
        return Response({
            'done' : False
        })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def waiting_payment(request) :
    clientid = g_v('qosic:clientid')
    transref = request.data.get('transref')
    portal = PaymentPortal.objects.filter(user = request, transref = transref).first()
    channel_layer = get_channel_layer()
    if portal :
        def set_code() :
            code = portal.code
            while code == 1 :
                code = get_status(transref, clientid = clientid)
                time.sleep(0.3)
    
            portal.code = code
            portal.save()

            if code not in [0, 1] :
                async_to_sync(channel_layer.group_send)(f"{request.user.pk}m{request.user.pk}", {
                    'type' : 'momo_pay',
                    'result' : {
                        'transref' : transref,
                        'status' : 'error'
                    },
                })
            else :
                abon = {
                    'typ' : abn
                }
                state = "free" if not user.cur_abn else user.cur_abn.get_typ()['typ']
                user = request.user
                Notif.objects.create(typ = "new_abon", text = g_v('notif:new:abon').format(state), user = user, urls = json.dumps(["/param?target=cur_abn"]))
                abn = Abon.objects.create(typ = g_v('typ:' + abon['typ']), debut = timezone.now(), user = request.user, status = abon['typ'])
                verifs = Verif.objects.filter(user = request.user)
                if verifs.exists() and state != 'free' :
                    verif = verifs.first()
                    Abon.objects.filter(pk = abn.pk).update(verif = verif)
                user.cur_abn = abn
                aboned_before = Abon.objects.filter(user = request.user).exclude(pk = abn.pk).exists()
                if state != 'free' or not aboned_before :
                    essentials = request.user.get_essentials()
                    now = timezone.now()
                    day_string = f"{now.year}:{now.month}:{now.day}"
                    essentials["all_swipe"][day_string] = 0
                    user.essentials = json.dumps(essentials)
                user.save()
                async_to_sync(channel_layer.group_send)(f"{request.user.pk}m{request.user.pk}", {
                    'type' : 'momo_pay',
                    'result' : {
                        'transref' : transref,
                        'status' : 'success'
                    },
                    'other' : AbonSerializer(abn)
                })
        send_by_thread(set_code)
        return Response({
            'done' : True,
        })
    else :
        return Response({
            'done' : False
        })
