"""A balance highlighter.

For: Achaea.
"""
from mudpyl.colours import HexFGCode
from mudpyl.triggers import non_binding_trigger

#The unused arguments are harmless.
#pylint: disable-msg=W0613

@non_binding_trigger("^You have recovered (?:equilibrium|balance on all "
                                                                  "limbs)\.$")
def balance_highlight(match, realm):
    """When we get balance or equilibrium back, set it to a garish green."""
    realm.alterer.change_fore(0, match.end(), HexFGCode(0x80, 0xFF, 0x80))

#pylint: enable-msg=W0613
