__copyright__ = """Copyright 2007 Sam Pointon"""

__license__ = """See LICENSE file."""

from mudpyl.net.nvt import make_string_sane

def test_removal_of_NUL():
    s = '\000foo\000bar'
    assert make_string_sane(s) == 'foobar'

def test_removal_of_BEL():
    s = '\007James\007 Bond'
    assert make_string_sane(s) == 'James Bond'

def test_backspace_handling_normal():
    s = 'fooX\010'
    res = make_string_sane(s)
    print res
    assert res == 'foo'

def test_backspace_handling_multiple():
    s = 'foobaz\010\010\010bar'
    res = make_string_sane(s)
    print res
    assert res == 'foobar'

def test_backspace_handling_no_previous_characters_no_blow_up():
    s = '\010'
    assert make_string_sane(s) == ''

def test_backspace_gone_too_far():
    s = 'foo\010\010\010\010'
    assert make_string_sane(s) == ''

def test_backspace_no_interference():
    #XXX um. Is this even right?
    s = 'fooX\000\010'
    res = make_string_sane(s)
    print res
    assert res == 'foo'

def test_HT_replacement():
    s = 'foo\011bar'
    assert make_string_sane(s) == 'foo    bar'

def test_HT_then_BS():
    s = 'foo\011\010bar'
    assert make_string_sane(s) == 'foobar'

def test_VT_removal():
    s = 'foo\013\013bar'
    assert make_string_sane(s) == 'foobar'

def test_FF_removal():
    s = 'foo\014bar'
    assert make_string_sane(s) == 'foobar'

from mudpyl.net.nvt import colour_pattern

def test_colour_pattern_matching_single():
    assert colour_pattern.search('\x1b[37m')

def test_colour_pattern_matching_multiple():
    assert colour_pattern.search('\x1b[37;41m')

from mudpyl.net.nvt import ColourCodeParser 
from mudpyl.colours import BLACK, CYAN, WHITE, fg_code, bg_code

def test_ColourCodeParser_fg_change():
    ccp = ColourCodeParser()
    inline = 'foo\x1b[30mbar'
    ml = ccp.parseline(inline)
    assert ml.fores.as_pruned_index_list() == [(0, fg_code(WHITE, False)), 
                                               (3, fg_code(BLACK, False))]
    assert ml.line == 'foobar'

def test_ColourCodeParser_bold_on():
    ccp = ColourCodeParser()
    inline = 'foo\x1b[1mbar'
    ml = ccp.parseline(inline)
    assert ml.fores.as_pruned_index_list() == [(0, fg_code(WHITE, False)),
                                               (3, fg_code(WHITE, True))]

def test_ColourCodeParser_bold_off():
    ccp = ColourCodeParser()
    inline = '\x1b[1mfoo\x1b[22mbar'
    ml = ccp.parseline(inline)
    assert ml.fores.as_pruned_index_list() == [(0, fg_code(WHITE, True)),
                                               (3, fg_code(WHITE, False))]

def test_ColourCodeParser_bold_on_and_off_remembers_colour():
    ccp = ColourCodeParser()
    inline = '\x1b[30;1mfoo\x1b[22mbar'
    ml = ccp.parseline(inline)
    assert ml.fores.as_pruned_index_list() == [(0, fg_code(BLACK, True)),
                                               (3, fg_code(BLACK, False))]

def test_ColourCodeParser_normalises_ANSI_colours():
    ccp = ColourCodeParser()
    inline = '\x1b[01mfoobar'
    ml = ccp.parseline(inline)
    assert ml.fores.as_pruned_index_list() == [(0, fg_code(WHITE, True))], \
           ml.fores.as_pruned_index_list()

#XXX: test resetting of colours

def test_ColourCodeParser_bg_change():
    ccp = ColourCodeParser()
    inline = 'foo\x1b[46mbar'
    ml = ccp.parseline(inline)
    assert ml.backs.as_pruned_index_list() == [(0, bg_code(BLACK)),
                                               (3, bg_code(CYAN))]
    assert ml.backs.as_populated_list() == [bg_code(BLACK)] * 3 + \
                                           [bg_code(CYAN)]
