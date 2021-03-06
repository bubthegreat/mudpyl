from mudpyl.library.imperian.autosipper import Autosipper
from mudpyl.metaline import Metaline
from mock import Mock
import re

def test_health_update_max_health_setting():
    m = re.match('(\d+)', '42')
    a = Autosipper(10, 10)
    a.health_update(m, Mock())
    assert a.max_health == 42

#XXX

def test_health_update_matching():
    a = Autosipper(10, 10)
    ml = Metaline(' Health   : 5/5     Reserves : 5/5', None, None)
    assert list(a.health_update.match(ml))
