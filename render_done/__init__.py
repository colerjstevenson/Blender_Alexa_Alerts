 ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

bl_info = {
    "name": "Render Alerts",
    "author": "Cole Stevenson",
    "version": (1, 0, 0),
    "blender": (4, 1, 0),
    "location": "Output > Alarm and Shutdown",
    "description": "several options for notifying you when a render finishes",
    "warning": "",
    "category": "Render"}

import bpy
import aud, platform, subprocess, os, threading, smtplib, time, traceback, requests, json, urllib, random
from bpy.props import *
from bpy.app.handlers import persistent
from bpy.types import Operator, Panel, PropertyGroup, AddonPreferences

C = bpy.context
D = bpy.data

OS = 'WIN' if platform.system().startswith('Win') else 'LIN' #Determine platform prefix
d = '/' if OS == 'WIN' else '-'                              #platform dependent flag
sound_path = os.path.normpath(os.path.dirname(__file__)+'/sounds/')
poweroff_list = [("NONE", "Do Not Shut Down", ""),
                ("POWER_OFF", "Power Off", ""),
                ("RESTART", "Restart", ""),
                ("SLEEP", "Sleep", "")]


agents = ['Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:47.0) Gecko/20100101 Firefox/47.0',
'Mozilla/5.0 (Macintosh; Intel Mac OS X x.y; rv:42.0) Gecko/20100101 Firefox/42.0',
'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36',
'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.106 Safari/537.36 OPR/38.0.2220.41'
]

@persistent
def playSoundAndStartTimer(scene): #Function hooked at render completion event
    global timer
    props = scene.alarm_and_shutdown
    if bpy.context.window_manager.use_alarm_and_shutdown:
        playSound(props.sound_type)
        if props.use_send_email: sendMail()
        # if props.use_send_telegram: sendTelegram()
        # if props.use_send_viber: sendViber()
        if props.use_trigger_alexa: triggerAlexa()
        # if props.shutdown_type != 'NONE': #Start a shut-down timer if shut-down type set to enything but NONE
        #     props.remaining_time = props.timeout_time+3
        #     override = bpy.context.copy()
        #     override['window'] = bpy.data.window_managers[0].windows[0]
        #     bpy.ops.render.report_shutdown(override, 'EXEC_DEFAULT')
        #     timer = threading.Timer(1, countDown)
        #     timer.start()

def handlerBind(self, context): #callback function bind to use_alarm_and_shutdown checkbox
	H = bpy.app.handlers.render_complete
	if playSoundAndStartTimer not in H: H.append(playSoundAndStartTimer) #it binds playSoundAndStartTimer to handler

def playSound(type='NONE'): #Function that plays selected sound
    soundList = {'THREETONE':'Threetone.mp3','SHORTRING':'Short_Ring.mp3','MAGIC':'Magic.mp3','CHIMES':'Chimes.mp3', 'CUSTOM':''}
    if type != 'NONE':
        Device = aud.Device()
        if type != 'CUSTOM': Sound = aud.Sound(os.path.normpath(sound_path+'/'+soundList[type]))
        else: Sound = aud.Sound(os.path.normpath(bpy.context.preferences.addons[__name__].preferences.filepath))
        try:
            Device.play(Sound.volume(bpy.context.scene.alarm_and_shutdown.alarm_volume/100))
        except:
            print("\a")

def countDown(): #Counting down till shut-down, then compiling os dependent shut-down command, then sending it to os
    global timer, OS, d
    props = bpy.context.scene.alarm_and_shutdown
    if props.remaining_time > 0:
        props.remaining_time -= 1
        timer = threading.Timer(1, countDown)
        timer.start()
    else:
        win_flags = {'RESTART':'r /f', 'POWER_OFF':'s /f', 'SLEEP':'h'}
        lin_flags = {'RESTART':'reboot', 'POWER_OFF':'poweroff', 'SLEEP':'suspend'}
        if OS == 'LIN': 
            os.system('systemctl '+lin_flags[props.shutdown_type])
        else:
            subprocess.call('shutdown /{}'.format(win_flags[props.shutdown_type]))

def encode(str):
    return urllib.parse.quote(str.replace('_','-'))
    
def url_params(type):
    prefs = bpy.context.preferences.addons[__name__].preferences
    chatid = prefs.chatid
    S = bpy.context.scene
    T = time.strftime("%a, %d %b %H:%M:%S", time.localtime())
    url_params = {
        'time': encode(T),
        'file': encode(bpy.path.basename(bpy.data.filepath)),
        'scene': encode(S.name),
        'postaction': S.alarm_and_shutdown.shutdown_type.lower(),
        'timeout': S.alarm_and_shutdown.timeout_time,
        }
    if type=='email':
        url_params['address'] = encode(prefs.emailto)
    # if type=='telegram':
    #     url_params['chatid'] = prefs.chatid
    # if type=='viber':
    #     url_params['userid'] = prefs.viberid
    if type == 'alexa':
        url_params['alexa'] = prefs.alexaUrl

    return url_params
    
def sendMail():
    global agents
    url = 'https://alarmandshutdown.ru/mail/send'
    r = requests.get(url, params=url_params('email'), headers={'user-agent':agents[random.randint(0,3)]})
    if r.status_code == 200:
        print('Email sent successfully')
    else:
        print('Error sending email. Error code: '+str(r.status_code))
    
# def sendTelegram():
#     global agents
#     url = 'https://alarmandshutdown.ru/telebot/completed'    
#     r = requests.get(url, params=url_params('telegram'), headers={'user-agent':agents[random.randint(0,3)]})
#     if r.status_code == 200:
#         print('Telegram message sent successfully')
#     else:
#         print('Error sending telegram message. Error code: '+str(r.status_code))
        
# def sendViber():
#     global agents
#     url = 'https://alarmandshutdown.ru/vibot/completed'    
#     r = requests.get(url, params=url_params('viber'), headers={'user-agent':agents[random.randint(0,3)]})
#     if r.status_code == 200:
#         print('Viber message sent successfully')
#     else:
#         print('Error sending viber message. Error code: '+str(r.status_code))

def triggerAlexa():
    prefs = bpy.context.preferences.addons[__name__].preferences
    if prefs.alexaUrl == '':
        r = requests.get("https://www.virtualsmarthome.xyz/url_routine_trigger/activate.php?trigger=9595900e-3faa-4321-acf1-ed1d369b7325&token=9e921fc9-5137-4cf2-b549-e72b449fcfdb&response=html") 
    else:   
        r = requests.get(prefs.alexaUrl)
    if r.status_code == 200:
        print('Alexa Triggered Successfully')
    else:
        print('Error triggering alexa. Error code: '+str(r.status_code))
    
class playAlarmSound(bpy.types.Operator): #operator that plays de sound
    bl_description = 'Tests alarm sound'
    bl_idname = 'sound.play_alarm'
    bl_label = 'Play Alarm Sound'
    
    @classmethod
    def poll(cls, context):
        if context.scene.alarm_and_shutdown.sound_type != 'NONE': return True
        return False

    def execute(self, context):
        playSound(bpy.context.scene.alarm_and_shutdown.sound_type)
        return {'FINISHED'}

class abortShutDown(bpy.types.Operator):
    bl_description = 'Abort shutdown timer'
    bl_idname = 'render.abort_shutdown'
    bl_label = 'Abort'
    
    @classmethod
    def poll(cls, context):
        if context.scene.alarm_and_shutdown.remaining_time > 0:
            return True
        return False

    def execute(self, context):
        global timer
        timer.cancel()
        context.scene.alarm_and_shutdown.remaining_time = 0
        return {'FINISHED'}

class reportTimer(bpy.types.Operator):
    bl_description = 'Report shutdown timer'
    bl_idname = 'render.report_shutdown'
    bl_label = 'Report'
    
    _timer = None

    def modal(self, context, event):
        if bpy.context.scene.alarm_and_shutdown.remaining_time < 1:
            self.cancel(context)
            self.report({'INFO'}, "Alarm and Shutdown: Shut-down aborted!")
            return {'CANCELLED'}

        if event.type == 'TIMER':
            #print("Alarm and Shutdown: Shut-down timer in progress! {0} seconds remaining".format(bpy.context.scene.alarm_and_shutdown.remaining_time))
            self.report({'WARNING'}, "Alarm and Shutdown: Shut-down timer in progress! {0} seconds remaining".format(bpy.context.scene.alarm_and_shutdown.remaining_time))

        return {'PASS_THROUGH'}

    def execute(self, context):
        wm = context.window_manager
        self._timer = wm.event_timer_add(1, window=context.window)
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        wm = context.window_manager
        wm.event_timer_remove(self._timer)


bpy.types.WindowManager.use_alarm_and_shutdown = BoolProperty(name='Enable', description='Enable alarm and shutdown', default=False, update=handlerBind)

class alarmAndShutdownPROPS(bpy.types.PropertyGroup): #All the properties utilized by addon
    timeout_time : IntProperty(name='Timeout/sec', description='Timeout untill shutdown action', min=0, step=1, subtype='TIME')
    sound_type : EnumProperty(items=[
                                ("NONE", "No sound", "No sound plays at render completion", 1),
                                ("CHIMES", "Chimes", "", 2),
                                ("MAGIC", "Magic", "", 3),
                                ("SHORTRING", "Short Ring", "", 4),
                                ("THREETONE", "Threetone", "", 5),
                                ("CUSTOM", "Custom", "", 6),
                                ], description='Sound type', name='Sound type')
    shutdown_type : EnumProperty(items=poweroff_list, default='NONE', description='Shutdown type', name='Shutdown type')
    remaining_time : IntProperty()
    alarm_volume : IntProperty(name='Volume', description='Alarm volume level', default=100, min=1, max=100, step=1, subtype='PERCENTAGE')
    use_send_email : BoolProperty(name='Send Email', description='Sends an email with notification on render completion', default=False)
    # use_send_telegram : BoolProperty(name='Send Telegram Message', description='Sends a message via Telegram on render completion', default=False)
    # use_send_viber : BoolProperty(name='Send Viber Message', description='Sends a message via Viber on render completion', default=False)
    use_attach_render : BoolProperty(name='Attach rendered image', description='Attaches rendered image to the notification', default=False)
    use_trigger_alexa : BoolProperty(name='Trigger Alexa Alert', description='Triggers an alert on alexa when render completes', default=False)
    

bpy.utils.register_class(alarmAndShutdownPROPS)
bpy.types.Scene.alarm_and_shutdown = PointerProperty(type=alarmAndShutdownPROPS)
    

class alarmAndShutdownPANEL(bpy.types.Panel):
    bl_description = 'Triggers alerts when a render comletes'
    bl_idname = 'RENDER_PT_alarm'
    bl_label = 'Render Alerts'
    bl_region_type = 'WINDOW'
    bl_space_type = 'PROPERTIES'
    bl_context = 'output'
    
    @classmethod
    def poll(cls, context):
        return True
    
    def draw(self, context):
        props = context.scene.alarm_and_shutdown
        prefs = bpy.context.preferences.addons[__name__].preferences
        l = self.layout
        m = l.column()
        m.active = bpy.context.window_manager.use_alarm_and_shutdown #Check whether addon function is enabled
        c = m.column(align=True)
        c.prop(props, 'sound_type', text='', icon='SOUND')
        r = c.row(align=True)
        r.prop(props, 'alarm_volume')
        r.operator('sound.play_alarm', text='', icon='OUTLINER_DATA_SPEAKER')
        c = m.column(align=True)
        c.prop(props, 'shutdown_type', text='', icon='QUIT')
        c.prop(props, 'timeout_time')
        c.prop(props, 'use_send_email')
        # c.prop(props, 'use_send_telegram')
        # c.prop(props, 'use_send_viber')
        c.prop(props, 'use_trigger_alexa')
        if props.use_send_email and prefs.emailto == '': c.label(text='Email address is not set', icon='ERROR')
        # if props.use_send_telegram and prefs.chatid == '': c.label(text='Telegram chat ID is not set', icon='ERROR')
        # if props.use_send_viber and prefs.viberid == '': c.label(text='Viber user ID is not set', icon='ERROR')
        if props.use_trigger_alexa and prefs.alexaUrl == '': c.label(text='alexaUrl is not set', icon='ERROR')
        c = m.column()
        c.scale_y = 3
        if props.remaining_time > 0:
            c.operator('render.abort_shutdown', text='Shut-down timer in progress. Abort.', icon='CANCEL')
        
    def draw_header(self, context):
        l = self.layout
        l.prop(context.window_manager, 'use_alarm_and_shutdown', text='')
    
class AlarmAndShutdownPREF(AddonPreferences):
    bl_idname = __name__
    filepath: StringProperty(name="Custom Audio File", description="Specify location of a custom audio file", subtype="FILE_PATH")
    emailto: StringProperty(name="Email address", description="Set a correct address to where an email will be sent. Up to three addresses supported (comma separated)")
    alexaUrl: StringProperty(name="Alexa URL", description="the url that triggers the alexa notification")
    # chatid: StringProperty(name="Telegram chat ID", description="Specify your telegram chat ID here. You can get it from AlarmAndShutdown bot via Telegram messenger")
    # viberid: StringProperty(name="Viber ID", description="Specify your Viber user ID here. You can get it from AlarmAndShutdown bot in via Viber messenger")

    def draw(self, context):
        l = self.layout
        r = l.row(align=True)
        r.label(text="Custom Sound File Path:")
        r.prop(self, "filepath", text="")
        l.label(text='Notification settings', icon='URL')
        c = l.column()
        c.prop(self, 'emailto')
        r = c.row(align=True)
        c.prop(self, 'alexaUrl')
        r = c.row(align=True)
        # r.prop(self, 'chatid')
        # op = r.operator('wm.url_open', text='', icon='QUESTION')
        # op.url = 'http://blenderust.com/alarm-and-shutdown-v1-3/#telegram'
        # r = c.row(align=True)
        # r.prop(self, 'viberid')
        # op = r.operator('wm.url_open', text='', icon='QUESTION')
        # op.url = 'http://blenderust.com/alarm-and-shutdown-v1-3/#viber'
        
toRegister = (alarmAndShutdownPANEL, AlarmAndShutdownPREF, playAlarmSound, abortShutDown, reportTimer)
    
def register():
    for cls in toRegister:
        bpy.utils.register_class(cls)
    handlerBind(None, C)

def unregister():
    H = bpy.app.handlers.render_complete
    if playSoundAndStartTimer in H:
        bpy.app.handlers.render_complete.remove(playSoundAndStartTimer)
    for cls in toRegister:
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
