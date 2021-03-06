#coding: utf-8

from mudpyl.aliases import non_binding_alias, binding_alias
from mudpyl.triggers import non_binding_trigger, binding_trigger, RegexTrigger
from mudpyl.gui.keychords import from_string
from mudpyl.modules import BaseModule
from mudpyl.colours import *
from mudpyl.metaline import Metaline, simpleml
import re
import json

from bylins.base import fill_vars


RE_FIGHT_STATUS = ur'^\d+H \d+M \d+о Зауч:\d+ .*\[[\w\s]+:[\.\w\s\-]+\] \[[\w\s-]+:[\.\w\s\-]+\] >'
RE_NORMAL_STATUS = ur'^\d+H \d+M \d+о Зауч:\d+ .*\d+L \d+G Вых:.*>'

RE_OFF_FIGHT = (
    re.compile(ur'^Вы быстро убежали с поля битвы\.', re.UNICODE),
    re.compile(ur'[\w\s]+ \[\d+\]', re.UNICODE),
    re.compile(RE_NORMAL_STATUS, re.UNICODE),
    )


def clear_target(t):
    t = t.replace(u'(летит) ', '')
    t = re.sub(ur'\(.*\) ', '', t)
    return t


class TargetTrigger(RegexTrigger):
    def match(self, metaline):
        fores = metaline.fores
        if len(fores) == 1:
            if fores[0] == HexFGCode(255, 0, 0):
                if len(metaline.line) > 3 and metaline.line[0] != '.' and metaline.line[0] != ' ' :
                    return [metaline.line,]
        if len(fores) == 2:
            if len(metaline.line) > 3 and metaline.line[0] == '(':
                return [metaline.line,]
        return []
    
    def func(self, match, realm):
        if self.module and not self.module.fight():
            self.module.on_target(match, realm)

# триггеры выключения-включения боя
class FigthTrigger(RegexTrigger):
    def match(self, metaline):
        l = metaline.line.strip()
        for i in RE_OFF_FIGHT:
            if i.match(l):
                self.module.unset_fight()
        return []


def ml(m, c):
    return simpleml(m, c, bg_code(BLACK))

def get_target_short(t, num):
    s = t.split()
    try:
        t1 = s[num][:3]
        t2 = s[num+1][:3]
        while len(t1) != 3 and len(t2) != 3:
            num += 1
            t1 = s[num][:3]
            t2 = s[num+1][:3]
        return '%s.%s' % (t1, t2)
    except:
        try:
            t1 = s[num-len(s)][:3]
            while len(t1) != 3:
                num += 1
                t1 = s[num-len(s)][:3]
                
            return '%s' % (t1)
        except:
            pass
    return None
    

class TargetsSystem(BaseModule):
    target_trigger = TargetTrigger()
    fight_trigger = FigthTrigger()
    
    attacks = [u'атака1', u'атака2', u'атака3', u'атака4', u'атака5']
    
    def __init__(self, factory):
        BaseModule.__init__(self, factory)
        
        self.target_trigger.module = self
        self.fight_trigger.module = self
        self.realm = factory
        self.m = factory.mmap
        
        # цели
        self.target_flag = False
        self.targets = []
        
        self.current_target = -1
        self.opozn_targer_counter = 0
        self.opozn_flag = False
        self.double_key = False
        self.last_alias = None
        
        self.curr_attack = 0
        
        self.do_agr = False
        
        self.do_udavka = False
        
        try:
            self.load_aliases('targets.json')
        except:
            self.taliases = {}
    
    def load_aliases(self, path):
        self.taliases = json.loads(file(path, 'r').read(), encoding="utf-8")
    
    def dump_aliases(self, path):
        file(path, 'w').write(json.dumps(self.taliases, encoding="utf-8"))

    def auto_agr(self):
        return self.realm.get_var(u'автоагр')

    @property
    def aliases(self):
        return [self.set_target,]
    
    @property
    def triggers(self):
        return [
            self.target_trigger,
            self.fight_trigger,
            self.on_fight_status,
            self.on_normal_status,
            self.on_room,
            self.on_opozn,
            self.repeat_opozn,
            self.repeat_opozn1,
            self.repeat_opozn2,
            self.on_exp,
            ]
    
    @property
    def macros(self):
        return {
            from_string('<F1>'): self.key1,
            from_string('<F2>'): self.key2,
            from_string('<F3>'): self.key3,
            from_string('<F4>'): self.key4,
            from_string('<F5>'): self.key5,
            from_string('C-<cyrillic_a>'): self.change_attack,
            from_string('C-<cyrillic_be>'): self.change_auto_agr,
            }
    
    def change_auto_agr(self, realm):
        self.realm.toggle_var(u'автоагр')
    
    @binding_alias(u'^ц(\d+) ([\.\w]+)$')
    def set_target(self, match, realm):
        t = int(match.group(1))
        al = match.group(2)
        try:
            self.set_target_alias(self.targets[t-1], al)
            self.realm.write(ml('Алиас: %s -> %s' % (self.targets[t-1], al), fg_code(YELLOW, True)))
        except:
            self.realm.write(ml('Нет цели %s' % (t), fg_code(YELLOW, True)))
        realm.send_to_mud = False
    
    def change_attack(self, realm):
        self.curr_attack += 1
        if self.curr_attack > len(self.attacks) - 1:
            self.curr_attack = 0
        self.realm.set_var(u'атака', u'$%s$' % self.attacks[self.curr_attack], False)
        self.realm.info(u'Атака: %s: %s' % (self.attacks[self.curr_attack], self.realm.get_var(self.attacks[self.curr_attack])))
    
    def key1(self, realm):
        self.on_key(0)
    
    def key2(self, realm):
        self.on_key(1)
        
    def key3(self, realm):
        self.on_key(2)
    
    def key4(self, realm):
        self.on_key(3)
        
    def key5(self, realm):
        self.on_key(4)
    
    def on_key(self, n):
        if len(self.targets) - 1 < n:
            self.realm.write(ml('Нет цели %s' % (n+1), fg_code(YELLOW, True)))
            return
        
        t = self.targets[n]
        
        if self.current_target == n and self.double_key:
            self.opozn_flag = False
            self.opozn_targer_counter = 0
            self.opozn_targer()
            self.double_key = False
            return
        
        self.current_target = n
        al = self.get_target_alias(t)
        if not al:
            self.realm.write(ml('Нет алиаса цели %s, повторное нажатие -- поиск алиаса' % (n+1), fg_code(YELLOW, True)))
            self.double_key = True
        else:
            c = fill_vars(self.realm.get_var(u'атака'), self.realm)
            if not c:
                self.realm.write(ml('Не выставлена переменная "атака"', fg_code(YELLOW, True)))
                return
            c = c.replace(u'%1', al)
            #self.realm.write(c)
            if self.do_udavka:
                c = u'удав %s' % al
            self.realm.send(c)
        
    
    def get_target_alias(self, t):
        r = self.m.last_room
        if r:
            if self.taliases.has_key(r.zone):
                if self.taliases[r.zone].has_key(t):
                    return self.taliases[r.zone][t]
        return None
    
    def set_target_alias(self, t, al):
        self.realm.write(ml(u'Алиас цели: %s->%s' % (t, al), fg_code(YELLOW, True)))
        r = self.m.last_room
        if r:
            if self.taliases.has_key(r.zone):
                self.taliases[r.zone][t] = al
            else:
                self.taliases[r.zone] = {t: al,}
            self.dump_aliases('targets.json')
    
    def set_round(self, v):
        self.realm.set_var(u'бой_раунд', v, False)
    
    def get_round(self):
        return self.realm.get_var(u'бой_раунд')
    
    def inc_round(self):
        self.realm.set_var(u'бой_раунд', self.get_round() + 1, False)
        self.realm.write('#out2 Раунд: %s' % self.get_round())
    
    def fight(self):
        return self.realm.get_var(u'бой')
    
    def set_fight(self):
        if not self.fight():
            self.realm.set_var(u'бой', True, False)
            self.set_round(0)
            self.realm.write(ml('#out2 Режим боя включен', fg_code(RED, True)))
    
    def unset_fight(self):
        if self.fight():
            self.realm.set_var(u'бой', False, False)
            self.set_round(0)
            self.realm.write(ml('#out2 Режим боя выключен', fg_code(GREEN, True)))
    
    def on_target(self, match, realm):
        if self.target_flag:
            t = clear_target(match)
            self.targets.append(t)
            #realm.write('#out2 Target: %s -> ' % t)
            realm.alterer.insert_metaline(0, ml(u'<F%s> (%s) - ' % (len(self.targets), self.get_target_alias(t)), fg_code(GREEN, True)))
            
        # авто агрим цели
        if not self.do_agr and self.auto_agr() and not self.realm.get_var(u'бой'):
            for i in range(len(self.targets)):
                a = self.get_target_alias(self.targets[i])
                if a:
                    self.do_agr = True
                    self.on_key(i)
                    break
        #print self.manager, match
    
    def opozn_targer(self):
        self.opozn_flag = True
        t = self.targets[self.current_target]
        sh = get_target_short(t, self.opozn_targer_counter)
        if sh:
            self.last_alias = sh
            self.opozn_targer_counter += 1
            self.realm.send(u'см %s' % sh)
        else:
            self.opozn_targer_counter = 0
            self.opozn_flag = False
            self.realm.write(ml(u'Не могу опознать цель "%s"' % t, fg_code(YELLOW, True)))
    
    @binding_trigger(ur'^ '+re.escape('*') + ' .*')
    def on_opozn(self, match, realm):
        if self.opozn_flag:
            self.set_target_alias(self.targets[self.current_target], self.last_alias)
            self.opozn_flag = False
    
    @binding_trigger(ur'^Похоже, этого здесь нет\!')
    def repeat_opozn(self, match, realm):
        if self.opozn_flag:
            self.opozn_targer()
    
    @binding_trigger(ur'^Смотреть во что\?')
    def repeat_opozn1(self, match, realm):
        if self.opozn_flag:
            self.opozn_targer()
    
    @binding_trigger(ur'^Вы не видите ничего необычного\.')
    def repeat_opozn2(self, match, realm):
        if self.opozn_flag:
            self.opozn_targer()
        
    
    @binding_trigger(ur'^Ваш опыт повысился на \d+ очков.')
    def on_exp(self, match, realm):
        self.do_agr = False
        if self.auto_agr():
            realm.send(u'look')

    
    @binding_trigger(RE_FIGHT_STATUS)
    def on_fight_status(self, match, realm):
        self.set_fight()
        self.inc_round()
        self.do_agr = False

    @binding_trigger(RE_NORMAL_STATUS)
    def on_normal_status(self, match, realm):
        self.unset_fight()
        self.target_flag = False
        
        self.do_udavka = False
        if not self.do_udavka and match.group(0).find(u'Уд:0') > 0 and self.realm.get_var(u'автоудавка'):
            self.do_udavka = True
            #self.realm.write(ml(u'Включаем удавку!!!', fg_code(YELLOW, True)))
            
    
    @binding_trigger(ur'[\w\s]+ \[\d+\]')
    def on_room(self, match, realm):
        self.target_flag = True
        self.targets = []
