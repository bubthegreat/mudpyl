from mudpyl.realms import RootRealm
from mudpyl.colours import fg_code, bg_code, WHITE, BLACK
from mudpyl.metaline import Metaline, RunLengthList
from mudpyl.triggers import binding_trigger
from mudpyl.aliases import binding_alias
from mudpyl.net.telnet import TelnetClientFactory

class FooException(Exception):
    pass

class Bad:
    def __init__(self, c):
        raise FooException()

class Circular:
    def __init__(self, c):
        pass
Circular.modules = [Circular]

class WithTriggers:
    def __init__(self, c):
        c.triggers = [2, 1, 6, 3]
        c.aliases = [10, 4, 6, 9, 1, 2]
    modules = []

class TestModuleLoading:

    def setUp(self):
        self.c = RootRealm(None)

    def test_load_sorts_triggers_and_aliases(self):
        self.c.load_module(WithTriggers)
        assert self.c.triggers == [1, 2, 3, 6]
        assert self.c.aliases == [1, 2, 4, 6, 9, 10]

    def test_circular_requirements(self):
        self.c.load_module(Circular)
        assert self.c.modules_loaded == set([Circular])

    def test_removes_from_modules_loaded_on_error(self):
        try:
            self.c.load_module(Bad)
        except FooException:
            assert Bad not in self.c.modules_loaded
        else:
    	    assert False

class FakeTelnet:

    def __init__(self):
        self.sent = []

    def sendLine(self, line):
        self.sent.append(line)

class MockOutputs:

    def __init__(self, fore, back, wts):
        self.fore = fore
        self.back = back
        self.write_to_screen = wts

class Test_write:

    def setUp(self):
        self.fore = "tata"
        self.back = "toto"
        self.fact = TelnetClientFactory(None)
        self.fact.outputs = MockOutputs(self.fore, self.back, self.our_wts)
        self.realm = self.fact.realm
        self.realm.telnet = FakeTelnet()
        self.lines_gotten = []
        #hack: use set() here because it has copy()
        self.noting_line = Metaline('foo', set(), set())

    def our_wts(self, ml):
        self.lines_gotten.append(ml)

    def writer(self, match, realm):
        print 'writer called!'
        realm.write(self.noting_line)

    def test_from_not_a_string(self):
        self.realm.write(42)
        assert len(self.lines_gotten) == 1
        assert self.lines_gotten[0].line == '42'

    def test_from_string(self):
        self.realm.write('spam')
        assert len(self.lines_gotten) == 1
        assert self.lines_gotten[0].line == 'spam'

    def test_from_metaline(self):
        ml = Metaline('foo', None, None)
        self.realm.write(ml)
        assert self.lines_gotten == [ml]

    def test_no_colourbleed_fg(self):
        self.realm.write("eggs")
        cols = self.lines_gotten[0].fores.as_pruned_index_list()
        expected = [(0, fg_code(WHITE, False))]
        assert cols == expected, (cols, expected)

    def test_no_colourbleed_bg(self):
        self.realm.write("eggs")
        cols = self.lines_gotten[0].backs.as_pruned_index_list()
        assert cols ==  [(0, bg_code(BLACK))], cols

    def test_passes_on_wrap_default(self):
        self.realm.write("eggs")
        assert not self.lines_gotten[0].wrap

    def test_soft_line_start_default_is_off(self):
        self.realm.write("barbaz")
        assert not self.lines_gotten[0].soft_line_start

    def test_passes_on_soft_line_start(self):
        self.realm.write('foo', soft_line_start = True)
        assert self.lines_gotten[0].soft_line_start

    noting_trigger = binding_trigger('bar')(writer)
    noting_alias = binding_alias('bar')(writer)

    def test_write_writes_after_during_matching_triggers(self):
        self.realm.triggers.append(self.noting_trigger)
        inline = Metaline('bar', set(), set())
        self.realm.receive(inline)
        assert self.lines_gotten == [inline, self.noting_line], \
               self.lines_gotten

    def test_write_writes_after_during_alias_matching(self):
        self.realm.aliases.append(self.noting_alias)
        inline = Metaline('bar', RunLengthList([(0, fg_code(WHITE, False))]),
                          RunLengthList([(0, bg_code(BLACK))]),
                          soft_line_start = True)
        self.realm.send('bar')
        print self.lines_gotten
        print
        expected = [inline, self.noting_line]
        print expected
        assert self.lines_gotten == expected

class Test_receive:

    def setUp(self):
        self.fore = "tata"
        self.back = "toto"
        self.fact = TelnetClientFactory(None)
        self.fact.outputs = MockOutputs(self.fore, self.back, self.our_wts)
        self.realm = self.fact.realm
        self.lines_gotten = []
        self.ml = Metaline('foo', set(), set())
        self.ml2 = Metaline("bar", None, None)

    def our_wts(self, ml):
        self.lines_gotten.append(ml)

    def test_sends_to_screen_normally(self):
        self.realm.receive(self.ml)
        assert self.lines_gotten == [self.ml]

    @binding_trigger("foo")
    def trigger_1(self, match, realm):
        realm.write(self.ml2)

    def test_write_writes_afterwards(self):
        self.realm.triggers.append(self.trigger_1)
        self.realm.receive(self.ml)
        assert self.lines_gotten == [self.ml, self.ml2]

    @binding_trigger("foo")
    def trigger_2(self, match, realm):
        realm.display_line = False

    def test_doesnt_display_if_asked_not_to(self):
        self.realm.triggers.append(self.trigger_2)
        self.realm.receive(self.ml)
        assert self.lines_gotten == []

    @binding_alias("spam")
    def bar_writing_alias(self, match, realm):
        realm.write("BAR BAR BAR")
        realm.send_to_mud = False
    
    @binding_trigger('foo')
    def spam_sending_trigger(self, match, realm):
        realm.send("spam")

    def test_aliases_inside_triggers_write_after_trigger_writes(self):
        self.realm.triggers.append(self.spam_sending_trigger)
        self.realm.aliases.append(self.bar_writing_alias)

        noteline = Metaline("BAR BAR BAR",
                            RunLengthList([(0, fg_code(WHITE, False))]),
                            RunLengthList([(0, bg_code(BLACK))]))

        self.realm.receive(self.ml)

        assert self.lines_gotten == [self.ml, noteline]

    #XXX: test trigger matching specifically instead of accidentally

class Test_send:

    def setUp(self):
        self.fore = "tata"
        self.back = "toto"
        self.fact = TelnetClientFactory(None)
        self.fact.outputs = MockOutputs(self.fore, self.back, self.our_wts)
        self.realm = self.fact.realm
        self.realm.telnet = self.tc = FakeTelnet()
        self.lines_gotten = []

    def our_wts(self, ml):
        self.lines_gotten.append(ml)

    def test_send_sends_to_the_mud(self):
        self.realm.send("bar")
        assert self.tc.sent == ['bar']

    def test_send_echos_by_default(self):
        self.realm.send("bar")
        expected = Metaline('bar', 
                            RunLengthList([(0, fg_code(WHITE, False))]),
                            RunLengthList([(0, bg_code(BLACK))]),
                            soft_line_start = True)
        assert self.lines_gotten == [expected]

    def test_send_doesnt_echo_if_told_not_to(self):
        self.realm.send("bar", False)
        assert self.lines_gotten == []

    def test_send_uses_echoes_with_soft_line_start(self):
        self.realm.send("spam")
        expected = Metaline('spam', 
                            RunLengthList([(0, fg_code(WHITE, False))]),
                            RunLengthList([(0, bg_code(BLACK))]),
                            soft_line_start = True)
        assert self.lines_gotten == [expected]

    #TODO: (not tested yet)
    #  - test calling send in a trigger and echoing then
    #  - test recursive calls to send properly
    #  - actually test matching properly

    @binding_alias("bar")
    def our_alias_1(self, match, realm):
        print 'sending after!'
        realm.send_after("foo")

    def test_send_after_sends_afterwards(self):
        self.realm.aliases.append(self.our_alias_1)
        self.realm.send('bar')

        assert self.tc.sent == ['bar', 'foo'], self.tc.sent

    def test_send_after_default_echoing_is_off(self):
        self.realm.aliases.append(self.our_alias_1)
        self.realm.send("bar")
        expected = [Metaline('bar', 
                             RunLengthList([(0, fg_code(WHITE, False))]),
                             RunLengthList([(0, bg_code(BLACK))]),
                             soft_line_start = True)]
        assert self.lines_gotten == expected

    @binding_alias('baz')
    def our_alias_2(self, match, realm):
        realm.send_after("eggs", echo = False)

    def test_send_after_doesnt_echo_if_asked_not_to(self):
        self.realm.aliases.append(self.our_alias_2)
        self.realm.send("baz")
        expected = [Metaline('baz', 
                             RunLengthList([(0, fg_code(WHITE, False))]),
                             RunLengthList([(0, bg_code(BLACK))]),
                             soft_line_start = True)]
        assert self.lines_gotten == expected

    @binding_alias("foo")
    def foo_alias_sends_bar(self, match, realm):
        print 'Foo alias going!'
        realm.send('bar', echo = True)

    @binding_alias("bar")
    def bar_alias_sends_baz(self, match, realm):
        print 'Bar alias going'
        realm.send('baz', echo = True)

    def test_sends_and_writes_in_a_consistent_order(self):
        self.realm.aliases.append(self.foo_alias_sends_bar)
        self.realm.aliases.append(self.bar_alias_sends_baz)
        self.realm.send("foo", echo = True)

        expect_write = [Metaline("baz",
                                 RunLengthList([(0, fg_code(WHITE, False))]),
                                 RunLengthList([(0, bg_code(BLACK))]),
                                 soft_line_start = True),
                        Metaline("bar",
                                 RunLengthList([(0, fg_code(WHITE, False))]),
                                 RunLengthList([(0, bg_code(BLACK))]),
                                 soft_line_start = True),
                        Metaline("foo",
                                 RunLengthList([(0, fg_code(WHITE, False))]),
                                 RunLengthList([(0, bg_code(BLACK))]),
                                 soft_line_start = True)]
        expect_send = ['baz', 'bar', 'foo']

        assert self.lines_gotten == expect_write
        assert self.tc.sent == expect_send

    @binding_alias('spam')
    def noisy_alias(self, match, realm):
        realm.write("FOO FOO FOO")

    def test_writes_come_after_echoing(self):
        self.realm.aliases.append(self.noisy_alias)
        self.realm.send("spam")

        expecting = [Metaline("spam",
                              RunLengthList([(0, fg_code(WHITE, False))]),
                              RunLengthList([(0, bg_code(BLACK))]),
                              soft_line_start = True),
                     Metaline("FOO FOO FOO",
                              RunLengthList([(0, fg_code(WHITE, False))]),
                              RunLengthList([(0, bg_code(BLACK))]))]

        assert self.lines_gotten == expecting
                              
#XXX: not tested still - TriggerMatchingRealm
#also not tested: send() and default echoing in MatchingRealms

class FakeTelnetWithClosing:

    def __init__(self):
        self.closed = False

    def close(self):
        assert not self.closed
        self.closed = True

class TestOtherStuff:

    def setUp(self):
        self.realm = RootRealm(None)
        self.realm.telnet = self.telnet = FakeTelnetWithClosing()
    
    def test_ga_as_line_end_is_defaultly_True(self):
        assert self.realm.ga_as_line_end

    def test_close_closes_telnet(self):
        self.realm.close()
        assert self.telnet.closed

    def test_close_clears_telnet_attribute(self):
        self.realm.close()
        assert self.realm.telnet is None

    def test_close_is_a_noop_when_telnet_is_None(self):
        self.realm.telnet = None
        self.realm.close()
        assert self.realm.telnet is None

from mudpyl import realms
from mudpyl.gui.keychords import from_string
import traceback

class FakeTracebackModule:

    def __init__(self):
        self.calls = 0

    def print_exc(self):
        self.calls += 1

class Test_maybe_do_macro:

    def setUp(self):
        self.realm = RootRealm(None)
        self.realm.macros[from_string('X')] = self.macro
        self.realm.macros[from_string('C-M-X')] = self.bad_macro
        self.realm.macros[from_string('Z')] = self.simulated_grumpy_user
        self.macro_called_with = []

    def macro(self, realm):
        self.macro_called_with.append(realm)

    def bad_macro(self, realm):
        raise Exception

    def simulated_grumpy_user(self, realm):
        raise KeyboardInterrupt

    def test_returns_False_if_no_macro_found(self):
        res = self.realm.maybe_do_macro(from_string('Q'))
        assert not res

    def test_returns_True_if_a_macro_found(self):
        res = self.realm.maybe_do_macro(from_string('X'))
        assert res

    def test_calls_macro_with_itself(self):
        self.realm.maybe_do_macro(from_string('X'))
        assert len(self.macro_called_with) == 1
        assert self.macro_called_with[0] is self.realm

    def test_KeyboardInterrupt_is_not_caught(self):
        try:
            self.realm.maybe_do_macro(from_string('Z'))
        except KeyboardInterrupt:
            pass
        else:
            assert False

    def test_Exception_is_caught(self):
        tb = realms.traceback = FakeTracebackModule()

        self.realm.maybe_do_macro(from_string('C-M-X'))

        assert tb.calls

        realms.traceback = traceback

    def test_bad_macros_still_return_True(self):
        realms.traceback = FakeTracebackModule()
        res = self.realm.maybe_do_macro(from_string('C-M-X'))
        assert res
        realms.traceback = traceback