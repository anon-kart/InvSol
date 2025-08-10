# $ANTLR 3.5.3 SolidityInvariant.g 2025-06-12 12:41:29

import sys
import antlr3
from antlr3 import *
from antlr3.compat import set, frozenset

from antlr3.tree import *



import sys
import traceback

from antlr3 import *
from SolidityInvariantLexer import SolidityInvariantLexer
from SolidityAST import *

def primaryCombine(target, idlist, suffix):
    if suffix is None:
        res = AttributeCall()
        res.target = target
        res.call = idlist
    elif suffix[0] == '(':
        res = MethodCall()
        res.target = target
        res.call = idlist
        ss = suffix[1]
        res.args = ss if isinstance(ss, (list, tuple)) else [ss]
    elif suffix[0] == '[':
        res = ArrayReference()
        res.target = target
        res.call = idlist
        ss = suffix[1]
        res.args = ss if isinstance(ss, (list, tuple)) else [ss]
    return res

def selsCombine(target, sels):
    if len(sels) == 0:
        return target
    else:
        ss = sels[0]
        if len(ss) == 1:
            first = primaryCombine(target, [], ('[', ss[0]))
        elif ss[1] is None:
            first = primaryCombine(target, [ss[0]], None)
        else:
            first = primaryCombine(target, [ss[0]], ('(', ss[1]))
        return selsCombine(first, sels[1:])



# for convenience in actions
HIDDEN = BaseRecognizer.HIDDEN

# token types
EOF=-1
T__54=54
T__55=55
T__56=56
T__57=57
T__58=58
T__59=59
T__60=60
T__61=61
T__62=62
T__63=63
T__64=64
T__65=65
T__66=66
AMP=4
AMPAMP=5
BANG=6
BAR=7
BARBAR=8
BOOL=9
BOOLLIT=10
BYTES=11
CARET=12
COLON=13
COMMA=14
DOT=15
EQ=16
EQEQ=17
EscapeSequence=18
GE=19
GT=20
IDENTIFIER=21
INT=22
INT256=23
INTLIT=24
IdentifierPart=25
IdentifierStart=26
LBRACE=27
LBRACKET=28
LE=29
LINE_COMMENT=30
LPAREN=31
LSHIFT=32
LT=33
NOTEQ=34
NULL=35
PERCENT=36
PLUS=37
QUES=38
RBRACE=39
RBRACKET=40
RPAREN=41
RSHIFT=42
SEMI=43
SLASH=44
STAR=45
STRING=46
STRINGLIT=47
SUB=48
SUPER=49
THIS=50
TILDE=51
UINT256=52
WS=53

# token names
tokenNames = [
    "<invalid>", "<EOR>", "<DOWN>", "<UP>",
    "AMP", "AMPAMP", "BANG", "BAR", "BARBAR", "BOOL", "BOOLLIT", "BYTES",
    "CARET", "COLON", "COMMA", "DOT", "EQ", "EQEQ", "EscapeSequence", "GE",
    "GT", "IDENTIFIER", "INT", "INT256", "INTLIT", "IdentifierPart", "IdentifierStart",
    "LBRACE", "LBRACKET", "LE", "LINE_COMMENT", "LPAREN", "LSHIFT", "LT",
    "NOTEQ", "NULL", "PERCENT", "PLUS", "QUES", "RBRACE", "RBRACKET", "RPAREN",
    "RSHIFT", "SEMI", "SLASH", "STAR", "STRING", "STRINGLIT", "SUB", "SUPER",
    "THIS", "TILDE", "UINT256", "WS", "'<=!=>'", "'<=='", "'<==>'", "'==>'",
    "'\\\\exists'", "'\\\\forall'", "'\\\\old'", "'\\\\pre'", "'\\\\result'",
    "'address'", "'block'", "'msg'", "'tx'"
]




class SolidityInvariantParser(Parser):
    grammarFileName = "SolidityInvariant.g"
    api_version = 1
    tokenNames = tokenNames

    def __init__(self, input, state=None, *args, **kwargs):
        if state is None:
            state = RecognizerSharedState()

        super(SolidityInvariantParser, self).__init__(input, state, *args, **kwargs)

        self._state.ruleMemo = {}




        self.delegates = []

        self._adaptor = None
        self.adaptor = CommonTreeAdaptor()



    def getTreeAdaptor(self):
        return self._adaptor

    def setTreeAdaptor(self, adaptor):
        self._adaptor = adaptor

    adaptor = property(getTreeAdaptor, setTreeAdaptor)


    class solidityInvariant_return(ParserRuleReturnScope):
        def __init__(self):
            super(SolidityInvariantParser.solidityInvariant_return, self).__init__()

            self.result = None
            self.tree = None





    # $ANTLR start "solidityInvariant"
    # SolidityInvariant.g:56:1: solidityInvariant returns [result] : expression ';' ;
    def solidityInvariant(self, ):
        retval = self.solidityInvariant_return()
        retval.start = self.input.LT(1)

        solidityInvariant_StartIndex = self.input.index()

        root_0 = None

        char_literal2 = None
        expression1 = None

        char_literal2_tree = None

        success = False

        try:
            try:
                if self._state.backtracking > 0 and self.alreadyParsedRule(self.input, 1):
                    # for cached failed rules, alreadyParsedRule will raise an exception
                    success = True
                    return retval


                # SolidityInvariant.g:57:5: ( expression ';' )
                # SolidityInvariant.g:57:9: expression ';'
                pass
                root_0 = self._adaptor.nil()


                self._state.following.append(self.FOLLOW_expression_in_solidityInvariant73)
                expression1 = self.expression()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    self._adaptor.addChild(root_0, expression1.tree)


                char_literal2 = self.match(self.input, SEMI, self.FOLLOW_SEMI_in_solidityInvariant75)
                if self._state.backtracking == 0:
                    char_literal2_tree = self._adaptor.createWithPayload(char_literal2)
                    self._adaptor.addChild(root_0, char_literal2_tree)



                if self._state.backtracking == 0:
                    pass
                    retval.result =  ((expression1 is not None) and [expression1.result] or [None])[0]





                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                success = True


            except RecognitionException as re:
                self.recover(self.input, re)

        finally:
            if self._state.backtracking > 0:
                self.memoize(self.input, 1, solidityInvariant_StartIndex, success)


            pass
        return retval

    # $ANTLR end "solidityInvariant"


    class expression_return(ParserRuleReturnScope):
        def __init__(self):
            super(SolidityInvariantParser.expression_return, self).__init__()

            self.result = None
            self.tree = None





    # $ANTLR start "expression"
    # SolidityInvariant.g:61:1: expression returns [result] : conditionalExpression ;
    def expression(self, ):
        retval = self.expression_return()
        retval.start = self.input.LT(1)

        expression_StartIndex = self.input.index()

        root_0 = None

        conditionalExpression3 = None


        success = False

        try:
            try:
                if self._state.backtracking > 0 and self.alreadyParsedRule(self.input, 2):
                    # for cached failed rules, alreadyParsedRule will raise an exception
                    success = True
                    return retval


                # SolidityInvariant.g:62:5: ( conditionalExpression )
                # SolidityInvariant.g:62:9: conditionalExpression
                pass
                root_0 = self._adaptor.nil()


                self._state.following.append(self.FOLLOW_conditionalExpression_in_expression108)
                conditionalExpression3 = self.conditionalExpression()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    self._adaptor.addChild(root_0, conditionalExpression3.tree)


                if self._state.backtracking == 0:
                    pass
                    retval.result =  ((conditionalExpression3 is not None) and [conditionalExpression3.result] or [None])[0]





                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                success = True


            except RecognitionException as re:
                self.recover(self.input, re)

        finally:
            if self._state.backtracking > 0:
                self.memoize(self.input, 2, expression_StartIndex, success)


            pass
        return retval

    # $ANTLR end "expression"


    class conditionalExpression_return(ParserRuleReturnScope):
        def __init__(self):
            super(SolidityInvariantParser.conditionalExpression_return, self).__init__()

            self.result = None
            self.tree = None





    # $ANTLR start "conditionalExpression"
    # SolidityInvariant.g:66:1: conditionalExpression returns [result] : cnd= equivalenceExpression ( '?' th= expression ':' el= conditionalExpression )? ;
    def conditionalExpression(self, ):
        retval = self.conditionalExpression_return()
        retval.start = self.input.LT(1)

        conditionalExpression_StartIndex = self.input.index()

        root_0 = None

        char_literal4 = None
        char_literal5 = None
        cnd = None
        th = None
        el = None

        char_literal4_tree = None
        char_literal5_tree = None

        success = False

        try:
            try:
                if self._state.backtracking > 0 and self.alreadyParsedRule(self.input, 3):
                    # for cached failed rules, alreadyParsedRule will raise an exception
                    success = True
                    return retval


                # SolidityInvariant.g:67:5: (cnd= equivalenceExpression ( '?' th= expression ':' el= conditionalExpression )? )
                # SolidityInvariant.g:67:9: cnd= equivalenceExpression ( '?' th= expression ':' el= conditionalExpression )?
                pass
                root_0 = self._adaptor.nil()


                self._state.following.append(self.FOLLOW_equivalenceExpression_in_conditionalExpression143)
                cnd = self.equivalenceExpression()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    self._adaptor.addChild(root_0, cnd.tree)


                # SolidityInvariant.g:68:9: ( '?' th= expression ':' el= conditionalExpression )?
                alt1 = 2
                LA1_0 = self.input.LA(1)

                if (LA1_0 == QUES) :
                    LA1_1 = self.input.LA(2)

                    if (self.synpred1_SolidityInvariant()) :
                        alt1 = 1
                if alt1 == 1:
                    # SolidityInvariant.g:68:11: '?' th= expression ':' el= conditionalExpression
                    pass
                    char_literal4 = self.match(self.input, QUES, self.FOLLOW_QUES_in_conditionalExpression155)
                    if self._state.backtracking == 0:
                        char_literal4_tree = self._adaptor.createWithPayload(char_literal4)
                        self._adaptor.addChild(root_0, char_literal4_tree)



                    self._state.following.append(self.FOLLOW_expression_in_conditionalExpression159)
                    th = self.expression()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, th.tree)


                    char_literal5 = self.match(self.input, COLON, self.FOLLOW_COLON_in_conditionalExpression161)
                    if self._state.backtracking == 0:
                        char_literal5_tree = self._adaptor.createWithPayload(char_literal5)
                        self._adaptor.addChild(root_0, char_literal5_tree)



                    self._state.following.append(self.FOLLOW_conditionalExpression_in_conditionalExpression165)
                    el = self.conditionalExpression()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, el.tree)





                if self._state.backtracking == 0:
                    pass

                    if th is None:
                        retval.result = ((cnd is not None) and [cnd.result] or [None])[0]
                    else:
                        retval.result = ConditionalExpression()
                        retval.result.condition = ((cnd is not None) and [cnd.result] or [None])[0]
                        retval.result.then_exp = ((th is not None) and [th.result] or [None])[0]
                        retval.result.else_exp = ((el is not None) and [el.result] or [None])[0]






                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                success = True


            except RecognitionException as re:
                self.recover(self.input, re)

        finally:
            if self._state.backtracking > 0:
                self.memoize(self.input, 3, conditionalExpression_StartIndex, success)


            pass
        return retval

    # $ANTLR end "conditionalExpression"


    class equivalenceExpression_return(ParserRuleReturnScope):
        def __init__(self):
            super(SolidityInvariantParser.equivalenceExpression_return, self).__init__()

            self.result = None
            self.tree = None





    # $ANTLR start "equivalenceExpression"
    # SolidityInvariant.g:80:1: equivalenceExpression returns [result] : l= impliesExpression (eqOp= equivalenceOp r= impliesExpression )? ;
    def equivalenceExpression(self, ):
        retval = self.equivalenceExpression_return()
        retval.start = self.input.LT(1)

        equivalenceExpression_StartIndex = self.input.index()

        root_0 = None

        l = None
        eqOp = None
        r = None


        success = False

        try:
            try:
                if self._state.backtracking > 0 and self.alreadyParsedRule(self.input, 4):
                    # for cached failed rules, alreadyParsedRule will raise an exception
                    success = True
                    return retval


                # SolidityInvariant.g:81:5: (l= impliesExpression (eqOp= equivalenceOp r= impliesExpression )? )
                # SolidityInvariant.g:81:9: l= impliesExpression (eqOp= equivalenceOp r= impliesExpression )?
                pass
                root_0 = self._adaptor.nil()


                self._state.following.append(self.FOLLOW_impliesExpression_in_equivalenceExpression203)
                l = self.impliesExpression()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    self._adaptor.addChild(root_0, l.tree)


                # SolidityInvariant.g:82:9: (eqOp= equivalenceOp r= impliesExpression )?
                alt2 = 2
                LA2_0 = self.input.LA(1)

                if (LA2_0 == 56) :
                    LA2_1 = self.input.LA(2)

                    if (self.synpred2_SolidityInvariant()) :
                        alt2 = 1
                elif (LA2_0 == 54) :
                    LA2_2 = self.input.LA(2)

                    if (self.synpred2_SolidityInvariant()) :
                        alt2 = 1
                if alt2 == 1:
                    # SolidityInvariant.g:82:11: eqOp= equivalenceOp r= impliesExpression
                    pass
                    self._state.following.append(self.FOLLOW_equivalenceOp_in_equivalenceExpression217)
                    eqOp = self.equivalenceOp()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, eqOp.tree)


                    self._state.following.append(self.FOLLOW_impliesExpression_in_equivalenceExpression221)
                    r = self.impliesExpression()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, r.tree)





                if self._state.backtracking == 0:
                    pass

                    if r is None:
                        retval.result = ((l is not None) and [l.result] or [None])[0]
                    else:
                        ((eqOp is not None) and [eqOp.result] or [None])[0].left = ((l is not None) and [l.result] or [None])[0]
                        ((eqOp is not None) and [eqOp.result] or [None])[0].right = ((r is not None) and [r.result] or [None])[0]
                        retval.result = ((eqOp is not None) and [eqOp.result] or [None])[0]






                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                success = True


            except RecognitionException as re:
                self.recover(self.input, re)

        finally:
            if self._state.backtracking > 0:
                self.memoize(self.input, 4, equivalenceExpression_StartIndex, success)


            pass
        return retval

    # $ANTLR end "equivalenceExpression"


    class equivalenceOp_return(ParserRuleReturnScope):
        def __init__(self):
            super(SolidityInvariantParser.equivalenceOp_return, self).__init__()

            self.result = None
            self.tree = None





    # $ANTLR start "equivalenceOp"
    # SolidityInvariant.g:93:1: equivalenceOp returns [result] : ( '<==>' | '<=!=>' );
    def equivalenceOp(self, ):
        retval = self.equivalenceOp_return()
        retval.start = self.input.LT(1)

        equivalenceOp_StartIndex = self.input.index()

        root_0 = None

        string_literal6 = None
        string_literal7 = None

        string_literal6_tree = None
        string_literal7_tree = None

        success = False

        try:
            try:
                if self._state.backtracking > 0 and self.alreadyParsedRule(self.input, 5):
                    # for cached failed rules, alreadyParsedRule will raise an exception
                    success = True
                    return retval


                # SolidityInvariant.g:94:5: ( '<==>' | '<=!=>' )
                alt3 = 2
                LA3_0 = self.input.LA(1)

                if (LA3_0 == 56) :
                    alt3 = 1
                elif (LA3_0 == 54) :
                    alt3 = 2
                else:
                    if self._state.backtracking > 0:
                        raise BacktrackingFailed


                    nvae = NoViableAltException("", 3, 0, self.input)

                    raise nvae


                if alt3 == 1:
                    # SolidityInvariant.g:94:9: '<==>'
                    pass
                    root_0 = self._adaptor.nil()


                    string_literal6 = self.match(self.input, 56, self.FOLLOW_56_in_equivalenceOp257)
                    if self._state.backtracking == 0:
                        string_literal6_tree = self._adaptor.createWithPayload(string_literal6)
                        self._adaptor.addChild(root_0, string_literal6_tree)



                    if self._state.backtracking == 0:
                        pass
                        retval.result =  IffExpression()




                elif alt3 == 2:
                    # SolidityInvariant.g:95:9: '<=!=>'
                    pass
                    root_0 = self._adaptor.nil()


                    string_literal7 = self.match(self.input, 54, self.FOLLOW_54_in_equivalenceOp273)
                    if self._state.backtracking == 0:
                        string_literal7_tree = self._adaptor.createWithPayload(string_literal7)
                        self._adaptor.addChild(root_0, string_literal7_tree)



                    if self._state.backtracking == 0:
                        pass
                        retval.result =  NIffExpression()




                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                success = True


            except RecognitionException as re:
                self.recover(self.input, re)

        finally:
            if self._state.backtracking > 0:
                self.memoize(self.input, 5, equivalenceOp_StartIndex, success)


            pass
        return retval

    # $ANTLR end "equivalenceOp"


    class impliesExpression_return(ParserRuleReturnScope):
        def __init__(self):
            super(SolidityInvariantParser.impliesExpression_return, self).__init__()

            self.result = None
            self.tree = None





    # $ANTLR start "impliesExpression"
    # SolidityInvariant.g:98:1: impliesExpression returns [result] : (ant= logicalOrExpression ( '==>' ie= impliesNonBackwardExpression )* |left= logicalOrExpression ( '<==' right= logicalOrExpression )* );
    def impliesExpression(self, ):
        retval = self.impliesExpression_return()
        retval.start = self.input.LT(1)

        impliesExpression_StartIndex = self.input.index()

        root_0 = None

        string_literal8 = None
        string_literal9 = None
        ant = None
        ie = None
        left = None
        right = None

        string_literal8_tree = None
        string_literal9_tree = None

        success = False

        try:
            try:
                if self._state.backtracking > 0 and self.alreadyParsedRule(self.input, 6):
                    # for cached failed rules, alreadyParsedRule will raise an exception
                    success = True
                    return retval


                # SolidityInvariant.g:99:5: (ant= logicalOrExpression ( '==>' ie= impliesNonBackwardExpression )* |left= logicalOrExpression ( '<==' right= logicalOrExpression )* )
                alt6 = 2
                LA6 = self.input.LA(1)
                if LA6 == PLUS:
                    LA6_1 = self.input.LA(2)

                    if (self.synpred5_SolidityInvariant()) :
                        alt6 = 1
                    elif (True) :
                        alt6 = 2
                    else:
                        if self._state.backtracking > 0:
                            raise BacktrackingFailed


                        nvae = NoViableAltException("", 6, 1, self.input)

                        raise nvae


                elif LA6 == SUB:
                    LA6_2 = self.input.LA(2)

                    if (self.synpred5_SolidityInvariant()) :
                        alt6 = 1
                    elif (True) :
                        alt6 = 2
                    else:
                        if self._state.backtracking > 0:
                            raise BacktrackingFailed


                        nvae = NoViableAltException("", 6, 2, self.input)

                        raise nvae


                elif LA6 == BANG:
                    LA6_3 = self.input.LA(2)

                    if (self.synpred5_SolidityInvariant()) :
                        alt6 = 1
                    elif (True) :
                        alt6 = 2
                    else:
                        if self._state.backtracking > 0:
                            raise BacktrackingFailed


                        nvae = NoViableAltException("", 6, 3, self.input)

                        raise nvae


                elif LA6 == TILDE:
                    LA6_4 = self.input.LA(2)

                    if (self.synpred5_SolidityInvariant()) :
                        alt6 = 1
                    elif (True) :
                        alt6 = 2
                    else:
                        if self._state.backtracking > 0:
                            raise BacktrackingFailed


                        nvae = NoViableAltException("", 6, 4, self.input)

                        raise nvae


                elif LA6 == IDENTIFIER:
                    LA6_5 = self.input.LA(2)

                    if (self.synpred5_SolidityInvariant()) :
                        alt6 = 1
                    elif (True) :
                        alt6 = 2
                    else:
                        if self._state.backtracking > 0:
                            raise BacktrackingFailed


                        nvae = NoViableAltException("", 6, 5, self.input)

                        raise nvae


                elif LA6 == THIS or LA6 == 63 or LA6 == 64 or LA6 == 65 or LA6 == 66:
                    LA6_6 = self.input.LA(2)

                    if (self.synpred5_SolidityInvariant()) :
                        alt6 = 1
                    elif (True) :
                        alt6 = 2
                    else:
                        if self._state.backtracking > 0:
                            raise BacktrackingFailed


                        nvae = NoViableAltException("", 6, 6, self.input)

                        raise nvae


                elif LA6 == INTLIT:
                    LA6_7 = self.input.LA(2)

                    if (self.synpred5_SolidityInvariant()) :
                        alt6 = 1
                    elif (True) :
                        alt6 = 2
                    else:
                        if self._state.backtracking > 0:
                            raise BacktrackingFailed


                        nvae = NoViableAltException("", 6, 7, self.input)

                        raise nvae


                elif LA6 == BOOLLIT:
                    LA6_8 = self.input.LA(2)

                    if (self.synpred5_SolidityInvariant()) :
                        alt6 = 1
                    elif (True) :
                        alt6 = 2
                    else:
                        if self._state.backtracking > 0:
                            raise BacktrackingFailed


                        nvae = NoViableAltException("", 6, 8, self.input)

                        raise nvae


                elif LA6 == STRINGLIT:
                    LA6_9 = self.input.LA(2)

                    if (self.synpred5_SolidityInvariant()) :
                        alt6 = 1
                    elif (True) :
                        alt6 = 2
                    else:
                        if self._state.backtracking > 0:
                            raise BacktrackingFailed


                        nvae = NoViableAltException("", 6, 9, self.input)

                        raise nvae


                elif LA6 == LPAREN:
                    LA6_10 = self.input.LA(2)

                    if (self.synpred5_SolidityInvariant()) :
                        alt6 = 1
                    elif (True) :
                        alt6 = 2
                    else:
                        if self._state.backtracking > 0:
                            raise BacktrackingFailed


                        nvae = NoViableAltException("", 6, 10, self.input)

                        raise nvae


                elif LA6 == 62:
                    LA6_11 = self.input.LA(2)

                    if (self.synpred5_SolidityInvariant()) :
                        alt6 = 1
                    elif (True) :
                        alt6 = 2
                    else:
                        if self._state.backtracking > 0:
                            raise BacktrackingFailed


                        nvae = NoViableAltException("", 6, 11, self.input)

                        raise nvae


                elif LA6 == 60 or LA6 == 61:
                    LA6_12 = self.input.LA(2)

                    if (self.synpred5_SolidityInvariant()) :
                        alt6 = 1
                    elif (True) :
                        alt6 = 2
                    else:
                        if self._state.backtracking > 0:
                            raise BacktrackingFailed


                        nvae = NoViableAltException("", 6, 12, self.input)

                        raise nvae


                elif LA6 == 59:
                    LA6_13 = self.input.LA(2)

                    if (self.synpred5_SolidityInvariant()) :
                        alt6 = 1
                    elif (True) :
                        alt6 = 2
                    else:
                        if self._state.backtracking > 0:
                            raise BacktrackingFailed


                        nvae = NoViableAltException("", 6, 13, self.input)

                        raise nvae


                elif LA6 == 58:
                    LA6_14 = self.input.LA(2)

                    if (self.synpred5_SolidityInvariant()) :
                        alt6 = 1
                    elif (True) :
                        alt6 = 2
                    else:
                        if self._state.backtracking > 0:
                            raise BacktrackingFailed


                        nvae = NoViableAltException("", 6, 14, self.input)

                        raise nvae


                else:
                    if self._state.backtracking > 0:
                        raise BacktrackingFailed


                    nvae = NoViableAltException("", 6, 0, self.input)

                    raise nvae


                if alt6 == 1:
                    # SolidityInvariant.g:99:9: ant= logicalOrExpression ( '==>' ie= impliesNonBackwardExpression )*
                    pass
                    root_0 = self._adaptor.nil()


                    self._state.following.append(self.FOLLOW_logicalOrExpression_in_impliesExpression303)
                    ant = self.logicalOrExpression()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, ant.tree)


                    if self._state.backtracking == 0:
                        pass

                        exprs = [((ant is not None) and [ant.result] or [None])[0]]




                    # SolidityInvariant.g:103:9: ( '==>' ie= impliesNonBackwardExpression )*
                    while True: #loop4
                        alt4 = 2
                        LA4_0 = self.input.LA(1)

                        if (LA4_0 == 57) :
                            LA4_2 = self.input.LA(2)

                            if (self.synpred4_SolidityInvariant()) :
                                alt4 = 1




                        if alt4 == 1:
                            # SolidityInvariant.g:103:10: '==>' ie= impliesNonBackwardExpression
                            pass
                            string_literal8 = self.match(self.input, 57, self.FOLLOW_57_in_impliesExpression324)
                            if self._state.backtracking == 0:
                                string_literal8_tree = self._adaptor.createWithPayload(string_literal8)
                                self._adaptor.addChild(root_0, string_literal8_tree)



                            self._state.following.append(self.FOLLOW_impliesNonBackwardExpression_in_impliesExpression328)
                            ie = self.impliesNonBackwardExpression()

                            self._state.following.pop()
                            if self._state.backtracking == 0:
                                self._adaptor.addChild(root_0, ie.tree)


                            if self._state.backtracking == 0:
                                pass

                                exprs.append(((ie is not None) and [ie.result] or [None])[0])





                        else:
                            break #loop4


                    if self._state.backtracking == 0:
                        pass

                        if len(exprs) == 1:
                            retval.result = exprs[0]
                        elif len(exprs) >= 2:
                            retval.result = ImpliesExpression()
                            retval.result.aggregate(exprs)
                        else:
                            raise Exception("Invalid impliesExpression: no expressions to aggregate")





                elif alt6 == 2:
                    # SolidityInvariant.g:117:9: left= logicalOrExpression ( '<==' right= logicalOrExpression )*
                    pass
                    root_0 = self._adaptor.nil()


                    self._state.following.append(self.FOLLOW_logicalOrExpression_in_impliesExpression375)
                    left = self.logicalOrExpression()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, left.tree)


                    if self._state.backtracking == 0:
                        pass

                        exprs = [((left is not None) and [left.result] or [None])[0]]




                    # SolidityInvariant.g:121:9: ( '<==' right= logicalOrExpression )*
                    while True: #loop5
                        alt5 = 2
                        LA5_0 = self.input.LA(1)

                        if (LA5_0 == 55) :
                            LA5_2 = self.input.LA(2)

                            if (self.synpred6_SolidityInvariant()) :
                                alt5 = 1




                        if alt5 == 1:
                            # SolidityInvariant.g:121:10: '<==' right= logicalOrExpression
                            pass
                            string_literal9 = self.match(self.input, 55, self.FOLLOW_55_in_impliesExpression396)
                            if self._state.backtracking == 0:
                                string_literal9_tree = self._adaptor.createWithPayload(string_literal9)
                                self._adaptor.addChild(root_0, string_literal9_tree)



                            self._state.following.append(self.FOLLOW_logicalOrExpression_in_impliesExpression400)
                            right = self.logicalOrExpression()

                            self._state.following.pop()
                            if self._state.backtracking == 0:
                                self._adaptor.addChild(root_0, right.tree)


                            if self._state.backtracking == 0:
                                pass

                                exprs.append(((right is not None) and [right.result] or [None])[0])





                        else:
                            break #loop5


                    if self._state.backtracking == 0:
                        pass

                        # Optional: implement reverse implication logic
                        retval.result = exprs[0]





                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                success = True


            except RecognitionException as re:
                self.recover(self.input, re)

        finally:
            if self._state.backtracking > 0:
                self.memoize(self.input, 6, impliesExpression_StartIndex, success)


            pass
        return retval

    # $ANTLR end "impliesExpression"


    class impliesNonBackwardExpression_return(ParserRuleReturnScope):
        def __init__(self):
            super(SolidityInvariantParser.impliesNonBackwardExpression_return, self).__init__()

            self.result = None
            self.tree = None





    # $ANTLR start "impliesNonBackwardExpression"
    # SolidityInvariant.g:132:1: impliesNonBackwardExpression returns [result] : ant= logicalOrExpression ( '==>' ie= impliesNonBackwardExpression )* ;
    def impliesNonBackwardExpression(self, ):
        retval = self.impliesNonBackwardExpression_return()
        retval.start = self.input.LT(1)

        impliesNonBackwardExpression_StartIndex = self.input.index()

        root_0 = None

        string_literal10 = None
        ant = None
        ie = None

        string_literal10_tree = None

        success = False

        try:
            try:
                if self._state.backtracking > 0 and self.alreadyParsedRule(self.input, 7):
                    # for cached failed rules, alreadyParsedRule will raise an exception
                    success = True
                    return retval


                # SolidityInvariant.g:133:5: (ant= logicalOrExpression ( '==>' ie= impliesNonBackwardExpression )* )
                # SolidityInvariant.g:133:9: ant= logicalOrExpression ( '==>' ie= impliesNonBackwardExpression )*
                pass
                root_0 = self._adaptor.nil()


                self._state.following.append(self.FOLLOW_logicalOrExpression_in_impliesNonBackwardExpression460)
                ant = self.logicalOrExpression()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    self._adaptor.addChild(root_0, ant.tree)


                if self._state.backtracking == 0:
                    pass

                    exprs = [((ant is not None) and [ant.result] or [None])[0]]




                # SolidityInvariant.g:137:9: ( '==>' ie= impliesNonBackwardExpression )*
                while True: #loop7
                    alt7 = 2
                    LA7_0 = self.input.LA(1)

                    if (LA7_0 == 57) :
                        LA7_2 = self.input.LA(2)

                        if (self.synpred7_SolidityInvariant()) :
                            alt7 = 1




                    if alt7 == 1:
                        # SolidityInvariant.g:137:10: '==>' ie= impliesNonBackwardExpression
                        pass
                        string_literal10 = self.match(self.input, 57, self.FOLLOW_57_in_impliesNonBackwardExpression481)
                        if self._state.backtracking == 0:
                            string_literal10_tree = self._adaptor.createWithPayload(string_literal10)
                            self._adaptor.addChild(root_0, string_literal10_tree)



                        self._state.following.append(self.FOLLOW_impliesNonBackwardExpression_in_impliesNonBackwardExpression485)
                        ie = self.impliesNonBackwardExpression()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            self._adaptor.addChild(root_0, ie.tree)


                        if self._state.backtracking == 0:
                            pass

                            exprs.append(((ie is not None) and [ie.result] or [None])[0])





                    else:
                        break #loop7


                if self._state.backtracking == 0:
                    pass

                    if len(exprs) == 1:
                        retval.result = exprs[0]
                    elif len(exprs) >= 2:
                        retval.result = ImpliesExpression()
                        retval.result.aggregate(exprs)
                    else:
                        raise Exception("Invalid impliesNonBackwardExpression: no expressions to aggregate")






                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                success = True


            except RecognitionException as re:
                self.recover(self.input, re)

        finally:
            if self._state.backtracking > 0:
                self.memoize(self.input, 7, impliesNonBackwardExpression_StartIndex, success)


            pass
        return retval

    # $ANTLR end "impliesNonBackwardExpression"


    class logicalOrExpression_return(ParserRuleReturnScope):
        def __init__(self):
            super(SolidityInvariantParser.logicalOrExpression_return, self).__init__()

            self.result = None
            self.tree = None





    # $ANTLR start "logicalOrExpression"
    # SolidityInvariant.g:153:1: logicalOrExpression returns [result] : l= logicalAndExpression ( '||' r= logicalAndExpression )* ;
    def logicalOrExpression(self, ):
        retval = self.logicalOrExpression_return()
        retval.start = self.input.LT(1)

        logicalOrExpression_StartIndex = self.input.index()

        root_0 = None

        string_literal11 = None
        l = None
        r = None

        string_literal11_tree = None

        success = False

        try:
            try:
                if self._state.backtracking > 0 and self.alreadyParsedRule(self.input, 8):
                    # for cached failed rules, alreadyParsedRule will raise an exception
                    success = True
                    return retval


                # SolidityInvariant.g:154:5: (l= logicalAndExpression ( '||' r= logicalAndExpression )* )
                # SolidityInvariant.g:154:9: l= logicalAndExpression ( '||' r= logicalAndExpression )*
                pass
                root_0 = self._adaptor.nil()


                self._state.following.append(self.FOLLOW_logicalAndExpression_in_logicalOrExpression545)
                l = self.logicalAndExpression()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    self._adaptor.addChild(root_0, l.tree)


                # SolidityInvariant.g:155:9: ( '||' r= logicalAndExpression )*
                while True: #loop8
                    alt8 = 2
                    LA8_0 = self.input.LA(1)

                    if (LA8_0 == BARBAR) :
                        LA8_2 = self.input.LA(2)

                        if (self.synpred8_SolidityInvariant()) :
                            alt8 = 1




                    if alt8 == 1:
                        # SolidityInvariant.g:155:11: '||' r= logicalAndExpression
                        pass
                        string_literal11 = self.match(self.input, BARBAR, self.FOLLOW_BARBAR_in_logicalOrExpression557)
                        if self._state.backtracking == 0:
                            string_literal11_tree = self._adaptor.createWithPayload(string_literal11)
                            self._adaptor.addChild(root_0, string_literal11_tree)



                        self._state.following.append(self.FOLLOW_logicalAndExpression_in_logicalOrExpression561)
                        r = self.logicalAndExpression()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            self._adaptor.addChild(root_0, r.tree)



                    else:
                        break #loop8


                if self._state.backtracking == 0:
                    pass

                    r_exprs = [r.result for r in r] if r is not None else []
                    props = [((l is not None) and [l.result] or [None])[0]] + r_exprs
                    if len(props) == 1:
                        retval.result = props[0]
                    else:
                        retval.result = OrExpression()
                        retval.result.aggregate(props)






                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                success = True


            except RecognitionException as re:
                self.recover(self.input, re)

        finally:
            if self._state.backtracking > 0:
                self.memoize(self.input, 8, logicalOrExpression_StartIndex, success)


            pass
        return retval

    # $ANTLR end "logicalOrExpression"


    class logicalAndExpression_return(ParserRuleReturnScope):
        def __init__(self):
            super(SolidityInvariantParser.logicalAndExpression_return, self).__init__()

            self.result = None
            self.tree = None





    # $ANTLR start "logicalAndExpression"
    # SolidityInvariant.g:168:1: logicalAndExpression returns [result] : l= bitwiseOrExpression ( '&&' r= equalityExpression )* ;
    def logicalAndExpression(self, ):
        retval = self.logicalAndExpression_return()
        retval.start = self.input.LT(1)

        logicalAndExpression_StartIndex = self.input.index()

        root_0 = None

        string_literal12 = None
        l = None
        r = None

        string_literal12_tree = None

        success = False

        try:
            try:
                if self._state.backtracking > 0 and self.alreadyParsedRule(self.input, 9):
                    # for cached failed rules, alreadyParsedRule will raise an exception
                    success = True
                    return retval


                # SolidityInvariant.g:169:5: (l= bitwiseOrExpression ( '&&' r= equalityExpression )* )
                # SolidityInvariant.g:169:9: l= bitwiseOrExpression ( '&&' r= equalityExpression )*
                pass
                root_0 = self._adaptor.nil()


                self._state.following.append(self.FOLLOW_bitwiseOrExpression_in_logicalAndExpression600)
                l = self.bitwiseOrExpression()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    self._adaptor.addChild(root_0, l.tree)


                # SolidityInvariant.g:170:9: ( '&&' r= equalityExpression )*
                while True: #loop9
                    alt9 = 2
                    LA9_0 = self.input.LA(1)

                    if (LA9_0 == AMPAMP) :
                        LA9_2 = self.input.LA(2)

                        if (self.synpred9_SolidityInvariant()) :
                            alt9 = 1




                    if alt9 == 1:
                        # SolidityInvariant.g:170:11: '&&' r= equalityExpression
                        pass
                        string_literal12 = self.match(self.input, AMPAMP, self.FOLLOW_AMPAMP_in_logicalAndExpression612)
                        if self._state.backtracking == 0:
                            string_literal12_tree = self._adaptor.createWithPayload(string_literal12)
                            self._adaptor.addChild(root_0, string_literal12_tree)



                        self._state.following.append(self.FOLLOW_equalityExpression_in_logicalAndExpression616)
                        r = self.equalityExpression()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            self._adaptor.addChild(root_0, r.tree)



                    else:
                        break #loop9


                if self._state.backtracking == 0:
                    pass

                    r_exprs = [r.result for r in r] if r is not None else []
                    props = [((l is not None) and [l.result] or [None])[0]] + r_exprs
                    if len(props) == 1:
                        retval.result = props[0]
                    else:
                        retval.result = AndExpression()
                        retval.result.aggregate(props)






                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                success = True


            except RecognitionException as re:
                self.recover(self.input, re)

        finally:
            if self._state.backtracking > 0:
                self.memoize(self.input, 9, logicalAndExpression_StartIndex, success)


            pass
        return retval

    # $ANTLR end "logicalAndExpression"


    class equalityExpression_return(ParserRuleReturnScope):
        def __init__(self):
            super(SolidityInvariantParser.equalityExpression_return, self).__init__()

            self.result = None
            self.tree = None





    # $ANTLR start "equalityExpression"
    # SolidityInvariant.g:183:1: equalityExpression returns [result] : l= relationalExpression (op= ( '==' | '!=' ) r= relationalExpression )* ;
    def equalityExpression(self, ):
        retval = self.equalityExpression_return()
        retval.start = self.input.LT(1)

        equalityExpression_StartIndex = self.input.index()

        root_0 = None

        op = None
        l = None
        r = None

        op_tree = None

        success = False

        try:
            try:
                if self._state.backtracking > 0 and self.alreadyParsedRule(self.input, 10):
                    # for cached failed rules, alreadyParsedRule will raise an exception
                    success = True
                    return retval


                # SolidityInvariant.g:184:5: (l= relationalExpression (op= ( '==' | '!=' ) r= relationalExpression )* )
                # SolidityInvariant.g:184:9: l= relationalExpression (op= ( '==' | '!=' ) r= relationalExpression )*
                pass
                root_0 = self._adaptor.nil()


                self._state.following.append(self.FOLLOW_relationalExpression_in_equalityExpression655)
                l = self.relationalExpression()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    self._adaptor.addChild(root_0, l.tree)


                if self._state.backtracking == 0:
                    pass

                    exprs = [((l is not None) and [l.result] or [None])[0]]
                    ops = []




                # SolidityInvariant.g:189:9: (op= ( '==' | '!=' ) r= relationalExpression )*
                while True: #loop10
                    alt10 = 2
                    LA10_0 = self.input.LA(1)

                    if (LA10_0 == EQEQ or LA10_0 == NOTEQ) :
                        LA10_2 = self.input.LA(2)

                        if (self.synpred11_SolidityInvariant()) :
                            alt10 = 1




                    if alt10 == 1:
                        # SolidityInvariant.g:189:10: op= ( '==' | '!=' ) r= relationalExpression
                        pass
                        op = self.input.LT(1)

                        if self.input.LA(1) == EQEQ or self.input.LA(1) == NOTEQ:
                            self.input.consume()
                            if self._state.backtracking == 0:
                                self._adaptor.addChild(root_0, self._adaptor.createWithPayload(op))

                            self._state.errorRecovery = False


                        else:
                            if self._state.backtracking > 0:
                                raise BacktrackingFailed


                            mse = MismatchedSetException(None, self.input)
                            raise mse



                        self._state.following.append(self.FOLLOW_relationalExpression_in_equalityExpression688)
                        r = self.relationalExpression()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            self._adaptor.addChild(root_0, r.tree)


                        if self._state.backtracking == 0:
                            pass

                            ops.append(op.text)
                            exprs.append(r.result)





                    else:
                        break #loop10


                if self._state.backtracking == 0:
                    pass

                    if not ops:
                        retval.result = exprs[0]
                    else:
                        zipped = [(exprs[i], ops[i], exprs[i+1]) for i in range(len(ops))]
                        retval.result = BinaryExpression()
                        retval.result.aggregate(zipped)






                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                success = True


            except RecognitionException as re:
                self.recover(self.input, re)

        finally:
            if self._state.backtracking > 0:
                self.memoize(self.input, 10, equalityExpression_StartIndex, success)


            pass
        return retval

    # $ANTLR end "equalityExpression"


    class relationalExpression_return(ParserRuleReturnScope):
        def __init__(self):
            super(SolidityInvariantParser.relationalExpression_return, self).__init__()

            self.result = None
            self.tree = None





    # $ANTLR start "relationalExpression"
    # SolidityInvariant.g:205:1: relationalExpression returns [result] : l= shiftExpression (op= ( '<' | '<=' | '>' | '>=' ) r= shiftExpression )* ;
    def relationalExpression(self, ):
        retval = self.relationalExpression_return()
        retval.start = self.input.LT(1)

        relationalExpression_StartIndex = self.input.index()

        root_0 = None

        op = None
        l = None
        r = None

        op_tree = None

        success = False

        try:
            try:
                if self._state.backtracking > 0 and self.alreadyParsedRule(self.input, 11):
                    # for cached failed rules, alreadyParsedRule will raise an exception
                    success = True
                    return retval


                # SolidityInvariant.g:206:5: (l= shiftExpression (op= ( '<' | '<=' | '>' | '>=' ) r= shiftExpression )* )
                # SolidityInvariant.g:206:9: l= shiftExpression (op= ( '<' | '<=' | '>' | '>=' ) r= shiftExpression )*
                pass
                root_0 = self._adaptor.nil()


                self._state.following.append(self.FOLLOW_shiftExpression_in_relationalExpression748)
                l = self.shiftExpression()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    self._adaptor.addChild(root_0, l.tree)


                if self._state.backtracking == 0:
                    pass

                    exprs = [((l is not None) and [l.result] or [None])[0]]
                    ops = []




                # SolidityInvariant.g:211:9: (op= ( '<' | '<=' | '>' | '>=' ) r= shiftExpression )*
                while True: #loop11
                    alt11 = 2
                    LA11_0 = self.input.LA(1)

                    if ((GE <= LA11_0 <= GT) or LA11_0 == LE or LA11_0 == LT) :
                        LA11_2 = self.input.LA(2)

                        if (self.synpred15_SolidityInvariant()) :
                            alt11 = 1




                    if alt11 == 1:
                        # SolidityInvariant.g:212:13: op= ( '<' | '<=' | '>' | '>=' ) r= shiftExpression
                        pass
                        op = self.input.LT(1)

                        if (GE <= self.input.LA(1) <= GT) or self.input.LA(1) == LE or self.input.LA(1) == LT:
                            self.input.consume()
                            if self._state.backtracking == 0:
                                self._adaptor.addChild(root_0, self._adaptor.createWithPayload(op))

                            self._state.errorRecovery = False


                        else:
                            if self._state.backtracking > 0:
                                raise BacktrackingFailed


                            mse = MismatchedSetException(None, self.input)
                            raise mse



                        self._state.following.append(self.FOLLOW_shiftExpression_in_relationalExpression802)
                        r = self.shiftExpression()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            self._adaptor.addChild(root_0, r.tree)


                        if self._state.backtracking == 0:
                            pass

                            ops.append(op.text)
                            exprs.append(r.result)





                    else:
                        break #loop11


                if self._state.backtracking == 0:
                    pass

                    if not ops:
                        retval.result = exprs[0]
                    else:
                        zipped = [(exprs[i], ops[i], exprs[i+1]) for i in range(len(ops))]
                        retval.result = BinaryExpression()
                        retval.result.aggregate(zipped)






                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                success = True


            except RecognitionException as re:
                self.recover(self.input, re)

        finally:
            if self._state.backtracking > 0:
                self.memoize(self.input, 11, relationalExpression_StartIndex, success)


            pass
        return retval

    # $ANTLR end "relationalExpression"


    class shiftExpression_return(ParserRuleReturnScope):
        def __init__(self):
            super(SolidityInvariantParser.shiftExpression_return, self).__init__()

            self.result = None
            self.tree = None





    # $ANTLR start "shiftExpression"
    # SolidityInvariant.g:228:1: shiftExpression returns [result] : l= additiveExpression (op= ( '<<' | '>>' ) r= additiveExpression )* ;
    def shiftExpression(self, ):
        retval = self.shiftExpression_return()
        retval.start = self.input.LT(1)

        shiftExpression_StartIndex = self.input.index()

        root_0 = None

        op = None
        l = None
        r = None

        op_tree = None

        success = False

        try:
            try:
                if self._state.backtracking > 0 and self.alreadyParsedRule(self.input, 12):
                    # for cached failed rules, alreadyParsedRule will raise an exception
                    success = True
                    return retval


                # SolidityInvariant.g:229:5: (l= additiveExpression (op= ( '<<' | '>>' ) r= additiveExpression )* )
                # SolidityInvariant.g:229:9: l= additiveExpression (op= ( '<<' | '>>' ) r= additiveExpression )*
                pass
                root_0 = self._adaptor.nil()


                self._state.following.append(self.FOLLOW_additiveExpression_in_shiftExpression862)
                l = self.additiveExpression()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    self._adaptor.addChild(root_0, l.tree)


                if self._state.backtracking == 0:
                    pass

                    exprs = [((l is not None) and [l.result] or [None])[0]]
                    ops = []




                # SolidityInvariant.g:234:9: (op= ( '<<' | '>>' ) r= additiveExpression )*
                while True: #loop12
                    alt12 = 2
                    LA12_0 = self.input.LA(1)

                    if (LA12_0 == LSHIFT or LA12_0 == RSHIFT) :
                        LA12_2 = self.input.LA(2)

                        if (self.synpred17_SolidityInvariant()) :
                            alt12 = 1




                    if alt12 == 1:
                        # SolidityInvariant.g:235:13: op= ( '<<' | '>>' ) r= additiveExpression
                        pass
                        op = self.input.LT(1)

                        if self.input.LA(1) == LSHIFT or self.input.LA(1) == RSHIFT:
                            self.input.consume()
                            if self._state.backtracking == 0:
                                self._adaptor.addChild(root_0, self._adaptor.createWithPayload(op))

                            self._state.errorRecovery = False


                        else:
                            if self._state.backtracking > 0:
                                raise BacktrackingFailed


                            mse = MismatchedSetException(None, self.input)
                            raise mse



                        self._state.following.append(self.FOLLOW_additiveExpression_in_shiftExpression908)
                        r = self.additiveExpression()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            self._adaptor.addChild(root_0, r.tree)


                        if self._state.backtracking == 0:
                            pass

                            ops.append(op.text)
                            exprs.append(r.result)





                    else:
                        break #loop12


                if self._state.backtracking == 0:
                    pass

                    if len(ops) == 0:
                        retval.result = exprs[0]
                    else:
                        zipped = [(exprs[i], ops[i], exprs[i+1]) for i in range(len(ops))]
                        retval.result = BinaryExpression()
                        retval.result.aggregate(zipped)






                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                success = True


            except RecognitionException as re:
                self.recover(self.input, re)

        finally:
            if self._state.backtracking > 0:
                self.memoize(self.input, 12, shiftExpression_StartIndex, success)


            pass
        return retval

    # $ANTLR end "shiftExpression"


    class additiveExpression_return(ParserRuleReturnScope):
        def __init__(self):
            super(SolidityInvariantParser.additiveExpression_return, self).__init__()

            self.result = None
            self.tree = None





    # $ANTLR start "additiveExpression"
    # SolidityInvariant.g:251:1: additiveExpression returns [result] : l= multiplicativeExpression (op= ( '+' | '-' ) r= multiplicativeExpression )* ;
    def additiveExpression(self, ):
        retval = self.additiveExpression_return()
        retval.start = self.input.LT(1)

        additiveExpression_StartIndex = self.input.index()

        root_0 = None

        op = None
        l = None
        r = None

        op_tree = None

        success = False

        try:
            try:
                if self._state.backtracking > 0 and self.alreadyParsedRule(self.input, 13):
                    # for cached failed rules, alreadyParsedRule will raise an exception
                    success = True
                    return retval


                # SolidityInvariant.g:252:5: (l= multiplicativeExpression (op= ( '+' | '-' ) r= multiplicativeExpression )* )
                # SolidityInvariant.g:252:9: l= multiplicativeExpression (op= ( '+' | '-' ) r= multiplicativeExpression )*
                pass
                root_0 = self._adaptor.nil()


                self._state.following.append(self.FOLLOW_multiplicativeExpression_in_additiveExpression968)
                l = self.multiplicativeExpression()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    self._adaptor.addChild(root_0, l.tree)


                if self._state.backtracking == 0:
                    pass

                    exprs = [((l is not None) and [l.result] or [None])[0]]
                    ops = []




                # SolidityInvariant.g:257:9: (op= ( '+' | '-' ) r= multiplicativeExpression )*
                while True: #loop13
                    alt13 = 2
                    LA13_0 = self.input.LA(1)

                    if (LA13_0 == PLUS or LA13_0 == SUB) :
                        LA13_2 = self.input.LA(2)

                        if (self.synpred19_SolidityInvariant()) :
                            alt13 = 1




                    if alt13 == 1:
                        # SolidityInvariant.g:258:13: op= ( '+' | '-' ) r= multiplicativeExpression
                        pass
                        op = self.input.LT(1)

                        if self.input.LA(1) == PLUS or self.input.LA(1) == SUB:
                            self.input.consume()
                            if self._state.backtracking == 0:
                                self._adaptor.addChild(root_0, self._adaptor.createWithPayload(op))

                            self._state.errorRecovery = False


                        else:
                            if self._state.backtracking > 0:
                                raise BacktrackingFailed


                            mse = MismatchedSetException(None, self.input)
                            raise mse



                        self._state.following.append(self.FOLLOW_multiplicativeExpression_in_additiveExpression1014)
                        r = self.multiplicativeExpression()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            self._adaptor.addChild(root_0, r.tree)


                        if self._state.backtracking == 0:
                            pass

                            ops.append(op.text)
                            exprs.append(r.result)





                    else:
                        break #loop13


                if self._state.backtracking == 0:
                    pass

                    if len(ops) == 0:
                        retval.result = exprs[0]
                    else:
                        zipped = [(exprs[i], ops[i], exprs[i+1]) for i in range(len(ops))]
                        retval.result = BinaryExpression()
                        retval.result.aggregate(zipped)






                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                success = True


            except RecognitionException as re:
                self.recover(self.input, re)

        finally:
            if self._state.backtracking > 0:
                self.memoize(self.input, 13, additiveExpression_StartIndex, success)


            pass
        return retval

    # $ANTLR end "additiveExpression"


    class multiplicativeExpression_return(ParserRuleReturnScope):
        def __init__(self):
            super(SolidityInvariantParser.multiplicativeExpression_return, self).__init__()

            self.result = None
            self.tree = None





    # $ANTLR start "multiplicativeExpression"
    # SolidityInvariant.g:274:1: multiplicativeExpression returns [result] : l= unaryExpression (op= ( '*' | '/' | '%' ) r= unaryExpression )* ;
    def multiplicativeExpression(self, ):
        retval = self.multiplicativeExpression_return()
        retval.start = self.input.LT(1)

        multiplicativeExpression_StartIndex = self.input.index()

        root_0 = None

        op = None
        l = None
        r = None

        op_tree = None

        success = False

        try:
            try:
                if self._state.backtracking > 0 and self.alreadyParsedRule(self.input, 14):
                    # for cached failed rules, alreadyParsedRule will raise an exception
                    success = True
                    return retval


                # SolidityInvariant.g:275:5: (l= unaryExpression (op= ( '*' | '/' | '%' ) r= unaryExpression )* )
                # SolidityInvariant.g:275:9: l= unaryExpression (op= ( '*' | '/' | '%' ) r= unaryExpression )*
                pass
                root_0 = self._adaptor.nil()


                self._state.following.append(self.FOLLOW_unaryExpression_in_multiplicativeExpression1074)
                l = self.unaryExpression()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    self._adaptor.addChild(root_0, l.tree)


                if self._state.backtracking == 0:
                    pass

                    exprs = [((l is not None) and [l.result] or [None])[0]]
                    ops = []




                # SolidityInvariant.g:280:9: (op= ( '*' | '/' | '%' ) r= unaryExpression )*
                while True: #loop14
                    alt14 = 2
                    LA14_0 = self.input.LA(1)

                    if (LA14_0 == PERCENT or (SLASH <= LA14_0 <= STAR)) :
                        LA14_2 = self.input.LA(2)

                        if (self.synpred22_SolidityInvariant()) :
                            alt14 = 1




                    if alt14 == 1:
                        # SolidityInvariant.g:281:13: op= ( '*' | '/' | '%' ) r= unaryExpression
                        pass
                        op = self.input.LT(1)

                        if self.input.LA(1) == PERCENT or (SLASH <= self.input.LA(1) <= STAR):
                            self.input.consume()
                            if self._state.backtracking == 0:
                                self._adaptor.addChild(root_0, self._adaptor.createWithPayload(op))

                            self._state.errorRecovery = False


                        else:
                            if self._state.backtracking > 0:
                                raise BacktrackingFailed


                            mse = MismatchedSetException(None, self.input)
                            raise mse



                        self._state.following.append(self.FOLLOW_unaryExpression_in_multiplicativeExpression1124)
                        r = self.unaryExpression()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            self._adaptor.addChild(root_0, r.tree)


                        if self._state.backtracking == 0:
                            pass

                            ops.append(op.text)
                            exprs.append(r.result)





                    else:
                        break #loop14


                if self._state.backtracking == 0:
                    pass

                    if len(ops) == 0:
                        retval.result = exprs[0]
                    else:
                        zipped = [(exprs[i], ops[i], exprs[i+1]) for i in range(len(ops))]
                        retval.result = BinaryExpression()
                        retval.result.aggregate(zipped)






                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                success = True


            except RecognitionException as re:
                self.recover(self.input, re)

        finally:
            if self._state.backtracking > 0:
                self.memoize(self.input, 14, multiplicativeExpression_StartIndex, success)


            pass
        return retval

    # $ANTLR end "multiplicativeExpression"


    class bitwiseOrExpression_return(ParserRuleReturnScope):
        def __init__(self):
            super(SolidityInvariantParser.bitwiseOrExpression_return, self).__init__()

            self.result = None
            self.tree = None





    # $ANTLR start "bitwiseOrExpression"
    # SolidityInvariant.g:298:1: bitwiseOrExpression returns [result] : l= bitwiseXorExpression (op= '|' r= bitwiseXorExpression )* ;
    def bitwiseOrExpression(self, ):
        retval = self.bitwiseOrExpression_return()
        retval.start = self.input.LT(1)

        bitwiseOrExpression_StartIndex = self.input.index()

        root_0 = None

        op = None
        l = None
        r = None

        op_tree = None

        success = False

        try:
            try:
                if self._state.backtracking > 0 and self.alreadyParsedRule(self.input, 15):
                    # for cached failed rules, alreadyParsedRule will raise an exception
                    success = True
                    return retval


                # SolidityInvariant.g:299:5: (l= bitwiseXorExpression (op= '|' r= bitwiseXorExpression )* )
                # SolidityInvariant.g:299:9: l= bitwiseXorExpression (op= '|' r= bitwiseXorExpression )*
                pass
                root_0 = self._adaptor.nil()


                self._state.following.append(self.FOLLOW_bitwiseXorExpression_in_bitwiseOrExpression1185)
                l = self.bitwiseXorExpression()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    self._adaptor.addChild(root_0, l.tree)


                if self._state.backtracking == 0:
                    pass

                    exprs = [((l is not None) and [l.result] or [None])[0]]
                    ops = []




                # SolidityInvariant.g:304:9: (op= '|' r= bitwiseXorExpression )*
                while True: #loop15
                    alt15 = 2
                    LA15_0 = self.input.LA(1)

                    if (LA15_0 == BAR) :
                        LA15_2 = self.input.LA(2)

                        if (self.synpred23_SolidityInvariant()) :
                            alt15 = 1




                    if alt15 == 1:
                        # SolidityInvariant.g:304:10: op= '|' r= bitwiseXorExpression
                        pass
                        op = self.match(self.input, BAR, self.FOLLOW_BAR_in_bitwiseOrExpression1208)
                        if self._state.backtracking == 0:
                            op_tree = self._adaptor.createWithPayload(op)
                            self._adaptor.addChild(root_0, op_tree)



                        self._state.following.append(self.FOLLOW_bitwiseXorExpression_in_bitwiseOrExpression1212)
                        r = self.bitwiseXorExpression()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            self._adaptor.addChild(root_0, r.tree)


                        if self._state.backtracking == 0:
                            pass

                            ops.append(op.text)
                            exprs.append(r.result)





                    else:
                        break #loop15


                if self._state.backtracking == 0:
                    pass

                    if len(ops) == 0:
                        retval.result = exprs[0]
                    else:
                        zipped = [(exprs[i], ops[i], exprs[i+1]) for i in range(len(ops))]
                        retval.result = BinaryExpression()
                        retval.result.aggregate(zipped)






                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                success = True


            except RecognitionException as re:
                self.recover(self.input, re)

        finally:
            if self._state.backtracking > 0:
                self.memoize(self.input, 15, bitwiseOrExpression_StartIndex, success)


            pass
        return retval

    # $ANTLR end "bitwiseOrExpression"


    class bitwiseXorExpression_return(ParserRuleReturnScope):
        def __init__(self):
            super(SolidityInvariantParser.bitwiseXorExpression_return, self).__init__()

            self.result = None
            self.tree = None





    # $ANTLR start "bitwiseXorExpression"
    # SolidityInvariant.g:320:1: bitwiseXorExpression returns [result] : l= bitwiseAndExpression (op= '^' r= bitwiseAndExpression )* ;
    def bitwiseXorExpression(self, ):
        retval = self.bitwiseXorExpression_return()
        retval.start = self.input.LT(1)

        bitwiseXorExpression_StartIndex = self.input.index()

        root_0 = None

        op = None
        l = None
        r = None

        op_tree = None

        success = False

        try:
            try:
                if self._state.backtracking > 0 and self.alreadyParsedRule(self.input, 16):
                    # for cached failed rules, alreadyParsedRule will raise an exception
                    success = True
                    return retval


                # SolidityInvariant.g:321:5: (l= bitwiseAndExpression (op= '^' r= bitwiseAndExpression )* )
                # SolidityInvariant.g:321:9: l= bitwiseAndExpression (op= '^' r= bitwiseAndExpression )*
                pass
                root_0 = self._adaptor.nil()


                self._state.following.append(self.FOLLOW_bitwiseAndExpression_in_bitwiseXorExpression1272)
                l = self.bitwiseAndExpression()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    self._adaptor.addChild(root_0, l.tree)


                if self._state.backtracking == 0:
                    pass

                    exprs = [((l is not None) and [l.result] or [None])[0]]
                    ops = []




                # SolidityInvariant.g:326:9: (op= '^' r= bitwiseAndExpression )*
                while True: #loop16
                    alt16 = 2
                    LA16_0 = self.input.LA(1)

                    if (LA16_0 == CARET) :
                        LA16_2 = self.input.LA(2)

                        if (self.synpred24_SolidityInvariant()) :
                            alt16 = 1




                    if alt16 == 1:
                        # SolidityInvariant.g:326:10: op= '^' r= bitwiseAndExpression
                        pass
                        op = self.match(self.input, CARET, self.FOLLOW_CARET_in_bitwiseXorExpression1295)
                        if self._state.backtracking == 0:
                            op_tree = self._adaptor.createWithPayload(op)
                            self._adaptor.addChild(root_0, op_tree)



                        self._state.following.append(self.FOLLOW_bitwiseAndExpression_in_bitwiseXorExpression1299)
                        r = self.bitwiseAndExpression()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            self._adaptor.addChild(root_0, r.tree)


                        if self._state.backtracking == 0:
                            pass

                            ops.append(op.text)
                            exprs.append(r.result)





                    else:
                        break #loop16


                if self._state.backtracking == 0:
                    pass

                    if len(ops) == 0:
                        retval.result = exprs[0]
                    else:
                        zipped = [(exprs[i], ops[i], exprs[i+1]) for i in range(len(ops))]
                        retval.result = BinaryExpression()
                        retval.result.aggregate(zipped)






                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                success = True


            except RecognitionException as re:
                self.recover(self.input, re)

        finally:
            if self._state.backtracking > 0:
                self.memoize(self.input, 16, bitwiseXorExpression_StartIndex, success)


            pass
        return retval

    # $ANTLR end "bitwiseXorExpression"


    class bitwiseAndExpression_return(ParserRuleReturnScope):
        def __init__(self):
            super(SolidityInvariantParser.bitwiseAndExpression_return, self).__init__()

            self.result = None
            self.tree = None





    # $ANTLR start "bitwiseAndExpression"
    # SolidityInvariant.g:342:1: bitwiseAndExpression returns [result] : l= equalityExpression (op= '&' r= equalityExpression )* ;
    def bitwiseAndExpression(self, ):
        retval = self.bitwiseAndExpression_return()
        retval.start = self.input.LT(1)

        bitwiseAndExpression_StartIndex = self.input.index()

        root_0 = None

        op = None
        l = None
        r = None

        op_tree = None

        success = False

        try:
            try:
                if self._state.backtracking > 0 and self.alreadyParsedRule(self.input, 17):
                    # for cached failed rules, alreadyParsedRule will raise an exception
                    success = True
                    return retval


                # SolidityInvariant.g:343:5: (l= equalityExpression (op= '&' r= equalityExpression )* )
                # SolidityInvariant.g:343:9: l= equalityExpression (op= '&' r= equalityExpression )*
                pass
                root_0 = self._adaptor.nil()


                self._state.following.append(self.FOLLOW_equalityExpression_in_bitwiseAndExpression1359)
                l = self.equalityExpression()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    self._adaptor.addChild(root_0, l.tree)


                if self._state.backtracking == 0:
                    pass

                    exprs = [((l is not None) and [l.result] or [None])[0]]
                    ops = []




                # SolidityInvariant.g:348:9: (op= '&' r= equalityExpression )*
                while True: #loop17
                    alt17 = 2
                    LA17_0 = self.input.LA(1)

                    if (LA17_0 == AMP) :
                        LA17_2 = self.input.LA(2)

                        if (self.synpred25_SolidityInvariant()) :
                            alt17 = 1




                    if alt17 == 1:
                        # SolidityInvariant.g:348:10: op= '&' r= equalityExpression
                        pass
                        op = self.match(self.input, AMP, self.FOLLOW_AMP_in_bitwiseAndExpression1382)
                        if self._state.backtracking == 0:
                            op_tree = self._adaptor.createWithPayload(op)
                            self._adaptor.addChild(root_0, op_tree)



                        self._state.following.append(self.FOLLOW_equalityExpression_in_bitwiseAndExpression1386)
                        r = self.equalityExpression()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            self._adaptor.addChild(root_0, r.tree)


                        if self._state.backtracking == 0:
                            pass

                            ops.append(op.text)
                            exprs.append(r.result)





                    else:
                        break #loop17


                if self._state.backtracking == 0:
                    pass

                    if len(ops) == 0:
                        retval.result = exprs[0]
                    else:
                        zipped = [(exprs[i], ops[i], exprs[i+1]) for i in range(len(ops))]
                        retval.result = BinaryExpression()
                        retval.result.aggregate(zipped)






                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                success = True


            except RecognitionException as re:
                self.recover(self.input, re)

        finally:
            if self._state.backtracking > 0:
                self.memoize(self.input, 17, bitwiseAndExpression_StartIndex, success)


            pass
        return retval

    # $ANTLR end "bitwiseAndExpression"


    class unaryExpression_return(ParserRuleReturnScope):
        def __init__(self):
            super(SolidityInvariantParser.unaryExpression_return, self).__init__()

            self.result = None
            self.tree = None





    # $ANTLR start "unaryExpression"
    # SolidityInvariant.g:364:1: unaryExpression returns [result] : ( '+' u= unaryExpression | '-' u= unaryExpression | '!' u= unaryExpression | '~' u= unaryExpression | unaryPrimary );
    def unaryExpression(self, ):
        retval = self.unaryExpression_return()
        retval.start = self.input.LT(1)

        unaryExpression_StartIndex = self.input.index()

        root_0 = None

        char_literal13 = None
        char_literal14 = None
        char_literal15 = None
        char_literal16 = None
        u = None
        unaryPrimary17 = None

        char_literal13_tree = None
        char_literal14_tree = None
        char_literal15_tree = None
        char_literal16_tree = None

        success = False

        try:
            try:
                if self._state.backtracking > 0 and self.alreadyParsedRule(self.input, 18):
                    # for cached failed rules, alreadyParsedRule will raise an exception
                    success = True
                    return retval


                # SolidityInvariant.g:365:5: ( '+' u= unaryExpression | '-' u= unaryExpression | '!' u= unaryExpression | '~' u= unaryExpression | unaryPrimary )
                alt18 = 5
                LA18 = self.input.LA(1)
                if LA18 == PLUS:
                    alt18 = 1
                elif LA18 == SUB:
                    alt18 = 2
                elif LA18 == BANG:
                    alt18 = 3
                elif LA18 == TILDE:
                    alt18 = 4
                elif LA18 == BOOLLIT or LA18 == IDENTIFIER or LA18 == INTLIT or LA18 == LPAREN or LA18 == STRINGLIT or LA18 == THIS or LA18 == 58 or LA18 == 59 or LA18 == 60 or LA18 == 61 or LA18 == 62 or LA18 == 63 or LA18 == 64 or LA18 == 65 or LA18 == 66:
                    alt18 = 5
                else:
                    if self._state.backtracking > 0:
                        raise BacktrackingFailed


                    nvae = NoViableAltException("", 18, 0, self.input)

                    raise nvae


                if alt18 == 1:
                    # SolidityInvariant.g:365:9: '+' u= unaryExpression
                    pass
                    root_0 = self._adaptor.nil()


                    char_literal13 = self.match(self.input, PLUS, self.FOLLOW_PLUS_in_unaryExpression1444)
                    if self._state.backtracking == 0:
                        char_literal13_tree = self._adaptor.createWithPayload(char_literal13)
                        self._adaptor.addChild(root_0, char_literal13_tree)



                    self._state.following.append(self.FOLLOW_unaryExpression_in_unaryExpression1448)
                    u = self.unaryExpression()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, u.tree)


                    if self._state.backtracking == 0:
                        pass
                        retval.result =  ((u is not None) and [u.result] or [None])[0]




                elif alt18 == 2:
                    # SolidityInvariant.g:367:9: '-' u= unaryExpression
                    pass
                    root_0 = self._adaptor.nil()


                    char_literal14 = self.match(self.input, SUB, self.FOLLOW_SUB_in_unaryExpression1468)
                    if self._state.backtracking == 0:
                        char_literal14_tree = self._adaptor.createWithPayload(char_literal14)
                        self._adaptor.addChild(root_0, char_literal14_tree)



                    self._state.following.append(self.FOLLOW_unaryExpression_in_unaryExpression1472)
                    u = self.unaryExpression()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, u.tree)


                    if self._state.backtracking == 0:
                        pass

                        retval.result = MinusUnaryExpression()
                        retval.result.item = ((u is not None) and [u.result] or [None])[0]





                elif alt18 == 3:
                    # SolidityInvariant.g:372:9: '!' u= unaryExpression
                    pass
                    root_0 = self._adaptor.nil()


                    char_literal15 = self.match(self.input, BANG, self.FOLLOW_BANG_in_unaryExpression1492)
                    if self._state.backtracking == 0:
                        char_literal15_tree = self._adaptor.createWithPayload(char_literal15)
                        self._adaptor.addChild(root_0, char_literal15_tree)



                    self._state.following.append(self.FOLLOW_unaryExpression_in_unaryExpression1496)
                    u = self.unaryExpression()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, u.tree)


                    if self._state.backtracking == 0:
                        pass

                        retval.result = NotExpression()
                        retval.result.item = ((u is not None) and [u.result] or [None])[0]





                elif alt18 == 4:
                    # SolidityInvariant.g:377:9: '~' u= unaryExpression
                    pass
                    root_0 = self._adaptor.nil()


                    char_literal16 = self.match(self.input, TILDE, self.FOLLOW_TILDE_in_unaryExpression1516)
                    if self._state.backtracking == 0:
                        char_literal16_tree = self._adaptor.createWithPayload(char_literal16)
                        self._adaptor.addChild(root_0, char_literal16_tree)



                    self._state.following.append(self.FOLLOW_unaryExpression_in_unaryExpression1520)
                    u = self.unaryExpression()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, u.tree)


                    if self._state.backtracking == 0:
                        pass

                        retval.result = BitwiseNotExpression()
                        retval.result.item = ((u is not None) and [u.result] or [None])[0]





                elif alt18 == 5:
                    # SolidityInvariant.g:382:9: unaryPrimary
                    pass
                    root_0 = self._adaptor.nil()


                    self._state.following.append(self.FOLLOW_unaryPrimary_in_unaryExpression1540)
                    unaryPrimary17 = self.unaryPrimary()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, unaryPrimary17.tree)


                    if self._state.backtracking == 0:
                        pass
                        retval.result =  ((unaryPrimary17 is not None) and [unaryPrimary17.result] or [None])[0]




                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                success = True


            except RecognitionException as re:
                self.recover(self.input, re)

        finally:
            if self._state.backtracking > 0:
                self.memoize(self.input, 18, unaryExpression_StartIndex, success)


            pass
        return retval

    # $ANTLR end "unaryExpression"


    class unaryPrimary_return(ParserRuleReturnScope):
        def __init__(self):
            super(SolidityInvariantParser.unaryPrimary_return, self).__init__()

            self.result = None
            self.tree = None





    # $ANTLR start "unaryPrimary"
    # SolidityInvariant.g:386:1: unaryPrimary returns [result] : ( simpleIdentifier ( indexSuffix )? | solidityGlobal | complexReference | literal | parExpression | jmlPrimary );
    def unaryPrimary(self, ):
        retval = self.unaryPrimary_return()
        retval.start = self.input.LT(1)

        unaryPrimary_StartIndex = self.input.index()

        root_0 = None

        simpleIdentifier18 = None
        indexSuffix19 = None
        solidityGlobal20 = None
        complexReference21 = None
        literal22 = None
        parExpression23 = None
        jmlPrimary24 = None


        success = False

        try:
            try:
                if self._state.backtracking > 0 and self.alreadyParsedRule(self.input, 19):
                    # for cached failed rules, alreadyParsedRule will raise an exception
                    success = True
                    return retval


                # SolidityInvariant.g:387:5: ( simpleIdentifier ( indexSuffix )? | solidityGlobal | complexReference | literal | parExpression | jmlPrimary )
                alt20 = 6
                LA20 = self.input.LA(1)
                if LA20 == IDENTIFIER:
                    LA20_1 = self.input.LA(2)

                    if (LA20_1 == EOF or (AMP <= LA20_1 <= AMPAMP) or (BAR <= LA20_1 <= BARBAR) or (CARET <= LA20_1 <= COMMA) or LA20_1 == EQEQ or (GE <= LA20_1 <= GT) or (LBRACKET <= LA20_1 <= LE) or (LSHIFT <= LA20_1 <= NOTEQ) or (PERCENT <= LA20_1 <= QUES) or (RBRACKET <= LA20_1 <= STAR) or LA20_1 == SUB or (54 <= LA20_1 <= 57)) :
                        alt20 = 1
                    elif (LA20_1 == DOT) :
                        alt20 = 3
                    else:
                        if self._state.backtracking > 0:
                            raise BacktrackingFailed


                        nvae = NoViableAltException("", 20, 1, self.input)

                        raise nvae


                elif LA20 == THIS or LA20 == 63 or LA20 == 64 or LA20 == 65 or LA20 == 66:
                    alt20 = 2
                elif LA20 == BOOLLIT or LA20 == INTLIT or LA20 == STRINGLIT:
                    alt20 = 4
                elif LA20 == LPAREN:
                    alt20 = 5
                elif LA20 == 58 or LA20 == 59 or LA20 == 60 or LA20 == 61 or LA20 == 62:
                    alt20 = 6
                else:
                    if self._state.backtracking > 0:
                        raise BacktrackingFailed


                    nvae = NoViableAltException("", 20, 0, self.input)

                    raise nvae


                if alt20 == 1:
                    # SolidityInvariant.g:387:9: simpleIdentifier ( indexSuffix )?
                    pass
                    root_0 = self._adaptor.nil()


                    self._state.following.append(self.FOLLOW_simpleIdentifier_in_unaryPrimary1573)
                    simpleIdentifier18 = self.simpleIdentifier()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, simpleIdentifier18.tree)


                    # SolidityInvariant.g:387:26: ( indexSuffix )?
                    alt19 = 2
                    LA19_0 = self.input.LA(1)

                    if (LA19_0 == LBRACKET) :
                        alt19 = 1
                    if alt19 == 1:
                        # SolidityInvariant.g:387:26: indexSuffix
                        pass
                        self._state.following.append(self.FOLLOW_indexSuffix_in_unaryPrimary1575)
                        indexSuffix19 = self.indexSuffix()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            self._adaptor.addChild(root_0, indexSuffix19.tree)





                    if self._state.backtracking == 0:
                        pass

                        if ((indexSuffix19 is not None) and [indexSuffix19.result] or [None])[0] is None:
                            retval.result =  ((simpleIdentifier18 is not None) and [simpleIdentifier18.result] or [None])[0]
                        else:
                            ref = ArrayReference()
                            ref.target = ((simpleIdentifier18 is not None) and [simpleIdentifier18.result] or [None])[0]
                            ref.args = [((indexSuffix19 is not None) and [indexSuffix19.result] or [None])[0]]
                            retval.result = ref





                elif alt20 == 2:
                    # SolidityInvariant.g:397:9: solidityGlobal
                    pass
                    root_0 = self._adaptor.nil()


                    self._state.following.append(self.FOLLOW_solidityGlobal_in_unaryPrimary1596)
                    solidityGlobal20 = self.solidityGlobal()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, solidityGlobal20.tree)


                    if self._state.backtracking == 0:
                        pass
                        retval.result =  ((solidityGlobal20 is not None) and [solidityGlobal20.result] or [None])[0]




                elif alt20 == 3:
                    # SolidityInvariant.g:399:9: complexReference
                    pass
                    root_0 = self._adaptor.nil()


                    self._state.following.append(self.FOLLOW_complexReference_in_unaryPrimary1616)
                    complexReference21 = self.complexReference()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, complexReference21.tree)


                    if self._state.backtracking == 0:
                        pass
                        retval.result =  ((complexReference21 is not None) and [complexReference21.result] or [None])[0]




                elif alt20 == 4:
                    # SolidityInvariant.g:401:9: literal
                    pass
                    root_0 = self._adaptor.nil()


                    self._state.following.append(self.FOLLOW_literal_in_unaryPrimary1636)
                    literal22 = self.literal()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, literal22.tree)


                    if self._state.backtracking == 0:
                        pass
                        retval.result =  ((literal22 is not None) and [literal22.result] or [None])[0]




                elif alt20 == 5:
                    # SolidityInvariant.g:403:9: parExpression
                    pass
                    root_0 = self._adaptor.nil()


                    self._state.following.append(self.FOLLOW_parExpression_in_unaryPrimary1656)
                    parExpression23 = self.parExpression()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, parExpression23.tree)


                    if self._state.backtracking == 0:
                        pass
                        retval.result =  ((parExpression23 is not None) and [parExpression23.result] or [None])[0]




                elif alt20 == 6:
                    # SolidityInvariant.g:405:9: jmlPrimary
                    pass
                    root_0 = self._adaptor.nil()


                    self._state.following.append(self.FOLLOW_jmlPrimary_in_unaryPrimary1676)
                    jmlPrimary24 = self.jmlPrimary()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, jmlPrimary24.tree)


                    if self._state.backtracking == 0:
                        pass
                        retval.result =  ((jmlPrimary24 is not None) and [jmlPrimary24.result] or [None])[0]




                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                success = True


            except RecognitionException as re:
                self.recover(self.input, re)

        finally:
            if self._state.backtracking > 0:
                self.memoize(self.input, 19, unaryPrimary_StartIndex, success)


            pass
        return retval

    # $ANTLR end "unaryPrimary"


    class solidityGlobal_return(ParserRuleReturnScope):
        def __init__(self):
            super(SolidityInvariantParser.solidityGlobal_return, self).__init__()

            self.result = None
            self.tree = None





    # $ANTLR start "solidityGlobal"
    # SolidityInvariant.g:409:1: solidityGlobal returns [result] : base= ( 'msg' | 'block' | 'tx' | 'address' | 'this' ) ( '.' attr= IDENTIFIER )+ ;
    def solidityGlobal(self, ):
        retval = self.solidityGlobal_return()
        retval.start = self.input.LT(1)

        solidityGlobal_StartIndex = self.input.index()

        root_0 = None

        base = None
        attr = None
        char_literal25 = None

        base_tree = None
        attr_tree = None
        char_literal25_tree = None

        success = False

        try:
            try:
                if self._state.backtracking > 0 and self.alreadyParsedRule(self.input, 20):
                    # for cached failed rules, alreadyParsedRule will raise an exception
                    success = True
                    return retval


                # SolidityInvariant.g:410:5: (base= ( 'msg' | 'block' | 'tx' | 'address' | 'this' ) ( '.' attr= IDENTIFIER )+ )
                # SolidityInvariant.g:410:9: base= ( 'msg' | 'block' | 'tx' | 'address' | 'this' ) ( '.' attr= IDENTIFIER )+
                pass
                root_0 = self._adaptor.nil()


                base = self.input.LT(1)

                if self.input.LA(1) == THIS or (63 <= self.input.LA(1) <= 66):
                    self.input.consume()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, self._adaptor.createWithPayload(base))

                    self._state.errorRecovery = False


                else:
                    if self._state.backtracking > 0:
                        raise BacktrackingFailed


                    mse = MismatchedSetException(None, self.input)
                    raise mse



                # SolidityInvariant.g:411:9: ( '.' attr= IDENTIFIER )+
                cnt21 = 0
                while True: #loop21
                    alt21 = 2
                    LA21_0 = self.input.LA(1)

                    if (LA21_0 == DOT) :
                        alt21 = 1


                    if alt21 == 1:
                        # SolidityInvariant.g:411:10: '.' attr= IDENTIFIER
                        pass
                        char_literal25 = self.match(self.input, DOT, self.FOLLOW_DOT_in_solidityGlobal1740)
                        if self._state.backtracking == 0:
                            char_literal25_tree = self._adaptor.createWithPayload(char_literal25)
                            self._adaptor.addChild(root_0, char_literal25_tree)



                        attr = self.match(self.input, IDENTIFIER, self.FOLLOW_IDENTIFIER_in_solidityGlobal1744)
                        if self._state.backtracking == 0:
                            attr_tree = self._adaptor.createWithPayload(attr)
                            self._adaptor.addChild(root_0, attr_tree)




                    else:
                        if cnt21 >= 1:
                            break #loop21

                        if self._state.backtracking > 0:
                            raise BacktrackingFailed


                        eee = EarlyExitException(21, self.input)
                        raise eee

                    cnt21 += 1


                if self._state.backtracking == 0:
                    pass

                    root = Identifier()
                    root.val = base.text

                    current = AttributeCall()
                    current.target = root
                    current.call = []

                    for token in attr:
                        new_attr = Identifier()
                        new_attr.val = token.text
                        current = AttributeCall()
                        current.target = current
                        current.call = [new_attr]

                    retval.result = current






                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                success = True


            except RecognitionException as re:
                self.recover(self.input, re)

        finally:
            if self._state.backtracking > 0:
                self.memoize(self.input, 20, solidityGlobal_StartIndex, success)


            pass
        return retval

    # $ANTLR end "solidityGlobal"


    class simpleIdentifier_return(ParserRuleReturnScope):
        def __init__(self):
            super(SolidityInvariantParser.simpleIdentifier_return, self).__init__()

            self.result = None
            self.tree = None





    # $ANTLR start "simpleIdentifier"
    # SolidityInvariant.g:432:1: simpleIdentifier returns [result] : IDENTIFIER ;
    def simpleIdentifier(self, ):
        retval = self.simpleIdentifier_return()
        retval.start = self.input.LT(1)

        simpleIdentifier_StartIndex = self.input.index()

        root_0 = None

        IDENTIFIER26 = None

        IDENTIFIER26_tree = None

        success = False

        try:
            try:
                if self._state.backtracking > 0 and self.alreadyParsedRule(self.input, 21):
                    # for cached failed rules, alreadyParsedRule will raise an exception
                    success = True
                    return retval


                # SolidityInvariant.g:433:5: ( IDENTIFIER )
                # SolidityInvariant.g:433:9: IDENTIFIER
                pass
                root_0 = self._adaptor.nil()


                IDENTIFIER26 = self.match(self.input, IDENTIFIER, self.FOLLOW_IDENTIFIER_in_simpleIdentifier1780)
                if self._state.backtracking == 0:
                    IDENTIFIER26_tree = self._adaptor.createWithPayload(IDENTIFIER26)
                    self._adaptor.addChild(root_0, IDENTIFIER26_tree)



                if self._state.backtracking == 0:
                    pass

                    retval.result = Identifier()
                    retval.result.val = IDENTIFIER26.text






                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                success = True


            except RecognitionException as re:
                self.recover(self.input, re)

        finally:
            if self._state.backtracking > 0:
                self.memoize(self.input, 21, simpleIdentifier_StartIndex, success)


            pass
        return retval

    # $ANTLR end "simpleIdentifier"


    class complexReference_return(ParserRuleReturnScope):
        def __init__(self):
            super(SolidityInvariantParser.complexReference_return, self).__init__()

            self.result = None
            self.tree = None





    # $ANTLR start "complexReference"
    # SolidityInvariant.g:440:1: complexReference returns [result] : t= IDENTIFIER ( '.' id= IDENTIFIER )+ (sfx= identifierSuffix )? ;
    def complexReference(self, ):
        retval = self.complexReference_return()
        retval.start = self.input.LT(1)

        complexReference_StartIndex = self.input.index()

        root_0 = None

        t = None
        id = None
        char_literal27 = None
        sfx = None

        t_tree = None
        id_tree = None
        char_literal27_tree = None

        success = False

        try:
            try:
                if self._state.backtracking > 0 and self.alreadyParsedRule(self.input, 22):
                    # for cached failed rules, alreadyParsedRule will raise an exception
                    success = True
                    return retval


                # SolidityInvariant.g:441:5: (t= IDENTIFIER ( '.' id= IDENTIFIER )+ (sfx= identifierSuffix )? )
                # SolidityInvariant.g:441:9: t= IDENTIFIER ( '.' id= IDENTIFIER )+ (sfx= identifierSuffix )?
                pass
                root_0 = self._adaptor.nil()


                t = self.match(self.input, IDENTIFIER, self.FOLLOW_IDENTIFIER_in_complexReference1815)
                if self._state.backtracking == 0:
                    t_tree = self._adaptor.createWithPayload(t)
                    self._adaptor.addChild(root_0, t_tree)



                if self._state.backtracking == 0:
                    pass

                    l_t = Identifier()
                    l_t.val = t.text
                    l_ids = []
                    l_suf = None




                # SolidityInvariant.g:448:9: ( '.' id= IDENTIFIER )+
                cnt22 = 0
                while True: #loop22
                    alt22 = 2
                    LA22_0 = self.input.LA(1)

                    if (LA22_0 == DOT) :
                        alt22 = 1


                    if alt22 == 1:
                        # SolidityInvariant.g:448:10: '.' id= IDENTIFIER
                        pass
                        char_literal27 = self.match(self.input, DOT, self.FOLLOW_DOT_in_complexReference1836)
                        if self._state.backtracking == 0:
                            char_literal27_tree = self._adaptor.createWithPayload(char_literal27)
                            self._adaptor.addChild(root_0, char_literal27_tree)



                        id = self.match(self.input, IDENTIFIER, self.FOLLOW_IDENTIFIER_in_complexReference1840)
                        if self._state.backtracking == 0:
                            id_tree = self._adaptor.createWithPayload(id)
                            self._adaptor.addChild(root_0, id_tree)



                        if self._state.backtracking == 0:
                            pass

                            l_id = Identifier()
                            l_id.val = id.text
                            l_ids.append(l_id)





                    else:
                        if cnt22 >= 1:
                            break #loop22

                        if self._state.backtracking > 0:
                            raise BacktrackingFailed


                        eee = EarlyExitException(22, self.input)
                        raise eee

                    cnt22 += 1


                # SolidityInvariant.g:455:9: (sfx= identifierSuffix )?
                alt23 = 2
                LA23_0 = self.input.LA(1)

                if (LA23_0 == LBRACKET or LA23_0 == LPAREN) :
                    alt23 = 1
                if alt23 == 1:
                    # SolidityInvariant.g:455:10: sfx= identifierSuffix
                    pass
                    self._state.following.append(self.FOLLOW_identifierSuffix_in_complexReference1878)
                    sfx = self.identifierSuffix()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, sfx.tree)





                if self._state.backtracking == 0:
                    pass

                    if sfx is not None:
                        l_suf = ((sfx is not None) and [sfx.args] or [None])[0]
                    retval.result = primaryCombine(l_t, l_ids, l_suf)






                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                success = True


            except RecognitionException as re:
                self.recover(self.input, re)

        finally:
            if self._state.backtracking > 0:
                self.memoize(self.input, 22, complexReference_StartIndex, success)


            pass
        return retval

    # $ANTLR end "complexReference"


    class literal_return(ParserRuleReturnScope):
        def __init__(self):
            super(SolidityInvariantParser.literal_return, self).__init__()

            self.result = None
            self.tree = None





    # $ANTLR start "literal"
    # SolidityInvariant.g:463:1: literal returns [result] : ( INTLIT | BOOLLIT | STRINGLIT );
    def literal(self, ):
        retval = self.literal_return()
        retval.start = self.input.LT(1)

        literal_StartIndex = self.input.index()

        root_0 = None

        INTLIT28 = None
        BOOLLIT29 = None
        STRINGLIT30 = None

        INTLIT28_tree = None
        BOOLLIT29_tree = None
        STRINGLIT30_tree = None

        success = False

        try:
            try:
                if self._state.backtracking > 0 and self.alreadyParsedRule(self.input, 23):
                    # for cached failed rules, alreadyParsedRule will raise an exception
                    success = True
                    return retval


                # SolidityInvariant.g:464:5: ( INTLIT | BOOLLIT | STRINGLIT )
                alt24 = 3
                LA24 = self.input.LA(1)
                if LA24 == INTLIT:
                    alt24 = 1
                elif LA24 == BOOLLIT:
                    alt24 = 2
                elif LA24 == STRINGLIT:
                    alt24 = 3
                else:
                    if self._state.backtracking > 0:
                        raise BacktrackingFailed


                    nvae = NoViableAltException("", 24, 0, self.input)

                    raise nvae


                if alt24 == 1:
                    # SolidityInvariant.g:464:9: INTLIT
                    pass
                    root_0 = self._adaptor.nil()


                    INTLIT28 = self.match(self.input, INTLIT, self.FOLLOW_INTLIT_in_literal1917)
                    if self._state.backtracking == 0:
                        INTLIT28_tree = self._adaptor.createWithPayload(INTLIT28)
                        self._adaptor.addChild(root_0, INTLIT28_tree)



                    if self._state.backtracking == 0:
                        pass

                        retval.result = IntLiteral()
                        retval.result.val = int(INTLIT28.text)





                elif alt24 == 2:
                    # SolidityInvariant.g:469:9: BOOLLIT
                    pass
                    root_0 = self._adaptor.nil()


                    BOOLLIT29 = self.match(self.input, BOOLLIT, self.FOLLOW_BOOLLIT_in_literal1937)
                    if self._state.backtracking == 0:
                        BOOLLIT29_tree = self._adaptor.createWithPayload(BOOLLIT29)
                        self._adaptor.addChild(root_0, BOOLLIT29_tree)



                    if self._state.backtracking == 0:
                        pass

                        retval.result = BoolLiteral()
                        retval.result.val = True if BOOLLIT29.text == 'true' else False





                elif alt24 == 3:
                    # SolidityInvariant.g:474:9: STRINGLIT
                    pass
                    root_0 = self._adaptor.nil()


                    STRINGLIT30 = self.match(self.input, STRINGLIT, self.FOLLOW_STRINGLIT_in_literal1957)
                    if self._state.backtracking == 0:
                        STRINGLIT30_tree = self._adaptor.createWithPayload(STRINGLIT30)
                        self._adaptor.addChild(root_0, STRINGLIT30_tree)



                    if self._state.backtracking == 0:
                        pass

                        retval.result = StringLiteral()
                        retval.result.val = STRINGLIT30.text.strip('"')





                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                success = True


            except RecognitionException as re:
                self.recover(self.input, re)

        finally:
            if self._state.backtracking > 0:
                self.memoize(self.input, 23, literal_StartIndex, success)


            pass
        return retval

    # $ANTLR end "literal"


    class parExpression_return(ParserRuleReturnScope):
        def __init__(self):
            super(SolidityInvariantParser.parExpression_return, self).__init__()

            self.result = None
            self.tree = None





    # $ANTLR start "parExpression"
    # SolidityInvariant.g:481:1: parExpression returns [result] : '(' expression ')' ;
    def parExpression(self, ):
        retval = self.parExpression_return()
        retval.start = self.input.LT(1)

        parExpression_StartIndex = self.input.index()

        root_0 = None

        char_literal31 = None
        char_literal33 = None
        expression32 = None

        char_literal31_tree = None
        char_literal33_tree = None

        success = False

        try:
            try:
                if self._state.backtracking > 0 and self.alreadyParsedRule(self.input, 24):
                    # for cached failed rules, alreadyParsedRule will raise an exception
                    success = True
                    return retval


                # SolidityInvariant.g:482:5: ( '(' expression ')' )
                # SolidityInvariant.g:482:9: '(' expression ')'
                pass
                root_0 = self._adaptor.nil()


                char_literal31 = self.match(self.input, LPAREN, self.FOLLOW_LPAREN_in_parExpression1990)
                if self._state.backtracking == 0:
                    char_literal31_tree = self._adaptor.createWithPayload(char_literal31)
                    self._adaptor.addChild(root_0, char_literal31_tree)



                self._state.following.append(self.FOLLOW_expression_in_parExpression1992)
                expression32 = self.expression()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    self._adaptor.addChild(root_0, expression32.tree)


                char_literal33 = self.match(self.input, RPAREN, self.FOLLOW_RPAREN_in_parExpression1994)
                if self._state.backtracking == 0:
                    char_literal33_tree = self._adaptor.createWithPayload(char_literal33)
                    self._adaptor.addChild(root_0, char_literal33_tree)



                if self._state.backtracking == 0:
                    pass
                    retval.result =  ((expression32 is not None) and [expression32.result] or [None])[0]





                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                success = True


            except RecognitionException as re:
                self.recover(self.input, re)

        finally:
            if self._state.backtracking > 0:
                self.memoize(self.input, 24, parExpression_StartIndex, success)


            pass
        return retval

    # $ANTLR end "parExpression"


    class indexSuffix_return(ParserRuleReturnScope):
        def __init__(self):
            super(SolidityInvariantParser.indexSuffix_return, self).__init__()

            self.result = None
            self.tree = None





    # $ANTLR start "indexSuffix"
    # SolidityInvariant.g:486:1: indexSuffix returns [result] : '[' expression ']' ;
    def indexSuffix(self, ):
        retval = self.indexSuffix_return()
        retval.start = self.input.LT(1)

        indexSuffix_StartIndex = self.input.index()

        root_0 = None

        char_literal34 = None
        char_literal36 = None
        expression35 = None

        char_literal34_tree = None
        char_literal36_tree = None

        success = False

        try:
            try:
                if self._state.backtracking > 0 and self.alreadyParsedRule(self.input, 25):
                    # for cached failed rules, alreadyParsedRule will raise an exception
                    success = True
                    return retval


                # SolidityInvariant.g:487:5: ( '[' expression ']' )
                # SolidityInvariant.g:487:9: '[' expression ']'
                pass
                root_0 = self._adaptor.nil()


                char_literal34 = self.match(self.input, LBRACKET, self.FOLLOW_LBRACKET_in_indexSuffix2027)
                if self._state.backtracking == 0:
                    char_literal34_tree = self._adaptor.createWithPayload(char_literal34)
                    self._adaptor.addChild(root_0, char_literal34_tree)



                self._state.following.append(self.FOLLOW_expression_in_indexSuffix2029)
                expression35 = self.expression()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    self._adaptor.addChild(root_0, expression35.tree)


                char_literal36 = self.match(self.input, RBRACKET, self.FOLLOW_RBRACKET_in_indexSuffix2031)
                if self._state.backtracking == 0:
                    char_literal36_tree = self._adaptor.createWithPayload(char_literal36)
                    self._adaptor.addChild(root_0, char_literal36_tree)



                if self._state.backtracking == 0:
                    pass
                    retval.result =  ((expression35 is not None) and [expression35.result] or [None])[0]





                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                success = True


            except RecognitionException as re:
                self.recover(self.input, re)

        finally:
            if self._state.backtracking > 0:
                self.memoize(self.input, 25, indexSuffix_StartIndex, success)


            pass
        return retval

    # $ANTLR end "indexSuffix"


    class identifierSuffix_return(ParserRuleReturnScope):
        def __init__(self):
            super(SolidityInvariantParser.identifierSuffix_return, self).__init__()

            self.args = None
            self.tree = None





    # $ANTLR start "identifierSuffix"
    # SolidityInvariant.g:492:1: identifierSuffix returns [args] : ( '(' (a= argList )? ')' | '[' expression ']' );
    def identifierSuffix(self, ):
        retval = self.identifierSuffix_return()
        retval.start = self.input.LT(1)

        identifierSuffix_StartIndex = self.input.index()

        root_0 = None

        char_literal37 = None
        char_literal38 = None
        char_literal39 = None
        char_literal41 = None
        a = None
        expression40 = None

        char_literal37_tree = None
        char_literal38_tree = None
        char_literal39_tree = None
        char_literal41_tree = None

        success = False

        try:
            try:
                if self._state.backtracking > 0 and self.alreadyParsedRule(self.input, 26):
                    # for cached failed rules, alreadyParsedRule will raise an exception
                    success = True
                    return retval


                # SolidityInvariant.g:493:5: ( '(' (a= argList )? ')' | '[' expression ']' )
                alt26 = 2
                LA26_0 = self.input.LA(1)

                if (LA26_0 == LPAREN) :
                    alt26 = 1
                elif (LA26_0 == LBRACKET) :
                    alt26 = 2
                else:
                    if self._state.backtracking > 0:
                        raise BacktrackingFailed


                    nvae = NoViableAltException("", 26, 0, self.input)

                    raise nvae


                if alt26 == 1:
                    # SolidityInvariant.g:493:9: '(' (a= argList )? ')'
                    pass
                    root_0 = self._adaptor.nil()


                    char_literal37 = self.match(self.input, LPAREN, self.FOLLOW_LPAREN_in_identifierSuffix2065)
                    if self._state.backtracking == 0:
                        char_literal37_tree = self._adaptor.createWithPayload(char_literal37)
                        self._adaptor.addChild(root_0, char_literal37_tree)



                    # SolidityInvariant.g:493:14: (a= argList )?
                    alt25 = 2
                    LA25_0 = self.input.LA(1)

                    if (LA25_0 == BANG or LA25_0 == BOOLLIT or LA25_0 == IDENTIFIER or LA25_0 == INTLIT or LA25_0 == LPAREN or LA25_0 == PLUS or (STRINGLIT <= LA25_0 <= SUB) or (THIS <= LA25_0 <= TILDE) or (58 <= LA25_0 <= 66)) :
                        alt25 = 1
                    if alt25 == 1:
                        # SolidityInvariant.g:493:14: a= argList
                        pass
                        self._state.following.append(self.FOLLOW_argList_in_identifierSuffix2069)
                        a = self.argList()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            self._adaptor.addChild(root_0, a.tree)





                    char_literal38 = self.match(self.input, RPAREN, self.FOLLOW_RPAREN_in_identifierSuffix2072)
                    if self._state.backtracking == 0:
                        char_literal38_tree = self._adaptor.createWithPayload(char_literal38)
                        self._adaptor.addChild(root_0, char_literal38_tree)



                    if self._state.backtracking == 0:
                        pass

                        if a is not None:
                            retval.args = ('(', a)
                        else:
                            retval.args = ('(', [])





                elif alt26 == 2:
                    # SolidityInvariant.g:500:9: '[' expression ']'
                    pass
                    root_0 = self._adaptor.nil()


                    char_literal39 = self.match(self.input, LBRACKET, self.FOLLOW_LBRACKET_in_identifierSuffix2092)
                    if self._state.backtracking == 0:
                        char_literal39_tree = self._adaptor.createWithPayload(char_literal39)
                        self._adaptor.addChild(root_0, char_literal39_tree)



                    self._state.following.append(self.FOLLOW_expression_in_identifierSuffix2094)
                    expression40 = self.expression()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, expression40.tree)


                    char_literal41 = self.match(self.input, RBRACKET, self.FOLLOW_RBRACKET_in_identifierSuffix2096)
                    if self._state.backtracking == 0:
                        char_literal41_tree = self._adaptor.createWithPayload(char_literal41)
                        self._adaptor.addChild(root_0, char_literal41_tree)



                    if self._state.backtracking == 0:
                        pass

                        retval.args = ('[', ((expression40 is not None) and [expression40.result] or [None])[0])





                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                success = True


            except RecognitionException as re:
                self.recover(self.input, re)

        finally:
            if self._state.backtracking > 0:
                self.memoize(self.input, 26, identifierSuffix_StartIndex, success)


            pass
        return retval

    # $ANTLR end "identifierSuffix"


    class argList_return(ParserRuleReturnScope):
        def __init__(self):
            super(SolidityInvariantParser.argList_return, self).__init__()

            self.args = None
            self.tree = None





    # $ANTLR start "argList"
    # SolidityInvariant.g:506:1: argList returns [args] : first= expression (restList= argListRest )* ;
    def argList(self, ):
        retval = self.argList_return()
        retval.start = self.input.LT(1)

        argList_StartIndex = self.input.index()

        root_0 = None

        first = None
        restList = None


        success = False

        try:
            try:
                if self._state.backtracking > 0 and self.alreadyParsedRule(self.input, 27):
                    # for cached failed rules, alreadyParsedRule will raise an exception
                    success = True
                    return retval


                # SolidityInvariant.g:507:5: (first= expression (restList= argListRest )* )
                # SolidityInvariant.g:507:9: first= expression (restList= argListRest )*
                pass
                root_0 = self._adaptor.nil()


                self._state.following.append(self.FOLLOW_expression_in_argList2131)
                first = self.expression()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    self._adaptor.addChild(root_0, first.tree)


                # SolidityInvariant.g:507:34: (restList= argListRest )*
                while True: #loop27
                    alt27 = 2
                    LA27_0 = self.input.LA(1)

                    if (LA27_0 == COMMA) :
                        alt27 = 1


                    if alt27 == 1:
                        # SolidityInvariant.g:507:34: restList= argListRest
                        pass
                        self._state.following.append(self.FOLLOW_argListRest_in_argList2135)
                        restList = self.argListRest()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            self._adaptor.addChild(root_0, restList.tree)



                    else:
                        break #loop27


                if self._state.backtracking == 0:
                    pass

                    retval.args = [((first is not None) and [first.result] or [None])[0]]
                    for r in restList:
                        retval.args.append(r)






                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                success = True


            except RecognitionException as re:
                self.recover(self.input, re)

        finally:
            if self._state.backtracking > 0:
                self.memoize(self.input, 27, argList_StartIndex, success)


            pass
        return retval

    # $ANTLR end "argList"


    class argListRest_return(ParserRuleReturnScope):
        def __init__(self):
            super(SolidityInvariantParser.argListRest_return, self).__init__()

            self.value = None
            self.tree = None





    # $ANTLR start "argListRest"
    # SolidityInvariant.g:515:1: argListRest returns [value] : ',' expr= expression ;
    def argListRest(self, ):
        retval = self.argListRest_return()
        retval.start = self.input.LT(1)

        argListRest_StartIndex = self.input.index()

        root_0 = None

        char_literal42 = None
        expr = None

        char_literal42_tree = None

        success = False

        try:
            try:
                if self._state.backtracking > 0 and self.alreadyParsedRule(self.input, 28):
                    # for cached failed rules, alreadyParsedRule will raise an exception
                    success = True
                    return retval


                # SolidityInvariant.g:516:5: ( ',' expr= expression )
                # SolidityInvariant.g:516:9: ',' expr= expression
                pass
                root_0 = self._adaptor.nil()


                char_literal42 = self.match(self.input, COMMA, self.FOLLOW_COMMA_in_argListRest2169)
                if self._state.backtracking == 0:
                    char_literal42_tree = self._adaptor.createWithPayload(char_literal42)
                    self._adaptor.addChild(root_0, char_literal42_tree)



                self._state.following.append(self.FOLLOW_expression_in_argListRest2173)
                expr = self.expression()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    self._adaptor.addChild(root_0, expr.tree)


                if self._state.backtracking == 0:
                    pass

                    retval.value = ((expr is not None) and [expr.result] or [None])[0]






                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                success = True


            except RecognitionException as re:
                self.recover(self.input, re)

        finally:
            if self._state.backtracking > 0:
                self.memoize(self.input, 28, argListRest_StartIndex, success)


            pass
        return retval

    # $ANTLR end "argListRest"


    class jmlPrimary_return(ParserRuleReturnScope):
        def __init__(self):
            super(SolidityInvariantParser.jmlPrimary_return, self).__init__()

            self.result = None
            self.tree = None





    # $ANTLR start "jmlPrimary"
    # SolidityInvariant.g:522:1: jmlPrimary returns [result] : ( resultExpression | oldExpression | specQuantifiedExpression );
    def jmlPrimary(self, ):
        retval = self.jmlPrimary_return()
        retval.start = self.input.LT(1)

        jmlPrimary_StartIndex = self.input.index()

        root_0 = None

        resultExpression43 = None
        oldExpression44 = None
        specQuantifiedExpression45 = None


        success = False

        try:
            try:
                if self._state.backtracking > 0 and self.alreadyParsedRule(self.input, 29):
                    # for cached failed rules, alreadyParsedRule will raise an exception
                    success = True
                    return retval


                # SolidityInvariant.g:523:5: ( resultExpression | oldExpression | specQuantifiedExpression )
                alt28 = 3
                LA28 = self.input.LA(1)
                if LA28 == 62:
                    alt28 = 1
                elif LA28 == 60 or LA28 == 61:
                    alt28 = 2
                elif LA28 == 58 or LA28 == 59:
                    alt28 = 3
                else:
                    if self._state.backtracking > 0:
                        raise BacktrackingFailed


                    nvae = NoViableAltException("", 28, 0, self.input)

                    raise nvae


                if alt28 == 1:
                    # SolidityInvariant.g:523:9: resultExpression
                    pass
                    root_0 = self._adaptor.nil()


                    self._state.following.append(self.FOLLOW_resultExpression_in_jmlPrimary2206)
                    resultExpression43 = self.resultExpression()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, resultExpression43.tree)


                    if self._state.backtracking == 0:
                        pass
                        retval.result =  ((resultExpression43 is not None) and [resultExpression43.result] or [None])[0]




                elif alt28 == 2:
                    # SolidityInvariant.g:525:9: oldExpression
                    pass
                    root_0 = self._adaptor.nil()


                    self._state.following.append(self.FOLLOW_oldExpression_in_jmlPrimary2226)
                    oldExpression44 = self.oldExpression()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, oldExpression44.tree)


                    if self._state.backtracking == 0:
                        pass
                        retval.result =  ((oldExpression44 is not None) and [oldExpression44.result] or [None])[0]




                elif alt28 == 3:
                    # SolidityInvariant.g:527:9: specQuantifiedExpression
                    pass
                    root_0 = self._adaptor.nil()


                    self._state.following.append(self.FOLLOW_specQuantifiedExpression_in_jmlPrimary2246)
                    specQuantifiedExpression45 = self.specQuantifiedExpression()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, specQuantifiedExpression45.tree)


                    if self._state.backtracking == 0:
                        pass
                        retval.result =  ((specQuantifiedExpression45 is not None) and [specQuantifiedExpression45.result] or [None])[0]




                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                success = True


            except RecognitionException as re:
                self.recover(self.input, re)

        finally:
            if self._state.backtracking > 0:
                self.memoize(self.input, 29, jmlPrimary_StartIndex, success)


            pass
        return retval

    # $ANTLR end "jmlPrimary"


    class resultExpression_return(ParserRuleReturnScope):
        def __init__(self):
            super(SolidityInvariantParser.resultExpression_return, self).__init__()

            self.result = None
            self.tree = None





    # $ANTLR start "resultExpression"
    # SolidityInvariant.g:531:1: resultExpression returns [result] : '\\\\result' ;
    def resultExpression(self, ):
        retval = self.resultExpression_return()
        retval.start = self.input.LT(1)

        resultExpression_StartIndex = self.input.index()

        root_0 = None

        string_literal46 = None

        string_literal46_tree = None

        success = False

        try:
            try:
                if self._state.backtracking > 0 and self.alreadyParsedRule(self.input, 30):
                    # for cached failed rules, alreadyParsedRule will raise an exception
                    success = True
                    return retval


                # SolidityInvariant.g:532:5: ( '\\\\result' )
                # SolidityInvariant.g:532:9: '\\\\result'
                pass
                root_0 = self._adaptor.nil()


                string_literal46 = self.match(self.input, 62, self.FOLLOW_62_in_resultExpression2279)
                if self._state.backtracking == 0:
                    string_literal46_tree = self._adaptor.createWithPayload(string_literal46)
                    self._adaptor.addChild(root_0, string_literal46_tree)



                if self._state.backtracking == 0:
                    pass

                    retval.result = ResultExpression()






                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                success = True


            except RecognitionException as re:
                self.recover(self.input, re)

        finally:
            if self._state.backtracking > 0:
                self.memoize(self.input, 30, resultExpression_StartIndex, success)


            pass
        return retval

    # $ANTLR end "resultExpression"


    class oldExpression_return(ParserRuleReturnScope):
        def __init__(self):
            super(SolidityInvariantParser.oldExpression_return, self).__init__()

            self.result = None
            self.tree = None





    # $ANTLR start "oldExpression"
    # SolidityInvariant.g:538:1: oldExpression returns [result] : oldId '(' expression ')' ;
    def oldExpression(self, ):
        retval = self.oldExpression_return()
        retval.start = self.input.LT(1)

        oldExpression_StartIndex = self.input.index()

        root_0 = None

        char_literal48 = None
        char_literal50 = None
        oldId47 = None
        expression49 = None

        char_literal48_tree = None
        char_literal50_tree = None

        success = False

        try:
            try:
                if self._state.backtracking > 0 and self.alreadyParsedRule(self.input, 31):
                    # for cached failed rules, alreadyParsedRule will raise an exception
                    success = True
                    return retval


                # SolidityInvariant.g:539:5: ( oldId '(' expression ')' )
                # SolidityInvariant.g:539:9: oldId '(' expression ')'
                pass
                root_0 = self._adaptor.nil()


                self._state.following.append(self.FOLLOW_oldId_in_oldExpression2312)
                oldId47 = self.oldId()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    self._adaptor.addChild(root_0, oldId47.tree)


                char_literal48 = self.match(self.input, LPAREN, self.FOLLOW_LPAREN_in_oldExpression2314)
                if self._state.backtracking == 0:
                    char_literal48_tree = self._adaptor.createWithPayload(char_literal48)
                    self._adaptor.addChild(root_0, char_literal48_tree)



                self._state.following.append(self.FOLLOW_expression_in_oldExpression2316)
                expression49 = self.expression()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    self._adaptor.addChild(root_0, expression49.tree)


                char_literal50 = self.match(self.input, RPAREN, self.FOLLOW_RPAREN_in_oldExpression2318)
                if self._state.backtracking == 0:
                    char_literal50_tree = self._adaptor.createWithPayload(char_literal50)
                    self._adaptor.addChild(root_0, char_literal50_tree)



                if self._state.backtracking == 0:
                    pass

                    retval.result = OldExpression()
                    retval.result.item = ((expression49 is not None) and [expression49.result] or [None])[0]






                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                success = True


            except RecognitionException as re:
                self.recover(self.input, re)

        finally:
            if self._state.backtracking > 0:
                self.memoize(self.input, 31, oldExpression_StartIndex, success)


            pass
        return retval

    # $ANTLR end "oldExpression"


    class oldId_return(ParserRuleReturnScope):
        def __init__(self):
            super(SolidityInvariantParser.oldId_return, self).__init__()

            self.tree = None





    # $ANTLR start "oldId"
    # SolidityInvariant.g:546:1: oldId : ( '\\\\old' | '\\\\pre' );
    def oldId(self, ):
        retval = self.oldId_return()
        retval.start = self.input.LT(1)

        oldId_StartIndex = self.input.index()

        root_0 = None

        set51 = None

        set51_tree = None

        success = False

        try:
            try:
                if self._state.backtracking > 0 and self.alreadyParsedRule(self.input, 32):
                    # for cached failed rules, alreadyParsedRule will raise an exception
                    success = True
                    return retval


                # SolidityInvariant.g:547:5: ( '\\\\old' | '\\\\pre' )
                # SolidityInvariant.g:
                pass
                root_0 = self._adaptor.nil()


                set51 = self.input.LT(1)

                if (60 <= self.input.LA(1) <= 61):
                    self.input.consume()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, self._adaptor.createWithPayload(set51))

                    self._state.errorRecovery = False


                else:
                    if self._state.backtracking > 0:
                        raise BacktrackingFailed


                    mse = MismatchedSetException(None, self.input)
                    raise mse





                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                success = True


            except RecognitionException as re:
                self.recover(self.input, re)

        finally:
            if self._state.backtracking > 0:
                self.memoize(self.input, 32, oldId_StartIndex, success)


            pass
        return retval

    # $ANTLR end "oldId"


    class specQuantifiedExpression_return(ParserRuleReturnScope):
        def __init__(self):
            super(SolidityInvariantParser.specQuantifiedExpression_return, self).__init__()

            self.result = None
            self.tree = None





    # $ANTLR start "specQuantifiedExpression"
    # SolidityInvariant.g:551:1: specQuantifiedExpression returns [result] : ( '\\\\forall' IDENTIFIER ':' type ';' expression | '\\\\exists' IDENTIFIER ':' type ';' expression );
    def specQuantifiedExpression(self, ):
        retval = self.specQuantifiedExpression_return()
        retval.start = self.input.LT(1)

        specQuantifiedExpression_StartIndex = self.input.index()

        root_0 = None

        string_literal52 = None
        IDENTIFIER53 = None
        char_literal54 = None
        char_literal56 = None
        string_literal58 = None
        IDENTIFIER59 = None
        char_literal60 = None
        char_literal62 = None
        type55 = None
        expression57 = None
        type61 = None
        expression63 = None

        string_literal52_tree = None
        IDENTIFIER53_tree = None
        char_literal54_tree = None
        char_literal56_tree = None
        string_literal58_tree = None
        IDENTIFIER59_tree = None
        char_literal60_tree = None
        char_literal62_tree = None

        success = False

        try:
            try:
                if self._state.backtracking > 0 and self.alreadyParsedRule(self.input, 33):
                    # for cached failed rules, alreadyParsedRule will raise an exception
                    success = True
                    return retval


                # SolidityInvariant.g:552:5: ( '\\\\forall' IDENTIFIER ':' type ';' expression | '\\\\exists' IDENTIFIER ':' type ';' expression )
                alt29 = 2
                LA29_0 = self.input.LA(1)

                if (LA29_0 == 59) :
                    alt29 = 1
                elif (LA29_0 == 58) :
                    alt29 = 2
                else:
                    if self._state.backtracking > 0:
                        raise BacktrackingFailed


                    nvae = NoViableAltException("", 29, 0, self.input)

                    raise nvae


                if alt29 == 1:
                    # SolidityInvariant.g:552:9: '\\\\forall' IDENTIFIER ':' type ';' expression
                    pass
                    root_0 = self._adaptor.nil()


                    string_literal52 = self.match(self.input, 59, self.FOLLOW_59_in_specQuantifiedExpression2380)
                    if self._state.backtracking == 0:
                        string_literal52_tree = self._adaptor.createWithPayload(string_literal52)
                        self._adaptor.addChild(root_0, string_literal52_tree)



                    IDENTIFIER53 = self.match(self.input, IDENTIFIER, self.FOLLOW_IDENTIFIER_in_specQuantifiedExpression2382)
                    if self._state.backtracking == 0:
                        IDENTIFIER53_tree = self._adaptor.createWithPayload(IDENTIFIER53)
                        self._adaptor.addChild(root_0, IDENTIFIER53_tree)



                    char_literal54 = self.match(self.input, COLON, self.FOLLOW_COLON_in_specQuantifiedExpression2384)
                    if self._state.backtracking == 0:
                        char_literal54_tree = self._adaptor.createWithPayload(char_literal54)
                        self._adaptor.addChild(root_0, char_literal54_tree)



                    self._state.following.append(self.FOLLOW_type_in_specQuantifiedExpression2386)
                    type55 = self.type()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, type55.tree)


                    char_literal56 = self.match(self.input, SEMI, self.FOLLOW_SEMI_in_specQuantifiedExpression2388)
                    if self._state.backtracking == 0:
                        char_literal56_tree = self._adaptor.createWithPayload(char_literal56)
                        self._adaptor.addChild(root_0, char_literal56_tree)



                    self._state.following.append(self.FOLLOW_expression_in_specQuantifiedExpression2390)
                    expression57 = self.expression()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, expression57.tree)


                    if self._state.backtracking == 0:
                        pass

                        retval.result = ForallExpression()
                        retval.result.var = IDENTIFIER53.text
                        retval.result.typ = ((type55 is not None) and [type55.result] or [None])[0]
                        retval.result.cond = ((expression57 is not None) and [expression57.result] or [None])[0]





                elif alt29 == 2:
                    # SolidityInvariant.g:559:9: '\\\\exists' IDENTIFIER ':' type ';' expression
                    pass
                    root_0 = self._adaptor.nil()


                    string_literal58 = self.match(self.input, 58, self.FOLLOW_58_in_specQuantifiedExpression2410)
                    if self._state.backtracking == 0:
                        string_literal58_tree = self._adaptor.createWithPayload(string_literal58)
                        self._adaptor.addChild(root_0, string_literal58_tree)



                    IDENTIFIER59 = self.match(self.input, IDENTIFIER, self.FOLLOW_IDENTIFIER_in_specQuantifiedExpression2412)
                    if self._state.backtracking == 0:
                        IDENTIFIER59_tree = self._adaptor.createWithPayload(IDENTIFIER59)
                        self._adaptor.addChild(root_0, IDENTIFIER59_tree)



                    char_literal60 = self.match(self.input, COLON, self.FOLLOW_COLON_in_specQuantifiedExpression2414)
                    if self._state.backtracking == 0:
                        char_literal60_tree = self._adaptor.createWithPayload(char_literal60)
                        self._adaptor.addChild(root_0, char_literal60_tree)



                    self._state.following.append(self.FOLLOW_type_in_specQuantifiedExpression2416)
                    type61 = self.type()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, type61.tree)


                    char_literal62 = self.match(self.input, SEMI, self.FOLLOW_SEMI_in_specQuantifiedExpression2418)
                    if self._state.backtracking == 0:
                        char_literal62_tree = self._adaptor.createWithPayload(char_literal62)
                        self._adaptor.addChild(root_0, char_literal62_tree)



                    self._state.following.append(self.FOLLOW_expression_in_specQuantifiedExpression2420)
                    expression63 = self.expression()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, expression63.tree)


                    if self._state.backtracking == 0:
                        pass

                        retval.result = ExistsExpression()
                        retval.result.var = IDENTIFIER59.text
                        retval.result.typ = ((type61 is not None) and [type61.result] or [None])[0]
                        retval.result.cond = ((expression63 is not None) and [expression63.result] or [None])[0]





                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                success = True


            except RecognitionException as re:
                self.recover(self.input, re)

        finally:
            if self._state.backtracking > 0:
                self.memoize(self.input, 33, specQuantifiedExpression_StartIndex, success)


            pass
        return retval

    # $ANTLR end "specQuantifiedExpression"


    class type_return(ParserRuleReturnScope):
        def __init__(self):
            super(SolidityInvariantParser.type_return, self).__init__()

            self.result = None
            self.tree = None





    # $ANTLR start "type"
    # SolidityInvariant.g:568:1: type returns [result] : ( UINT256 | INT | INT256 | BOOL | STRING | BYTES );
    def type(self, ):
        retval = self.type_return()
        retval.start = self.input.LT(1)

        type_StartIndex = self.input.index()

        root_0 = None

        UINT25664 = None
        INT65 = None
        INT25666 = None
        BOOL67 = None
        STRING68 = None
        BYTES69 = None

        UINT25664_tree = None
        INT65_tree = None
        INT25666_tree = None
        BOOL67_tree = None
        STRING68_tree = None
        BYTES69_tree = None

        success = False

        try:
            try:
                if self._state.backtracking > 0 and self.alreadyParsedRule(self.input, 34):
                    # for cached failed rules, alreadyParsedRule will raise an exception
                    success = True
                    return retval


                # SolidityInvariant.g:569:5: ( UINT256 | INT | INT256 | BOOL | STRING | BYTES )
                alt30 = 6
                LA30 = self.input.LA(1)
                if LA30 == UINT256:
                    alt30 = 1
                elif LA30 == INT:
                    alt30 = 2
                elif LA30 == INT256:
                    alt30 = 3
                elif LA30 == BOOL:
                    alt30 = 4
                elif LA30 == STRING:
                    alt30 = 5
                elif LA30 == BYTES:
                    alt30 = 6
                else:
                    if self._state.backtracking > 0:
                        raise BacktrackingFailed


                    nvae = NoViableAltException("", 30, 0, self.input)

                    raise nvae


                if alt30 == 1:
                    # SolidityInvariant.g:569:9: UINT256
                    pass
                    root_0 = self._adaptor.nil()


                    UINT25664 = self.match(self.input, UINT256, self.FOLLOW_UINT256_in_type2453)
                    if self._state.backtracking == 0:
                        UINT25664_tree = self._adaptor.createWithPayload(UINT25664)
                        self._adaptor.addChild(root_0, UINT25664_tree)



                    if self._state.backtracking == 0:
                        pass
                        retval.result =  TypeLiteral('uint256')




                elif alt30 == 2:
                    # SolidityInvariant.g:570:9: INT
                    pass
                    root_0 = self._adaptor.nil()


                    INT65 = self.match(self.input, INT, self.FOLLOW_INT_in_type2469)
                    if self._state.backtracking == 0:
                        INT65_tree = self._adaptor.createWithPayload(INT65)
                        self._adaptor.addChild(root_0, INT65_tree)



                    if self._state.backtracking == 0:
                        pass
                        retval.result =  TypeLiteral('int')




                elif alt30 == 3:
                    # SolidityInvariant.g:571:9: INT256
                    pass
                    root_0 = self._adaptor.nil()


                    INT25666 = self.match(self.input, INT256, self.FOLLOW_INT256_in_type2489)
                    if self._state.backtracking == 0:
                        INT25666_tree = self._adaptor.createWithPayload(INT25666)
                        self._adaptor.addChild(root_0, INT25666_tree)



                    if self._state.backtracking == 0:
                        pass
                        retval.result =  TypeLiteral('int256')




                elif alt30 == 4:
                    # SolidityInvariant.g:572:9: BOOL
                    pass
                    root_0 = self._adaptor.nil()


                    BOOL67 = self.match(self.input, BOOL, self.FOLLOW_BOOL_in_type2506)
                    if self._state.backtracking == 0:
                        BOOL67_tree = self._adaptor.createWithPayload(BOOL67)
                        self._adaptor.addChild(root_0, BOOL67_tree)



                    if self._state.backtracking == 0:
                        pass
                        retval.result =  TypeLiteral('bool')




                elif alt30 == 5:
                    # SolidityInvariant.g:573:9: STRING
                    pass
                    root_0 = self._adaptor.nil()


                    STRING68 = self.match(self.input, STRING, self.FOLLOW_STRING_in_type2525)
                    if self._state.backtracking == 0:
                        STRING68_tree = self._adaptor.createWithPayload(STRING68)
                        self._adaptor.addChild(root_0, STRING68_tree)



                    if self._state.backtracking == 0:
                        pass
                        retval.result =  TypeLiteral('string')




                elif alt30 == 6:
                    # SolidityInvariant.g:574:9: BYTES
                    pass
                    root_0 = self._adaptor.nil()


                    BYTES69 = self.match(self.input, BYTES, self.FOLLOW_BYTES_in_type2542)
                    if self._state.backtracking == 0:
                        BYTES69_tree = self._adaptor.createWithPayload(BYTES69)
                        self._adaptor.addChild(root_0, BYTES69_tree)



                    if self._state.backtracking == 0:
                        pass
                        retval.result =  TypeLiteral('bytes')




                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                success = True


            except RecognitionException as re:
                self.recover(self.input, re)

        finally:
            if self._state.backtracking > 0:
                self.memoize(self.input, 34, type_StartIndex, success)


            pass
        return retval

    # $ANTLR end "type"

    # $ANTLR start "synpred1_SolidityInvariant"
    def synpred1_SolidityInvariant_fragment(self, ):
        th = None
        el = None


        # SolidityInvariant.g:68:11: ( '?' th= expression ':' el= conditionalExpression )
        # SolidityInvariant.g:68:11: '?' th= expression ':' el= conditionalExpression
        pass
        root_0 = self._adaptor.nil()


        self.match(self.input, QUES, self.FOLLOW_QUES_in_synpred1_SolidityInvariant155)


        self._state.following.append(self.FOLLOW_expression_in_synpred1_SolidityInvariant159)
        th = self.expression()

        self._state.following.pop()


        self.match(self.input, COLON, self.FOLLOW_COLON_in_synpred1_SolidityInvariant161)


        self._state.following.append(self.FOLLOW_conditionalExpression_in_synpred1_SolidityInvariant165)
        el = self.conditionalExpression()

        self._state.following.pop()




    # $ANTLR end "synpred1_SolidityInvariant"



    # $ANTLR start "synpred2_SolidityInvariant"
    def synpred2_SolidityInvariant_fragment(self, ):
        eqOp = None
        r = None


        # SolidityInvariant.g:82:11: (eqOp= equivalenceOp r= impliesExpression )
        # SolidityInvariant.g:82:11: eqOp= equivalenceOp r= impliesExpression
        pass
        root_0 = self._adaptor.nil()


        self._state.following.append(self.FOLLOW_equivalenceOp_in_synpred2_SolidityInvariant217)
        eqOp = self.equivalenceOp()

        self._state.following.pop()


        self._state.following.append(self.FOLLOW_impliesExpression_in_synpred2_SolidityInvariant221)
        r = self.impliesExpression()

        self._state.following.pop()




    # $ANTLR end "synpred2_SolidityInvariant"



    # $ANTLR start "synpred4_SolidityInvariant"
    def synpred4_SolidityInvariant_fragment(self, ):
        ie = None


        # SolidityInvariant.g:103:10: ( '==>' ie= impliesNonBackwardExpression )
        # SolidityInvariant.g:103:10: '==>' ie= impliesNonBackwardExpression
        pass
        root_0 = self._adaptor.nil()


        self.match(self.input, 57, self.FOLLOW_57_in_synpred4_SolidityInvariant324)


        self._state.following.append(self.FOLLOW_impliesNonBackwardExpression_in_synpred4_SolidityInvariant328)
        ie = self.impliesNonBackwardExpression()

        self._state.following.pop()




    # $ANTLR end "synpred4_SolidityInvariant"



    # $ANTLR start "synpred5_SolidityInvariant"
    def synpred5_SolidityInvariant_fragment(self, ):
        ant = None
        ie = None


        # SolidityInvariant.g:99:9: (ant= logicalOrExpression ( '==>' ie= impliesNonBackwardExpression )* )
        # SolidityInvariant.g:99:9: ant= logicalOrExpression ( '==>' ie= impliesNonBackwardExpression )*
        pass
        root_0 = self._adaptor.nil()


        self._state.following.append(self.FOLLOW_logicalOrExpression_in_synpred5_SolidityInvariant303)
        ant = self.logicalOrExpression()

        self._state.following.pop()


        # SolidityInvariant.g:103:9: ( '==>' ie= impliesNonBackwardExpression )*
        while True: #loop31
            alt31 = 2
            LA31_0 = self.input.LA(1)

            if (LA31_0 == 57) :
                alt31 = 1


            if alt31 == 1:
                # SolidityInvariant.g:103:10: '==>' ie= impliesNonBackwardExpression
                pass
                self.match(self.input, 57, self.FOLLOW_57_in_synpred5_SolidityInvariant324)


                self._state.following.append(self.FOLLOW_impliesNonBackwardExpression_in_synpred5_SolidityInvariant328)
                ie = self.impliesNonBackwardExpression()

                self._state.following.pop()



            else:
                break #loop31




    # $ANTLR end "synpred5_SolidityInvariant"



    # $ANTLR start "synpred6_SolidityInvariant"
    def synpred6_SolidityInvariant_fragment(self, ):
        right = None


        # SolidityInvariant.g:121:10: ( '<==' right= logicalOrExpression )
        # SolidityInvariant.g:121:10: '<==' right= logicalOrExpression
        pass
        root_0 = self._adaptor.nil()


        self.match(self.input, 55, self.FOLLOW_55_in_synpred6_SolidityInvariant396)


        self._state.following.append(self.FOLLOW_logicalOrExpression_in_synpred6_SolidityInvariant400)
        right = self.logicalOrExpression()

        self._state.following.pop()




    # $ANTLR end "synpred6_SolidityInvariant"



    # $ANTLR start "synpred7_SolidityInvariant"
    def synpred7_SolidityInvariant_fragment(self, ):
        ie = None


        # SolidityInvariant.g:137:10: ( '==>' ie= impliesNonBackwardExpression )
        # SolidityInvariant.g:137:10: '==>' ie= impliesNonBackwardExpression
        pass
        root_0 = self._adaptor.nil()


        self.match(self.input, 57, self.FOLLOW_57_in_synpred7_SolidityInvariant481)


        self._state.following.append(self.FOLLOW_impliesNonBackwardExpression_in_synpred7_SolidityInvariant485)
        ie = self.impliesNonBackwardExpression()

        self._state.following.pop()




    # $ANTLR end "synpred7_SolidityInvariant"



    # $ANTLR start "synpred8_SolidityInvariant"
    def synpred8_SolidityInvariant_fragment(self, ):
        r = None


        # SolidityInvariant.g:155:11: ( '||' r= logicalAndExpression )
        # SolidityInvariant.g:155:11: '||' r= logicalAndExpression
        pass
        root_0 = self._adaptor.nil()


        self.match(self.input, BARBAR, self.FOLLOW_BARBAR_in_synpred8_SolidityInvariant557)


        self._state.following.append(self.FOLLOW_logicalAndExpression_in_synpred8_SolidityInvariant561)
        r = self.logicalAndExpression()

        self._state.following.pop()




    # $ANTLR end "synpred8_SolidityInvariant"



    # $ANTLR start "synpred9_SolidityInvariant"
    def synpred9_SolidityInvariant_fragment(self, ):
        r = None


        # SolidityInvariant.g:170:11: ( '&&' r= equalityExpression )
        # SolidityInvariant.g:170:11: '&&' r= equalityExpression
        pass
        root_0 = self._adaptor.nil()


        self.match(self.input, AMPAMP, self.FOLLOW_AMPAMP_in_synpred9_SolidityInvariant612)


        self._state.following.append(self.FOLLOW_equalityExpression_in_synpred9_SolidityInvariant616)
        r = self.equalityExpression()

        self._state.following.pop()




    # $ANTLR end "synpred9_SolidityInvariant"



    # $ANTLR start "synpred11_SolidityInvariant"
    def synpred11_SolidityInvariant_fragment(self, ):
        op = None
        r = None

        op_tree = None

        # SolidityInvariant.g:189:10: (op= ( '==' | '!=' ) r= relationalExpression )
        # SolidityInvariant.g:189:10: op= ( '==' | '!=' ) r= relationalExpression
        pass
        root_0 = self._adaptor.nil()


        op = self.input.LT(1)

        if self.input.LA(1) == EQEQ or self.input.LA(1) == NOTEQ:
            self.input.consume()
            self._state.errorRecovery = False


        else:
            if self._state.backtracking > 0:
                raise BacktrackingFailed


            mse = MismatchedSetException(None, self.input)
            raise mse



        self._state.following.append(self.FOLLOW_relationalExpression_in_synpred11_SolidityInvariant688)
        r = self.relationalExpression()

        self._state.following.pop()




    # $ANTLR end "synpred11_SolidityInvariant"



    # $ANTLR start "synpred15_SolidityInvariant"
    def synpred15_SolidityInvariant_fragment(self, ):
        op = None
        r = None

        op_tree = None

        # SolidityInvariant.g:212:13: (op= ( '<' | '<=' | '>' | '>=' ) r= shiftExpression )
        # SolidityInvariant.g:212:13: op= ( '<' | '<=' | '>' | '>=' ) r= shiftExpression
        pass
        root_0 = self._adaptor.nil()


        op = self.input.LT(1)

        if (GE <= self.input.LA(1) <= GT) or self.input.LA(1) == LE or self.input.LA(1) == LT:
            self.input.consume()
            self._state.errorRecovery = False


        else:
            if self._state.backtracking > 0:
                raise BacktrackingFailed


            mse = MismatchedSetException(None, self.input)
            raise mse



        self._state.following.append(self.FOLLOW_shiftExpression_in_synpred15_SolidityInvariant802)
        r = self.shiftExpression()

        self._state.following.pop()




    # $ANTLR end "synpred15_SolidityInvariant"



    # $ANTLR start "synpred17_SolidityInvariant"
    def synpred17_SolidityInvariant_fragment(self, ):
        op = None
        r = None

        op_tree = None

        # SolidityInvariant.g:235:13: (op= ( '<<' | '>>' ) r= additiveExpression )
        # SolidityInvariant.g:235:13: op= ( '<<' | '>>' ) r= additiveExpression
        pass
        root_0 = self._adaptor.nil()


        op = self.input.LT(1)

        if self.input.LA(1) == LSHIFT or self.input.LA(1) == RSHIFT:
            self.input.consume()
            self._state.errorRecovery = False


        else:
            if self._state.backtracking > 0:
                raise BacktrackingFailed


            mse = MismatchedSetException(None, self.input)
            raise mse



        self._state.following.append(self.FOLLOW_additiveExpression_in_synpred17_SolidityInvariant908)
        r = self.additiveExpression()

        self._state.following.pop()




    # $ANTLR end "synpred17_SolidityInvariant"



    # $ANTLR start "synpred19_SolidityInvariant"
    def synpred19_SolidityInvariant_fragment(self, ):
        op = None
        r = None

        op_tree = None

        # SolidityInvariant.g:258:13: (op= ( '+' | '-' ) r= multiplicativeExpression )
        # SolidityInvariant.g:258:13: op= ( '+' | '-' ) r= multiplicativeExpression
        pass
        root_0 = self._adaptor.nil()


        op = self.input.LT(1)

        if self.input.LA(1) == PLUS or self.input.LA(1) == SUB:
            self.input.consume()
            self._state.errorRecovery = False


        else:
            if self._state.backtracking > 0:
                raise BacktrackingFailed


            mse = MismatchedSetException(None, self.input)
            raise mse



        self._state.following.append(self.FOLLOW_multiplicativeExpression_in_synpred19_SolidityInvariant1014)
        r = self.multiplicativeExpression()

        self._state.following.pop()




    # $ANTLR end "synpred19_SolidityInvariant"



    # $ANTLR start "synpred22_SolidityInvariant"
    def synpred22_SolidityInvariant_fragment(self, ):
        op = None
        r = None

        op_tree = None

        # SolidityInvariant.g:281:13: (op= ( '*' | '/' | '%' ) r= unaryExpression )
        # SolidityInvariant.g:281:13: op= ( '*' | '/' | '%' ) r= unaryExpression
        pass
        root_0 = self._adaptor.nil()


        op = self.input.LT(1)

        if self.input.LA(1) == PERCENT or (SLASH <= self.input.LA(1) <= STAR):
            self.input.consume()
            self._state.errorRecovery = False


        else:
            if self._state.backtracking > 0:
                raise BacktrackingFailed


            mse = MismatchedSetException(None, self.input)
            raise mse



        self._state.following.append(self.FOLLOW_unaryExpression_in_synpred22_SolidityInvariant1124)
        r = self.unaryExpression()

        self._state.following.pop()




    # $ANTLR end "synpred22_SolidityInvariant"



    # $ANTLR start "synpred23_SolidityInvariant"
    def synpred23_SolidityInvariant_fragment(self, ):
        op = None
        r = None

        op_tree = None

        # SolidityInvariant.g:304:10: (op= '|' r= bitwiseXorExpression )
        # SolidityInvariant.g:304:10: op= '|' r= bitwiseXorExpression
        pass
        root_0 = self._adaptor.nil()


        op = self.match(self.input, BAR, self.FOLLOW_BAR_in_synpred23_SolidityInvariant1208)


        self._state.following.append(self.FOLLOW_bitwiseXorExpression_in_synpred23_SolidityInvariant1212)
        r = self.bitwiseXorExpression()

        self._state.following.pop()




    # $ANTLR end "synpred23_SolidityInvariant"



    # $ANTLR start "synpred24_SolidityInvariant"
    def synpred24_SolidityInvariant_fragment(self, ):
        op = None
        r = None

        op_tree = None

        # SolidityInvariant.g:326:10: (op= '^' r= bitwiseAndExpression )
        # SolidityInvariant.g:326:10: op= '^' r= bitwiseAndExpression
        pass
        root_0 = self._adaptor.nil()


        op = self.match(self.input, CARET, self.FOLLOW_CARET_in_synpred24_SolidityInvariant1295)


        self._state.following.append(self.FOLLOW_bitwiseAndExpression_in_synpred24_SolidityInvariant1299)
        r = self.bitwiseAndExpression()

        self._state.following.pop()




    # $ANTLR end "synpred24_SolidityInvariant"



    # $ANTLR start "synpred25_SolidityInvariant"
    def synpred25_SolidityInvariant_fragment(self, ):
        op = None
        r = None

        op_tree = None

        # SolidityInvariant.g:348:10: (op= '&' r= equalityExpression )
        # SolidityInvariant.g:348:10: op= '&' r= equalityExpression
        pass
        root_0 = self._adaptor.nil()


        op = self.match(self.input, AMP, self.FOLLOW_AMP_in_synpred25_SolidityInvariant1382)


        self._state.following.append(self.FOLLOW_equalityExpression_in_synpred25_SolidityInvariant1386)
        r = self.equalityExpression()

        self._state.following.pop()




    # $ANTLR end "synpred25_SolidityInvariant"




    def synpred7_SolidityInvariant(self):
        self._state.backtracking += 1
        start = self.input.mark()
        try:
            self.synpred7_SolidityInvariant_fragment()
        except BacktrackingFailed:
            success = False
        else:
            success = True
        self.input.rewind(start)
        self._state.backtracking -= 1
        return success

    def synpred11_SolidityInvariant(self):
        self._state.backtracking += 1
        start = self.input.mark()
        try:
            self.synpred11_SolidityInvariant_fragment()
        except BacktrackingFailed:
            success = False
        else:
            success = True
        self.input.rewind(start)
        self._state.backtracking -= 1
        return success

    def synpred25_SolidityInvariant(self):
        self._state.backtracking += 1
        start = self.input.mark()
        try:
            self.synpred25_SolidityInvariant_fragment()
        except BacktrackingFailed:
            success = False
        else:
            success = True
        self.input.rewind(start)
        self._state.backtracking -= 1
        return success

    def synpred4_SolidityInvariant(self):
        self._state.backtracking += 1
        start = self.input.mark()
        try:
            self.synpred4_SolidityInvariant_fragment()
        except BacktrackingFailed:
            success = False
        else:
            success = True
        self.input.rewind(start)
        self._state.backtracking -= 1
        return success

    def synpred15_SolidityInvariant(self):
        self._state.backtracking += 1
        start = self.input.mark()
        try:
            self.synpred15_SolidityInvariant_fragment()
        except BacktrackingFailed:
            success = False
        else:
            success = True
        self.input.rewind(start)
        self._state.backtracking -= 1
        return success

    def synpred6_SolidityInvariant(self):
        self._state.backtracking += 1
        start = self.input.mark()
        try:
            self.synpred6_SolidityInvariant_fragment()
        except BacktrackingFailed:
            success = False
        else:
            success = True
        self.input.rewind(start)
        self._state.backtracking -= 1
        return success

    def synpred24_SolidityInvariant(self):
        self._state.backtracking += 1
        start = self.input.mark()
        try:
            self.synpred24_SolidityInvariant_fragment()
        except BacktrackingFailed:
            success = False
        else:
            success = True
        self.input.rewind(start)
        self._state.backtracking -= 1
        return success

    def synpred9_SolidityInvariant(self):
        self._state.backtracking += 1
        start = self.input.mark()
        try:
            self.synpred9_SolidityInvariant_fragment()
        except BacktrackingFailed:
            success = False
        else:
            success = True
        self.input.rewind(start)
        self._state.backtracking -= 1
        return success

    def synpred17_SolidityInvariant(self):
        self._state.backtracking += 1
        start = self.input.mark()
        try:
            self.synpred17_SolidityInvariant_fragment()
        except BacktrackingFailed:
            success = False
        else:
            success = True
        self.input.rewind(start)
        self._state.backtracking -= 1
        return success

    def synpred23_SolidityInvariant(self):
        self._state.backtracking += 1
        start = self.input.mark()
        try:
            self.synpred23_SolidityInvariant_fragment()
        except BacktrackingFailed:
            success = False
        else:
            success = True
        self.input.rewind(start)
        self._state.backtracking -= 1
        return success

    def synpred5_SolidityInvariant(self):
        self._state.backtracking += 1
        start = self.input.mark()
        try:
            self.synpred5_SolidityInvariant_fragment()
        except BacktrackingFailed:
            success = False
        else:
            success = True
        self.input.rewind(start)
        self._state.backtracking -= 1
        return success

    def synpred8_SolidityInvariant(self):
        self._state.backtracking += 1
        start = self.input.mark()
        try:
            self.synpred8_SolidityInvariant_fragment()
        except BacktrackingFailed:
            success = False
        else:
            success = True
        self.input.rewind(start)
        self._state.backtracking -= 1
        return success

    def synpred1_SolidityInvariant(self):
        self._state.backtracking += 1
        start = self.input.mark()
        try:
            self.synpred1_SolidityInvariant_fragment()
        except BacktrackingFailed:
            success = False
        else:
            success = True
        self.input.rewind(start)
        self._state.backtracking -= 1
        return success

    def synpred22_SolidityInvariant(self):
        self._state.backtracking += 1
        start = self.input.mark()
        try:
            self.synpred22_SolidityInvariant_fragment()
        except BacktrackingFailed:
            success = False
        else:
            success = True
        self.input.rewind(start)
        self._state.backtracking -= 1
        return success

    def synpred19_SolidityInvariant(self):
        self._state.backtracking += 1
        start = self.input.mark()
        try:
            self.synpred19_SolidityInvariant_fragment()
        except BacktrackingFailed:
            success = False
        else:
            success = True
        self.input.rewind(start)
        self._state.backtracking -= 1
        return success

    def synpred2_SolidityInvariant(self):
        self._state.backtracking += 1
        start = self.input.mark()
        try:
            self.synpred2_SolidityInvariant_fragment()
        except BacktrackingFailed:
            success = False
        else:
            success = True
        self.input.rewind(start)
        self._state.backtracking -= 1
        return success





    FOLLOW_expression_in_solidityInvariant73 = frozenset([43])
    FOLLOW_SEMI_in_solidityInvariant75 = frozenset([1])
    FOLLOW_conditionalExpression_in_expression108 = frozenset([1])
    FOLLOW_equivalenceExpression_in_conditionalExpression143 = frozenset([1, 38])
    FOLLOW_QUES_in_conditionalExpression155 = frozenset([6, 10, 21, 24, 31, 37, 47, 48, 50, 51, 58, 59, 60, 61, 62, 63, 64, 65, 66])
    FOLLOW_expression_in_conditionalExpression159 = frozenset([13])
    FOLLOW_COLON_in_conditionalExpression161 = frozenset([6, 10, 21, 24, 31, 37, 47, 48, 50, 51, 58, 59, 60, 61, 62, 63, 64, 65, 66])
    FOLLOW_conditionalExpression_in_conditionalExpression165 = frozenset([1])
    FOLLOW_impliesExpression_in_equivalenceExpression203 = frozenset([1, 54, 56])
    FOLLOW_equivalenceOp_in_equivalenceExpression217 = frozenset([6, 10, 21, 24, 31, 37, 47, 48, 50, 51, 58, 59, 60, 61, 62, 63, 64, 65, 66])
    FOLLOW_impliesExpression_in_equivalenceExpression221 = frozenset([1])
    FOLLOW_56_in_equivalenceOp257 = frozenset([1])
    FOLLOW_54_in_equivalenceOp273 = frozenset([1])
    FOLLOW_logicalOrExpression_in_impliesExpression303 = frozenset([1, 57])
    FOLLOW_57_in_impliesExpression324 = frozenset([6, 10, 21, 24, 31, 37, 47, 48, 50, 51, 58, 59, 60, 61, 62, 63, 64, 65, 66])
    FOLLOW_impliesNonBackwardExpression_in_impliesExpression328 = frozenset([1, 57])
    FOLLOW_logicalOrExpression_in_impliesExpression375 = frozenset([1, 55])
    FOLLOW_55_in_impliesExpression396 = frozenset([6, 10, 21, 24, 31, 37, 47, 48, 50, 51, 58, 59, 60, 61, 62, 63, 64, 65, 66])
    FOLLOW_logicalOrExpression_in_impliesExpression400 = frozenset([1, 55])
    FOLLOW_logicalOrExpression_in_impliesNonBackwardExpression460 = frozenset([1, 57])
    FOLLOW_57_in_impliesNonBackwardExpression481 = frozenset([6, 10, 21, 24, 31, 37, 47, 48, 50, 51, 58, 59, 60, 61, 62, 63, 64, 65, 66])
    FOLLOW_impliesNonBackwardExpression_in_impliesNonBackwardExpression485 = frozenset([1, 57])
    FOLLOW_logicalAndExpression_in_logicalOrExpression545 = frozenset([1, 8])
    FOLLOW_BARBAR_in_logicalOrExpression557 = frozenset([6, 10, 21, 24, 31, 37, 47, 48, 50, 51, 58, 59, 60, 61, 62, 63, 64, 65, 66])
    FOLLOW_logicalAndExpression_in_logicalOrExpression561 = frozenset([1, 8])
    FOLLOW_bitwiseOrExpression_in_logicalAndExpression600 = frozenset([1, 5])
    FOLLOW_AMPAMP_in_logicalAndExpression612 = frozenset([6, 10, 21, 24, 31, 37, 47, 48, 50, 51, 58, 59, 60, 61, 62, 63, 64, 65, 66])
    FOLLOW_equalityExpression_in_logicalAndExpression616 = frozenset([1, 5])
    FOLLOW_relationalExpression_in_equalityExpression655 = frozenset([1, 17, 34])
    FOLLOW_set_in_equalityExpression678 = frozenset([6, 10, 21, 24, 31, 37, 47, 48, 50, 51, 58, 59, 60, 61, 62, 63, 64, 65, 66])
    FOLLOW_relationalExpression_in_equalityExpression688 = frozenset([1, 17, 34])
    FOLLOW_shiftExpression_in_relationalExpression748 = frozenset([1, 19, 20, 29, 33])
    FOLLOW_set_in_relationalExpression784 = frozenset([6, 10, 21, 24, 31, 37, 47, 48, 50, 51, 58, 59, 60, 61, 62, 63, 64, 65, 66])
    FOLLOW_shiftExpression_in_relationalExpression802 = frozenset([1, 19, 20, 29, 33])
    FOLLOW_additiveExpression_in_shiftExpression862 = frozenset([1, 32, 42])
    FOLLOW_set_in_shiftExpression898 = frozenset([6, 10, 21, 24, 31, 37, 47, 48, 50, 51, 58, 59, 60, 61, 62, 63, 64, 65, 66])
    FOLLOW_additiveExpression_in_shiftExpression908 = frozenset([1, 32, 42])
    FOLLOW_multiplicativeExpression_in_additiveExpression968 = frozenset([1, 37, 48])
    FOLLOW_set_in_additiveExpression1004 = frozenset([6, 10, 21, 24, 31, 37, 47, 48, 50, 51, 58, 59, 60, 61, 62, 63, 64, 65, 66])
    FOLLOW_multiplicativeExpression_in_additiveExpression1014 = frozenset([1, 37, 48])
    FOLLOW_unaryExpression_in_multiplicativeExpression1074 = frozenset([1, 36, 44, 45])
    FOLLOW_set_in_multiplicativeExpression1110 = frozenset([6, 10, 21, 24, 31, 37, 47, 48, 50, 51, 58, 59, 60, 61, 62, 63, 64, 65, 66])
    FOLLOW_unaryExpression_in_multiplicativeExpression1124 = frozenset([1, 36, 44, 45])
    FOLLOW_bitwiseXorExpression_in_bitwiseOrExpression1185 = frozenset([1, 7])
    FOLLOW_BAR_in_bitwiseOrExpression1208 = frozenset([6, 10, 21, 24, 31, 37, 47, 48, 50, 51, 58, 59, 60, 61, 62, 63, 64, 65, 66])
    FOLLOW_bitwiseXorExpression_in_bitwiseOrExpression1212 = frozenset([1, 7])
    FOLLOW_bitwiseAndExpression_in_bitwiseXorExpression1272 = frozenset([1, 12])
    FOLLOW_CARET_in_bitwiseXorExpression1295 = frozenset([6, 10, 21, 24, 31, 37, 47, 48, 50, 51, 58, 59, 60, 61, 62, 63, 64, 65, 66])
    FOLLOW_bitwiseAndExpression_in_bitwiseXorExpression1299 = frozenset([1, 12])
    FOLLOW_equalityExpression_in_bitwiseAndExpression1359 = frozenset([1, 4])
    FOLLOW_AMP_in_bitwiseAndExpression1382 = frozenset([6, 10, 21, 24, 31, 37, 47, 48, 50, 51, 58, 59, 60, 61, 62, 63, 64, 65, 66])
    FOLLOW_equalityExpression_in_bitwiseAndExpression1386 = frozenset([1, 4])
    FOLLOW_PLUS_in_unaryExpression1444 = frozenset([6, 10, 21, 24, 31, 37, 47, 48, 50, 51, 58, 59, 60, 61, 62, 63, 64, 65, 66])
    FOLLOW_unaryExpression_in_unaryExpression1448 = frozenset([1])
    FOLLOW_SUB_in_unaryExpression1468 = frozenset([6, 10, 21, 24, 31, 37, 47, 48, 50, 51, 58, 59, 60, 61, 62, 63, 64, 65, 66])
    FOLLOW_unaryExpression_in_unaryExpression1472 = frozenset([1])
    FOLLOW_BANG_in_unaryExpression1492 = frozenset([6, 10, 21, 24, 31, 37, 47, 48, 50, 51, 58, 59, 60, 61, 62, 63, 64, 65, 66])
    FOLLOW_unaryExpression_in_unaryExpression1496 = frozenset([1])
    FOLLOW_TILDE_in_unaryExpression1516 = frozenset([6, 10, 21, 24, 31, 37, 47, 48, 50, 51, 58, 59, 60, 61, 62, 63, 64, 65, 66])
    FOLLOW_unaryExpression_in_unaryExpression1520 = frozenset([1])
    FOLLOW_unaryPrimary_in_unaryExpression1540 = frozenset([1])
    FOLLOW_simpleIdentifier_in_unaryPrimary1573 = frozenset([1, 28])
    FOLLOW_indexSuffix_in_unaryPrimary1575 = frozenset([1])
    FOLLOW_solidityGlobal_in_unaryPrimary1596 = frozenset([1])
    FOLLOW_complexReference_in_unaryPrimary1616 = frozenset([1])
    FOLLOW_literal_in_unaryPrimary1636 = frozenset([1])
    FOLLOW_parExpression_in_unaryPrimary1656 = frozenset([1])
    FOLLOW_jmlPrimary_in_unaryPrimary1676 = frozenset([1])
    FOLLOW_set_in_solidityGlobal1711 = frozenset([15])
    FOLLOW_DOT_in_solidityGlobal1740 = frozenset([21])
    FOLLOW_IDENTIFIER_in_solidityGlobal1744 = frozenset([1, 15])
    FOLLOW_IDENTIFIER_in_simpleIdentifier1780 = frozenset([1])
    FOLLOW_IDENTIFIER_in_complexReference1815 = frozenset([15])
    FOLLOW_DOT_in_complexReference1836 = frozenset([21])
    FOLLOW_IDENTIFIER_in_complexReference1840 = frozenset([1, 15, 28, 31])
    FOLLOW_identifierSuffix_in_complexReference1878 = frozenset([1])
    FOLLOW_INTLIT_in_literal1917 = frozenset([1])
    FOLLOW_BOOLLIT_in_literal1937 = frozenset([1])
    FOLLOW_STRINGLIT_in_literal1957 = frozenset([1])
    FOLLOW_LPAREN_in_parExpression1990 = frozenset([6, 10, 21, 24, 31, 37, 47, 48, 50, 51, 58, 59, 60, 61, 62, 63, 64, 65, 66])
    FOLLOW_expression_in_parExpression1992 = frozenset([41])
    FOLLOW_RPAREN_in_parExpression1994 = frozenset([1])
    FOLLOW_LBRACKET_in_indexSuffix2027 = frozenset([6, 10, 21, 24, 31, 37, 47, 48, 50, 51, 58, 59, 60, 61, 62, 63, 64, 65, 66])
    FOLLOW_expression_in_indexSuffix2029 = frozenset([40])
    FOLLOW_RBRACKET_in_indexSuffix2031 = frozenset([1])
    FOLLOW_LPAREN_in_identifierSuffix2065 = frozenset([6, 10, 21, 24, 31, 37, 41, 47, 48, 50, 51, 58, 59, 60, 61, 62, 63, 64, 65, 66])
    FOLLOW_argList_in_identifierSuffix2069 = frozenset([41])
    FOLLOW_RPAREN_in_identifierSuffix2072 = frozenset([1])
    FOLLOW_LBRACKET_in_identifierSuffix2092 = frozenset([6, 10, 21, 24, 31, 37, 47, 48, 50, 51, 58, 59, 60, 61, 62, 63, 64, 65, 66])
    FOLLOW_expression_in_identifierSuffix2094 = frozenset([40])
    FOLLOW_RBRACKET_in_identifierSuffix2096 = frozenset([1])
    FOLLOW_expression_in_argList2131 = frozenset([1, 14])
    FOLLOW_argListRest_in_argList2135 = frozenset([1, 14])
    FOLLOW_COMMA_in_argListRest2169 = frozenset([6, 10, 21, 24, 31, 37, 47, 48, 50, 51, 58, 59, 60, 61, 62, 63, 64, 65, 66])
    FOLLOW_expression_in_argListRest2173 = frozenset([1])
    FOLLOW_resultExpression_in_jmlPrimary2206 = frozenset([1])
    FOLLOW_oldExpression_in_jmlPrimary2226 = frozenset([1])
    FOLLOW_specQuantifiedExpression_in_jmlPrimary2246 = frozenset([1])
    FOLLOW_62_in_resultExpression2279 = frozenset([1])
    FOLLOW_oldId_in_oldExpression2312 = frozenset([31])
    FOLLOW_LPAREN_in_oldExpression2314 = frozenset([6, 10, 21, 24, 31, 37, 47, 48, 50, 51, 58, 59, 60, 61, 62, 63, 64, 65, 66])
    FOLLOW_expression_in_oldExpression2316 = frozenset([41])
    FOLLOW_RPAREN_in_oldExpression2318 = frozenset([1])
    FOLLOW_59_in_specQuantifiedExpression2380 = frozenset([21])
    FOLLOW_IDENTIFIER_in_specQuantifiedExpression2382 = frozenset([13])
    FOLLOW_COLON_in_specQuantifiedExpression2384 = frozenset([9, 11, 22, 23, 46, 52])
    FOLLOW_type_in_specQuantifiedExpression2386 = frozenset([43])
    FOLLOW_SEMI_in_specQuantifiedExpression2388 = frozenset([6, 10, 21, 24, 31, 37, 47, 48, 50, 51, 58, 59, 60, 61, 62, 63, 64, 65, 66])
    FOLLOW_expression_in_specQuantifiedExpression2390 = frozenset([1])
    FOLLOW_58_in_specQuantifiedExpression2410 = frozenset([21])
    FOLLOW_IDENTIFIER_in_specQuantifiedExpression2412 = frozenset([13])
    FOLLOW_COLON_in_specQuantifiedExpression2414 = frozenset([9, 11, 22, 23, 46, 52])
    FOLLOW_type_in_specQuantifiedExpression2416 = frozenset([43])
    FOLLOW_SEMI_in_specQuantifiedExpression2418 = frozenset([6, 10, 21, 24, 31, 37, 47, 48, 50, 51, 58, 59, 60, 61, 62, 63, 64, 65, 66])
    FOLLOW_expression_in_specQuantifiedExpression2420 = frozenset([1])
    FOLLOW_UINT256_in_type2453 = frozenset([1])
    FOLLOW_INT_in_type2469 = frozenset([1])
    FOLLOW_INT256_in_type2489 = frozenset([1])
    FOLLOW_BOOL_in_type2506 = frozenset([1])
    FOLLOW_STRING_in_type2525 = frozenset([1])
    FOLLOW_BYTES_in_type2542 = frozenset([1])
    FOLLOW_QUES_in_synpred1_SolidityInvariant155 = frozenset([6, 10, 21, 24, 31, 37, 47, 48, 50, 51, 58, 59, 60, 61, 62, 63, 64, 65, 66])
    FOLLOW_expression_in_synpred1_SolidityInvariant159 = frozenset([13])
    FOLLOW_COLON_in_synpred1_SolidityInvariant161 = frozenset([6, 10, 21, 24, 31, 37, 47, 48, 50, 51, 58, 59, 60, 61, 62, 63, 64, 65, 66])
    FOLLOW_conditionalExpression_in_synpred1_SolidityInvariant165 = frozenset([1])
    FOLLOW_equivalenceOp_in_synpred2_SolidityInvariant217 = frozenset([6, 10, 21, 24, 31, 37, 47, 48, 50, 51, 58, 59, 60, 61, 62, 63, 64, 65, 66])
    FOLLOW_impliesExpression_in_synpred2_SolidityInvariant221 = frozenset([1])
    FOLLOW_57_in_synpred4_SolidityInvariant324 = frozenset([6, 10, 21, 24, 31, 37, 47, 48, 50, 51, 58, 59, 60, 61, 62, 63, 64, 65, 66])
    FOLLOW_impliesNonBackwardExpression_in_synpred4_SolidityInvariant328 = frozenset([1])
    FOLLOW_logicalOrExpression_in_synpred5_SolidityInvariant303 = frozenset([1, 57])
    FOLLOW_57_in_synpred5_SolidityInvariant324 = frozenset([6, 10, 21, 24, 31, 37, 47, 48, 50, 51, 58, 59, 60, 61, 62, 63, 64, 65, 66])
    FOLLOW_impliesNonBackwardExpression_in_synpred5_SolidityInvariant328 = frozenset([1, 57])
    FOLLOW_55_in_synpred6_SolidityInvariant396 = frozenset([6, 10, 21, 24, 31, 37, 47, 48, 50, 51, 58, 59, 60, 61, 62, 63, 64, 65, 66])
    FOLLOW_logicalOrExpression_in_synpred6_SolidityInvariant400 = frozenset([1])
    FOLLOW_57_in_synpred7_SolidityInvariant481 = frozenset([6, 10, 21, 24, 31, 37, 47, 48, 50, 51, 58, 59, 60, 61, 62, 63, 64, 65, 66])
    FOLLOW_impliesNonBackwardExpression_in_synpred7_SolidityInvariant485 = frozenset([1])
    FOLLOW_BARBAR_in_synpred8_SolidityInvariant557 = frozenset([6, 10, 21, 24, 31, 37, 47, 48, 50, 51, 58, 59, 60, 61, 62, 63, 64, 65, 66])
    FOLLOW_logicalAndExpression_in_synpred8_SolidityInvariant561 = frozenset([1])
    FOLLOW_AMPAMP_in_synpred9_SolidityInvariant612 = frozenset([6, 10, 21, 24, 31, 37, 47, 48, 50, 51, 58, 59, 60, 61, 62, 63, 64, 65, 66])
    FOLLOW_equalityExpression_in_synpred9_SolidityInvariant616 = frozenset([1])
    FOLLOW_set_in_synpred11_SolidityInvariant678 = frozenset([6, 10, 21, 24, 31, 37, 47, 48, 50, 51, 58, 59, 60, 61, 62, 63, 64, 65, 66])
    FOLLOW_relationalExpression_in_synpred11_SolidityInvariant688 = frozenset([1])
    FOLLOW_set_in_synpred15_SolidityInvariant784 = frozenset([6, 10, 21, 24, 31, 37, 47, 48, 50, 51, 58, 59, 60, 61, 62, 63, 64, 65, 66])
    FOLLOW_shiftExpression_in_synpred15_SolidityInvariant802 = frozenset([1])
    FOLLOW_set_in_synpred17_SolidityInvariant898 = frozenset([6, 10, 21, 24, 31, 37, 47, 48, 50, 51, 58, 59, 60, 61, 62, 63, 64, 65, 66])
    FOLLOW_additiveExpression_in_synpred17_SolidityInvariant908 = frozenset([1])
    FOLLOW_set_in_synpred19_SolidityInvariant1004 = frozenset([6, 10, 21, 24, 31, 37, 47, 48, 50, 51, 58, 59, 60, 61, 62, 63, 64, 65, 66])
    FOLLOW_multiplicativeExpression_in_synpred19_SolidityInvariant1014 = frozenset([1])
    FOLLOW_set_in_synpred22_SolidityInvariant1110 = frozenset([6, 10, 21, 24, 31, 37, 47, 48, 50, 51, 58, 59, 60, 61, 62, 63, 64, 65, 66])
    FOLLOW_unaryExpression_in_synpred22_SolidityInvariant1124 = frozenset([1])
    FOLLOW_BAR_in_synpred23_SolidityInvariant1208 = frozenset([6, 10, 21, 24, 31, 37, 47, 48, 50, 51, 58, 59, 60, 61, 62, 63, 64, 65, 66])
    FOLLOW_bitwiseXorExpression_in_synpred23_SolidityInvariant1212 = frozenset([1])
    FOLLOW_CARET_in_synpred24_SolidityInvariant1295 = frozenset([6, 10, 21, 24, 31, 37, 47, 48, 50, 51, 58, 59, 60, 61, 62, 63, 64, 65, 66])
    FOLLOW_bitwiseAndExpression_in_synpred24_SolidityInvariant1299 = frozenset([1])
    FOLLOW_AMP_in_synpred25_SolidityInvariant1382 = frozenset([6, 10, 21, 24, 31, 37, 47, 48, 50, 51, 58, 59, 60, 61, 62, 63, 64, 65, 66])
    FOLLOW_equalityExpression_in_synpred25_SolidityInvariant1386 = frozenset([1])



def main(argv, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr):
    from antlr3.main import ParserMain
    main = ParserMain("SolidityInvariantLexer", SolidityInvariantParser)

    main.stdin = stdin
    main.stdout = stdout
    main.stderr = stderr
    main.execute(argv)

def parse_expr(expr_str):
    """
    Parses a Solidity invariant expression string or AST node and returns its AST representation.
    Automatically strips any trailing semicolon and filters invalid patterns.
    """
    try:
        # Handle non-string input (already-parsed AST object)
        if not isinstance(expr_str, str):
            try:
                expr_str = expr_str.text()
            except Exception as inner_ex:
                print(f"🚫 [AST-TO-STRING FAIL] Cannot convert: '{expr_str}' → {inner_ex}")
                return None

        print(f"🧼 CLEANING expression in parse_expr(): '{expr_str}'")

        # Strip whitespace and semicolon
        expr_str = expr_str.strip().rstrip(';')
        expr_str = re.sub(r'\s+', ' ', expr_str)

        # Skip clearly invalid expressions
        if not expr_str or expr_str.endswith('.'):
            print(f"🚫 Skipping invalid expression: '{expr_str}'")
            return None

        # Setup ANTLR parsing pipeline
        input_stream = antlr3.ANTLRStringStream(expr_str + ";")
        lexer = SolidityInvariantLexer(input_stream)
        token_stream = antlr3.CommonTokenStream(lexer)
        parser = SolidityInvariantParser(token_stream)

        # Parse expression
        parse_tree = parser.solidityInvariant()
        print(f"🔍 ANTLR parse tree object: {parse_tree}")
        print(f"🔎 ANTLR result attribute: {getattr(parse_tree, 'result', None)}")

        # Use parse_tree.result if available
        parsed_result = getattr(parse_tree, 'result', None)

        if parsed_result:
            print(f"✅ Parsed OK: {expr_str} → {parsed_result.text()} ({type(parsed_result).__name__})")
            return parsed_result
        else:
            fallback_text = getattr(parse_tree, 'text', lambda: None)()
            if fallback_text:
                print(f"⚠️ .result was None, fallback to parse_tree → {fallback_text}")
                return parse_tree
            else:
                print(f"❌ parse_expr() could not extract usable AST from: '{expr_str}'")
                print(f"📎 parse_tree class: {type(parse_tree).__name__}")
                return None

    except Exception as e:
        print(f"🚫 parse_expr() exception for: '{expr_str}' → {e}")
        return None


if __name__ == '__main__':
    main(sys.argv)
