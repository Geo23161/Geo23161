from channels.generic.websocket import JsonWebsocketConsumer
from asgiref.sync import async_to_sync
from .models import *
from .views import send_by_thread
import time

def get_delete(pk) :
    try :
        pks = PerfectLovDetails.objects.get(key = f"{pk}:delete")
        return json.loads(pks.value)
    except :
        return []

def the_other(room, user) :
    return room.users.all().exclude(pk = user.pk).first()

class LovConsumer(JsonWebsocketConsumer) :
    
    def connect(self) :
        if self.scope['user'].is_anonymous:
            return self.close()
        
        def initiate_all() :
            all_rooms = self.scope['user'].rooms.all()
            rooms = all_rooms.filter(created_at__gt = self.scope['user'].last)
            messages = Message.objects.filter(room__in = all_rooms, step = 'sent')
            essentials = self.scope['user'].get_essentials()
            notifs = Notif.objects.filter(created_at__gt = self.scope['user'].last, user = self.scope['user'])
            try : 
                verif = VerifSerializer(Verif.objects.get(user__pk = self.scope['user'].pk)).data
            except :
                verif = None
            done = {
                'rooms' : RoomSerializer(rooms, many = True).data,
                'messages' : MessageSerializer(messages, many = True).data,
                'essentials' : essentials,
                'verif' : verif,
                'asset_url' : g_v('cloudinary:base'),
                'notifs' : NotifSerializer(notifs, many = True).data,
                'day_discuss' : json.loads(g_v('day:discuss')),
                'bad_profil' : PerfectLovDetails.objects.filter(key=f"bad:profil:{self.scope['user'].pk}").exists(),
                'should_invite' : PerfectLovDetails.objects.filter(key="should_invite").exists(),
            }
            deleteds = []
            for room in all_rooms :
                deleteds.append([
                    pk for pk in get_delete(room.pk)
                ])
                async_to_sync(self.channel_layer.group_add)(room.slug, self.channel_name)
            async_to_sync(self.channel_layer.group_add)(f"{self.scope['user'].pk}m{self.scope['user'].pk}", self.channel_name)
            
            result = {
                'type' : 'initialisation',
                'result' : done,
                'other' : deleteds
            }
            self.accept()
            time.sleep(0.4)
            self.send_json(result)
        send_by_thread(initiate_all)

    def new_room(self, ev) :
        async_to_sync(self.channel_layer.group_add)(ev['result']['slug'], self.channel_name)
        return self.send_json(ev)
    
    def new_message(self, ev) :
        return self.send_json(ev)
    
    def message_update(self, ev) :
        return self.send_json(ev)
    
    def d_m(self, ev) :
        return self.send_json(ev)
    
    def messsage_update(self, ev) :
        return self.send_json(ev)
    
    def send_online(self, ev) :
        if ev['result']['id'] != self.scope['user'].pk :
            print(ev['result']['prenom'], self.scope['user'].prenom)
            return self.send_json(ev)
    
    def new_photo(self, ev) :
        return self.send_json(ev)
    
    def s_o(self, ev) :
        if ev['result'][0] != self.scope['user'].pk :
            return self.send_json(ev)
    
    def launcher_send(self, ev) :
        if ev['result']['author'] != self.scope['user'].pk :
            return self.send_json(ev)
        
    def refuse_la(self, ev) :
        if ev['result']['author'] == self.scope['user'].pk :
            return self.send_json(ev)
        else :
            return self.send_json({
                'type' : 'refused',
                'result' : 0
            })

    def new_niveau(self, ev) :
        print(ev)
        return self.send_json(ev)
    
    def new_notif(self, ev) :
        return self.send_json(ev)
    
    def s_m(self, ev) :
        if ev['result']['target'] == self.scope['user'].pk :
            return self.send_json(ev)
    
    def receive_json(self, content, **kwargs):
        user = User.objects.get(pk = self.scope['user'].pk)
        if content['type'] == 'heartbeat' :
            user.last = timezone.now()
            user.save()
            for room in user.rooms.all() :
                uer = SimpleUserSerializer(user).data
                async_to_sync(self.channel_layer.group_send)(room.slug, {
                        'type' : 's_o',
                        'result' : [user.id, uer['last']]
                })
            essentials = content['essentials']
            likes = content['likes']
            matches = content['matches']
            rescues = content['rescues']
            nivs = content['nivs']
            for niv in nivs :
                room = RoomMatch.objects.filter(pk = niv['room'])
                if room.exists() :
                    room = room.first()
                    pl = PerfectLovDetails.objects.filter(key = f"launcher:{room.pk}")
                    if pl.exists() :
                        pl.first().save()
                    else :
                        if f"{room.niveau.level}:{room.niveau.cur_task}" != niv['niv'] :
                            async_to_sync(self.channel_layer.group_send)(room.slug, {
                            'type' : 'new_niveau',
                            'result' : NiveauSerializer(room.niveau).data,
                            'other' : room.slug
                            })
            old_ess = user.get_essentials()
            for key, value in essentials.items() :
                if key == 'all_swipe' :
                    for k,v in value.items() :
                        old_ess['all_swipe'][k] = v
                elif key == 'seens_tofs' :
                    for pk in value :
                        old_ess['seen_tofs'].append(pk)
                elif key == 'already_seens' :
                    old_ess['already_seens'] = [
                        old for old in old_ess['already_seens'] if not old['id'] in [
                            l["id"] for l in value
                        ]
                    ]
                    real_val = []
                    for l in value :
                        if not l['id'] in [ p['id'] for p in real_val] :
                            real_val.append(l)
                    for ss in real_val :
                        old_ess['already_seens'].append(ss)
            user.set_essentials(old_ess)
            for pk in likes :
                User.objects.get(pk = pk).likes.add(user)
                search_match(action='post_add', reverse= True, instance=user, pk_set= {User.objects.get(pk = pk).pk}) 
            for m in matches :
                target = User.objects.get(pk = m)
                if not RoomMatch.objects.filter(slug = room_slug(user, target)).exists() :
                    task = Taches.objects.filter(niveau = 0).first()
                    niv = Niveau.objects.create(cur_task = task.pk)
                    niv.taches.add(task)
                    room_match = RoomMatch.objects.get_or_create(slug = room_slug(user, target))[0]
                    room_match.niveau = niv
                    room_match.save()
                    room_match.users.add(user)
                    room_match.users.add(target)
                    for use in room_match.users.all() :
                        async_to_sync(self.channel_layer.group_send)(f"{use.pk}m{use.pk}", {
                            'type' : 'new_room',
                            'result' : RoomSerializer(room_match).data
                        })
                        notif = Notif.objects.create(typ = 'new_match', text = g_v('new:match:notif').format(use.prenom, room_match.why.lower()), photo = use.get_profil(), user  = the_other(room_match ,use), urls = json.dumps([f"/profil/{use.pk}", f"/room/{room_match.slug}"]))
            for iid in rescues :
                try :
                    mes = Message.objects.get(pk = iid)
                    if not content['time'] : mes.save()
                except :
                    pass
        elif content['type'] == 'r_m' :
            mess = Message.objects.get(pk = content['result'])
            if mess.step == 'sent' :
                mess.step = 'delivered'
                mess.save()
        elif content['type'] == 's_s' :
            mess = Message.objects.get(pk = content['result'])
            mess.step = 'seen'
            mess.save()
        elif content['type'] == 'keeping' :
            pks = content['result']
            room_pks = content['other']
            print(room_pks)
            messages = Message.objects.filter(pk__in = pks)
            final= [ [m.step, m.pk] for m in messages ]
            rooms = user.rooms.all().exclude(pk__in = room_pks)
            cont = {
                'type' : 'keeping',
                'result' : final,
                'other' : RoomSerializer(rooms, many = True).data
            }
            self.send_json(cont)
        elif content['type'] == 'c_m' :
            me = content['result']
            state = content['state']
            can_cont = True
            """ if state != 'on' :
                new_state = state_messag(me['get_room'], self.scope['user'])
                if new_state == 'on' : can_cont = True
                else :
                    self.send_json({
                            'type' : 's_m',
                            'result' : {
                                'state' : new_state,
                                'target' : user.pk,
                                'old_pk' : me['old_pk']
                            }
                    })
                    Message.objects.filter(old_pk = me['old_pk']).delete() """
            if can_cont :
                try :
                    room = RoomMatch.objects.filter(pk = me['get_room'])
                    if room.exists() :
                        room = room.first()
                        message = Message.objects.create( room = room, text = me['text'], user = me['user'], old_pk = me['old_pk'] )
                        #handle_mess_perm(me['get_room'], self.scope['user'], me['old_pk'])
                    else :
                        self.send_json({
                                'type' : 's_m',
                                'result' : {
                                    'state' : 'deleted',
                                    'target' : user.pk,
                                    'old_pk' : me['old_pk']
                                }
                        })
                except Exception as e :
                    print("Erreur creation message => ",e)
        elif content['type'] == 'l_m' :
            launcher = content['result']
            obj = PerfectLovDetails.objects.create(key = f'launcher:{launcher["id"]}', value = json.dumps(launcher))
        elif content['type'] == 'v_l' :
            launcher = content['result']
            obj = PerfectLovDetails.objects.get(key = f'launcher:{launcher["id"]}')
            obj.value= json.dumps(launcher)
            obj.save()
        elif content['type'] == 'register_me' :
            async_to_sync(self.channel_layer.group_add)( content['result'], self.channel_name)
        elif content['type'] == 'initiate_chat' :
            result = content['result']
            target = User.objects.get(pk = result['target'])
            if result['author'] == user.pk :
                if not RoomMatch.objects.filter(slug = room_slug(user, target)).exists() :
                    task = Taches.objects.filter(niveau = 0).first()
                    niv = Niveau.objects.create(cur_task = task.pk)
                    niv.taches.add(task)
                    room_match = RoomMatch.objects.get_or_create(slug = room_slug(user, target))[0]
                    room_match.niveau = niv
                    room_match.why = f"{user.prenom} pense que vous pouvez potentiellemnt matcher."
                    room_match.save()
                    room_match.users.add(user)
                    room_match.users.add(target)
                    for use in room_match.users.all() :
                        async_to_sync(self.channel_layer.group_send)(f"{use.pk}m{use.pk}", {
                            'type' : 'new_room',
                            'result' : RoomSerializer(room_match).data
                        })
        elif content['type'] == "rmv_me" :
            async_to_sync(self.channel_layer.group_discard)(content['result'] ,self.channel_name)
            
    def disconnect(self, code):
        if self.scope['user'].is_anonymous:
            return self.close()
        def remove_all_room() :
            all_rooms = self.scope['user'].rooms.all()
            for room in all_rooms :
                async_to_sync(self.channel_layer.group_discard)(room.slug, self.channel_name)
            async_to_sync(self.channel_layer.group_discard)(f"{self.scope['user'].pk}m{self.scope['user'].pk}", self.channel_name)
        send_by_thread(remove_all_room)
        self.close()