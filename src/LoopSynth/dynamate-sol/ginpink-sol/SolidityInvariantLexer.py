# $ANTLR 3.5.3 SolidityInvariant.g 2025-06-12 12:41:29

import sys
from antlr3 import *
from antlr3.compat import set, frozenset



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


class SolidityInvariantLexer(Lexer):

    grammarFileName = "SolidityInvariant.g"
    api_version = 1

    def __init__(self, input=None, state=None):
        if state is None:
            state = RecognizerSharedState()
        super(SolidityInvariantLexer, self).__init__(input, state)

        self.delegates = []

        self.dfa9 = self.DFA9(
            self, 9,
            eot = self.DFA9_eot,
            eof = self.DFA9_eof,
            min = self.DFA9_min,
            max = self.DFA9_max,
            accept = self.DFA9_accept,
            special = self.DFA9_special,
            transition = self.DFA9_transition
            )






    # $ANTLR start "T__54"
    def mT__54(self, ):
        try:
            _type = T__54
            _channel = DEFAULT_CHANNEL

            # SolidityInvariant.g:7:7: ( '<=!=>' )
            # SolidityInvariant.g:7:9: '<=!=>'
            pass 
            self.match("<=!=>")




            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "T__54"



    # $ANTLR start "T__55"
    def mT__55(self, ):
        try:
            _type = T__55
            _channel = DEFAULT_CHANNEL

            # SolidityInvariant.g:8:7: ( '<==' )
            # SolidityInvariant.g:8:9: '<=='
            pass 
            self.match("<==")




            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "T__55"



    # $ANTLR start "T__56"
    def mT__56(self, ):
        try:
            _type = T__56
            _channel = DEFAULT_CHANNEL

            # SolidityInvariant.g:9:7: ( '<==>' )
            # SolidityInvariant.g:9:9: '<==>'
            pass 
            self.match("<==>")




            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "T__56"



    # $ANTLR start "T__57"
    def mT__57(self, ):
        try:
            _type = T__57
            _channel = DEFAULT_CHANNEL

            # SolidityInvariant.g:10:7: ( '==>' )
            # SolidityInvariant.g:10:9: '==>'
            pass 
            self.match("==>")




            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "T__57"



    # $ANTLR start "T__58"
    def mT__58(self, ):
        try:
            _type = T__58
            _channel = DEFAULT_CHANNEL

            # SolidityInvariant.g:11:7: ( '\\\\exists' )
            # SolidityInvariant.g:11:9: '\\\\exists'
            pass 
            self.match("\\exists")




            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "T__58"



    # $ANTLR start "T__59"
    def mT__59(self, ):
        try:
            _type = T__59
            _channel = DEFAULT_CHANNEL

            # SolidityInvariant.g:12:7: ( '\\\\forall' )
            # SolidityInvariant.g:12:9: '\\\\forall'
            pass 
            self.match("\\forall")




            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "T__59"



    # $ANTLR start "T__60"
    def mT__60(self, ):
        try:
            _type = T__60
            _channel = DEFAULT_CHANNEL

            # SolidityInvariant.g:13:7: ( '\\\\old' )
            # SolidityInvariant.g:13:9: '\\\\old'
            pass 
            self.match("\\old")




            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "T__60"



    # $ANTLR start "T__61"
    def mT__61(self, ):
        try:
            _type = T__61
            _channel = DEFAULT_CHANNEL

            # SolidityInvariant.g:14:7: ( '\\\\pre' )
            # SolidityInvariant.g:14:9: '\\\\pre'
            pass 
            self.match("\\pre")




            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "T__61"



    # $ANTLR start "T__62"
    def mT__62(self, ):
        try:
            _type = T__62
            _channel = DEFAULT_CHANNEL

            # SolidityInvariant.g:15:7: ( '\\\\result' )
            # SolidityInvariant.g:15:9: '\\\\result'
            pass 
            self.match("\\result")




            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "T__62"



    # $ANTLR start "T__63"
    def mT__63(self, ):
        try:
            _type = T__63
            _channel = DEFAULT_CHANNEL

            # SolidityInvariant.g:16:7: ( 'address' )
            # SolidityInvariant.g:16:9: 'address'
            pass 
            self.match("address")




            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "T__63"



    # $ANTLR start "T__64"
    def mT__64(self, ):
        try:
            _type = T__64
            _channel = DEFAULT_CHANNEL

            # SolidityInvariant.g:17:7: ( 'block' )
            # SolidityInvariant.g:17:9: 'block'
            pass 
            self.match("block")




            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "T__64"



    # $ANTLR start "T__65"
    def mT__65(self, ):
        try:
            _type = T__65
            _channel = DEFAULT_CHANNEL

            # SolidityInvariant.g:18:7: ( 'msg' )
            # SolidityInvariant.g:18:9: 'msg'
            pass 
            self.match("msg")




            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "T__65"



    # $ANTLR start "T__66"
    def mT__66(self, ):
        try:
            _type = T__66
            _channel = DEFAULT_CHANNEL

            # SolidityInvariant.g:19:7: ( 'tx' )
            # SolidityInvariant.g:19:9: 'tx'
            pass 
            self.match("tx")




            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "T__66"



    # $ANTLR start "INTLIT"
    def mINTLIT(self, ):
        try:
            _type = INTLIT
            _channel = DEFAULT_CHANNEL

            # SolidityInvariant.g:582:5: ( ( '0' .. '9' )+ )
            # SolidityInvariant.g:582:9: ( '0' .. '9' )+
            pass 
            # SolidityInvariant.g:582:9: ( '0' .. '9' )+
            cnt1 = 0
            while True: #loop1
                alt1 = 2
                LA1_0 = self.input.LA(1)

                if ((48 <= LA1_0 <= 57)) :
                    alt1 = 1


                if alt1 == 1:
                    # SolidityInvariant.g:
                    pass 
                    if (48 <= self.input.LA(1) <= 57):
                        self.input.consume()
                    else:
                        mse = MismatchedSetException(None, self.input)
                        self.recover(mse)
                        raise mse




                else:
                    if cnt1 >= 1:
                        break #loop1

                    eee = EarlyExitException(1, self.input)
                    raise eee

                cnt1 += 1




            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "INTLIT"



    # $ANTLR start "BOOLLIT"
    def mBOOLLIT(self, ):
        try:
            _type = BOOLLIT
            _channel = DEFAULT_CHANNEL

            # SolidityInvariant.g:586:5: ( 'true' | 'false' )
            alt2 = 2
            LA2_0 = self.input.LA(1)

            if (LA2_0 == 116) :
                alt2 = 1
            elif (LA2_0 == 102) :
                alt2 = 2
            else:
                nvae = NoViableAltException("", 2, 0, self.input)

                raise nvae


            if alt2 == 1:
                # SolidityInvariant.g:586:9: 'true'
                pass 
                self.match("true")



            elif alt2 == 2:
                # SolidityInvariant.g:587:9: 'false'
                pass 
                self.match("false")



            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "BOOLLIT"



    # $ANTLR start "STRINGLIT"
    def mSTRINGLIT(self, ):
        try:
            _type = STRINGLIT
            _channel = DEFAULT_CHANNEL

            # SolidityInvariant.g:591:5: ( '\"' ( EscapeSequence |~ ( '\\\\' | '\"' ) )* '\"' )
            # SolidityInvariant.g:591:9: '\"' ( EscapeSequence |~ ( '\\\\' | '\"' ) )* '\"'
            pass 
            self.match(34)

            # SolidityInvariant.g:591:13: ( EscapeSequence |~ ( '\\\\' | '\"' ) )*
            while True: #loop3
                alt3 = 3
                LA3_0 = self.input.LA(1)

                if (LA3_0 == 92) :
                    alt3 = 1
                elif ((0 <= LA3_0 <= 33) or (35 <= LA3_0 <= 91) or (93 <= LA3_0 <= 65535)) :
                    alt3 = 2


                if alt3 == 1:
                    # SolidityInvariant.g:591:15: EscapeSequence
                    pass 
                    self.mEscapeSequence()



                elif alt3 == 2:
                    # SolidityInvariant.g:591:32: ~ ( '\\\\' | '\"' )
                    pass 
                    if (0 <= self.input.LA(1) <= 33) or (35 <= self.input.LA(1) <= 91) or (93 <= self.input.LA(1) <= 65535):
                        self.input.consume()
                    else:
                        mse = MismatchedSetException(None, self.input)
                        self.recover(mse)
                        raise mse




                else:
                    break #loop3


            self.match(34)



            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "STRINGLIT"



    # $ANTLR start "EscapeSequence"
    def mEscapeSequence(self, ):
        try:
            # SolidityInvariant.g:595:5: ( '\\\\' ( 'b' | 't' | 'n' | 'f' | 'r' | '\"' | '\\'' | '\\\\' | ( '0' .. '3' ) ( '0' .. '7' ) ( '0' .. '7' ) | ( '0' .. '7' ) ( '0' .. '7' ) | ( '0' .. '7' ) ) )
            # SolidityInvariant.g:595:9: '\\\\' ( 'b' | 't' | 'n' | 'f' | 'r' | '\"' | '\\'' | '\\\\' | ( '0' .. '3' ) ( '0' .. '7' ) ( '0' .. '7' ) | ( '0' .. '7' ) ( '0' .. '7' ) | ( '0' .. '7' ) )
            pass 
            self.match(92)

            # SolidityInvariant.g:595:14: ( 'b' | 't' | 'n' | 'f' | 'r' | '\"' | '\\'' | '\\\\' | ( '0' .. '3' ) ( '0' .. '7' ) ( '0' .. '7' ) | ( '0' .. '7' ) ( '0' .. '7' ) | ( '0' .. '7' ) )
            alt4 = 11
            LA4 = self.input.LA(1)
            if LA4 == 98:
                alt4 = 1
            elif LA4 == 116:
                alt4 = 2
            elif LA4 == 110:
                alt4 = 3
            elif LA4 == 102:
                alt4 = 4
            elif LA4 == 114:
                alt4 = 5
            elif LA4 == 34:
                alt4 = 6
            elif LA4 == 39:
                alt4 = 7
            elif LA4 == 92:
                alt4 = 8
            elif LA4 == 48 or LA4 == 49 or LA4 == 50 or LA4 == 51:
                LA4_9 = self.input.LA(2)

                if ((48 <= LA4_9 <= 55)) :
                    LA4_11 = self.input.LA(3)

                    if ((48 <= LA4_11 <= 55)) :
                        alt4 = 9
                    else:
                        alt4 = 10

                else:
                    alt4 = 11

            elif LA4 == 52 or LA4 == 53 or LA4 == 54 or LA4 == 55:
                LA4_10 = self.input.LA(2)

                if ((48 <= LA4_10 <= 55)) :
                    alt4 = 10
                else:
                    alt4 = 11

            else:
                nvae = NoViableAltException("", 4, 0, self.input)

                raise nvae


            if alt4 == 1:
                # SolidityInvariant.g:596:13: 'b'
                pass 
                self.match(98)


            elif alt4 == 2:
                # SolidityInvariant.g:596:19: 't'
                pass 
                self.match(116)


            elif alt4 == 3:
                # SolidityInvariant.g:596:25: 'n'
                pass 
                self.match(110)


            elif alt4 == 4:
                # SolidityInvariant.g:596:31: 'f'
                pass 
                self.match(102)


            elif alt4 == 5:
                # SolidityInvariant.g:596:37: 'r'
                pass 
                self.match(114)


            elif alt4 == 6:
                # SolidityInvariant.g:596:43: '\"'
                pass 
                self.match(34)


            elif alt4 == 7:
                # SolidityInvariant.g:596:49: '\\''
                pass 
                self.match(39)


            elif alt4 == 8:
                # SolidityInvariant.g:596:56: '\\\\'
                pass 
                self.match(92)


            elif alt4 == 9:
                # SolidityInvariant.g:597:13: ( '0' .. '3' ) ( '0' .. '7' ) ( '0' .. '7' )
                pass 
                if (48 <= self.input.LA(1) <= 51):
                    self.input.consume()
                else:
                    mse = MismatchedSetException(None, self.input)
                    self.recover(mse)
                    raise mse



                if (48 <= self.input.LA(1) <= 55):
                    self.input.consume()
                else:
                    mse = MismatchedSetException(None, self.input)
                    self.recover(mse)
                    raise mse



                if (48 <= self.input.LA(1) <= 55):
                    self.input.consume()
                else:
                    mse = MismatchedSetException(None, self.input)
                    self.recover(mse)
                    raise mse




            elif alt4 == 10:
                # SolidityInvariant.g:598:13: ( '0' .. '7' ) ( '0' .. '7' )
                pass 
                if (48 <= self.input.LA(1) <= 55):
                    self.input.consume()
                else:
                    mse = MismatchedSetException(None, self.input)
                    self.recover(mse)
                    raise mse



                if (48 <= self.input.LA(1) <= 55):
                    self.input.consume()
                else:
                    mse = MismatchedSetException(None, self.input)
                    self.recover(mse)
                    raise mse




            elif alt4 == 11:
                # SolidityInvariant.g:599:13: ( '0' .. '7' )
                pass 
                if (48 <= self.input.LA(1) <= 55):
                    self.input.consume()
                else:
                    mse = MismatchedSetException(None, self.input)
                    self.recover(mse)
                    raise mse









        finally:
            pass

    # $ANTLR end "EscapeSequence"



    # $ANTLR start "WS"
    def mWS(self, ):
        try:
            _type = WS
            _channel = DEFAULT_CHANNEL

            # SolidityInvariant.g:604:5: ( ( ' ' | '\\r' | '\\t' | '\\u000C' | '\\n' ) )
            # SolidityInvariant.g:604:9: ( ' ' | '\\r' | '\\t' | '\\u000C' | '\\n' )
            pass 
            if (9 <= self.input.LA(1) <= 10) or (12 <= self.input.LA(1) <= 13) or self.input.LA(1) == 32:
                self.input.consume()
            else:
                mse = MismatchedSetException(None, self.input)
                self.recover(mse)
                raise mse



            #action start
            _channel = HIDDEN; 
            #action end




            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "WS"



    # $ANTLR start "LINE_COMMENT"
    def mLINE_COMMENT(self, ):
        try:
            _type = LINE_COMMENT
            _channel = DEFAULT_CHANNEL

            # SolidityInvariant.g:609:5: ( '//' (~ ( '\\n' | '\\r' ) )* ( ( '\\r' )? '\\n' )? )
            # SolidityInvariant.g:609:9: '//' (~ ( '\\n' | '\\r' ) )* ( ( '\\r' )? '\\n' )?
            pass 
            self.match("//")


            # SolidityInvariant.g:609:14: (~ ( '\\n' | '\\r' ) )*
            while True: #loop5
                alt5 = 2
                LA5_0 = self.input.LA(1)

                if ((0 <= LA5_0 <= 9) or (11 <= LA5_0 <= 12) or (14 <= LA5_0 <= 65535)) :
                    alt5 = 1


                if alt5 == 1:
                    # SolidityInvariant.g:
                    pass 
                    if (0 <= self.input.LA(1) <= 9) or (11 <= self.input.LA(1) <= 12) or (14 <= self.input.LA(1) <= 65535):
                        self.input.consume()
                    else:
                        mse = MismatchedSetException(None, self.input)
                        self.recover(mse)
                        raise mse




                else:
                    break #loop5


            # SolidityInvariant.g:609:28: ( ( '\\r' )? '\\n' )?
            alt7 = 2
            LA7_0 = self.input.LA(1)

            if (LA7_0 == 10 or LA7_0 == 13) :
                alt7 = 1
            if alt7 == 1:
                # SolidityInvariant.g:609:29: ( '\\r' )? '\\n'
                pass 
                # SolidityInvariant.g:609:29: ( '\\r' )?
                alt6 = 2
                LA6_0 = self.input.LA(1)

                if (LA6_0 == 13) :
                    alt6 = 1
                if alt6 == 1:
                    # SolidityInvariant.g:609:29: '\\r'
                    pass 
                    self.match(13)




                self.match(10)




            #action start
            _channel = HIDDEN; 
            #action end




            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "LINE_COMMENT"



    # $ANTLR start "UINT256"
    def mUINT256(self, ):
        try:
            _type = UINT256
            _channel = DEFAULT_CHANNEL

            # SolidityInvariant.g:617:9: ( 'uint256' )
            # SolidityInvariant.g:617:11: 'uint256'
            pass 
            self.match("uint256")




            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "UINT256"



    # $ANTLR start "INT"
    def mINT(self, ):
        try:
            _type = INT
            _channel = DEFAULT_CHANNEL

            # SolidityInvariant.g:618:9: ( 'int' )
            # SolidityInvariant.g:618:11: 'int'
            pass 
            self.match("int")




            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "INT"



    # $ANTLR start "INT256"
    def mINT256(self, ):
        try:
            _type = INT256
            _channel = DEFAULT_CHANNEL

            # SolidityInvariant.g:619:9: ( 'int256' )
            # SolidityInvariant.g:619:11: 'int256'
            pass 
            self.match("int256")




            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "INT256"



    # $ANTLR start "BOOL"
    def mBOOL(self, ):
        try:
            _type = BOOL
            _channel = DEFAULT_CHANNEL

            # SolidityInvariant.g:620:9: ( 'bool' )
            # SolidityInvariant.g:620:11: 'bool'
            pass 
            self.match("bool")




            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "BOOL"



    # $ANTLR start "STRING"
    def mSTRING(self, ):
        try:
            _type = STRING
            _channel = DEFAULT_CHANNEL

            # SolidityInvariant.g:621:9: ( 'string' )
            # SolidityInvariant.g:621:11: 'string'
            pass 
            self.match("string")




            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "STRING"



    # $ANTLR start "BYTES"
    def mBYTES(self, ):
        try:
            _type = BYTES
            _channel = DEFAULT_CHANNEL

            # SolidityInvariant.g:622:9: ( 'bytes' )
            # SolidityInvariant.g:622:11: 'bytes'
            pass 
            self.match("bytes")




            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "BYTES"



    # $ANTLR start "THIS"
    def mTHIS(self, ):
        try:
            _type = THIS
            _channel = DEFAULT_CHANNEL

            # SolidityInvariant.g:624:13: ( 'this' )
            # SolidityInvariant.g:624:15: 'this'
            pass 
            self.match("this")




            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "THIS"



    # $ANTLR start "NULL"
    def mNULL(self, ):
        try:
            _type = NULL
            _channel = DEFAULT_CHANNEL

            # SolidityInvariant.g:625:13: ( 'null' )
            # SolidityInvariant.g:625:15: 'null'
            pass 
            self.match("null")




            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "NULL"



    # $ANTLR start "SUPER"
    def mSUPER(self, ):
        try:
            _type = SUPER
            _channel = DEFAULT_CHANNEL

            # SolidityInvariant.g:626:13: ( 'super' )
            # SolidityInvariant.g:626:15: 'super'
            pass 
            self.match("super")




            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "SUPER"



    # $ANTLR start "LPAREN"
    def mLPAREN(self, ):
        try:
            _type = LPAREN
            _channel = DEFAULT_CHANNEL

            # SolidityInvariant.g:628:13: ( '(' )
            # SolidityInvariant.g:628:15: '('
            pass 
            self.match(40)



            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "LPAREN"



    # $ANTLR start "RPAREN"
    def mRPAREN(self, ):
        try:
            _type = RPAREN
            _channel = DEFAULT_CHANNEL

            # SolidityInvariant.g:629:13: ( ')' )
            # SolidityInvariant.g:629:15: ')'
            pass 
            self.match(41)



            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "RPAREN"



    # $ANTLR start "LBRACE"
    def mLBRACE(self, ):
        try:
            _type = LBRACE
            _channel = DEFAULT_CHANNEL

            # SolidityInvariant.g:630:13: ( '{' )
            # SolidityInvariant.g:630:15: '{'
            pass 
            self.match(123)



            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "LBRACE"



    # $ANTLR start "RBRACE"
    def mRBRACE(self, ):
        try:
            _type = RBRACE
            _channel = DEFAULT_CHANNEL

            # SolidityInvariant.g:631:13: ( '}' )
            # SolidityInvariant.g:631:15: '}'
            pass 
            self.match(125)



            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "RBRACE"



    # $ANTLR start "LBRACKET"
    def mLBRACKET(self, ):
        try:
            _type = LBRACKET
            _channel = DEFAULT_CHANNEL

            # SolidityInvariant.g:632:13: ( '[' )
            # SolidityInvariant.g:632:15: '['
            pass 
            self.match(91)



            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "LBRACKET"



    # $ANTLR start "RBRACKET"
    def mRBRACKET(self, ):
        try:
            _type = RBRACKET
            _channel = DEFAULT_CHANNEL

            # SolidityInvariant.g:633:13: ( ']' )
            # SolidityInvariant.g:633:15: ']'
            pass 
            self.match(93)



            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "RBRACKET"



    # $ANTLR start "SEMI"
    def mSEMI(self, ):
        try:
            _type = SEMI
            _channel = DEFAULT_CHANNEL

            # SolidityInvariant.g:634:13: ( ';' )
            # SolidityInvariant.g:634:15: ';'
            pass 
            self.match(59)



            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "SEMI"



    # $ANTLR start "COMMA"
    def mCOMMA(self, ):
        try:
            _type = COMMA
            _channel = DEFAULT_CHANNEL

            # SolidityInvariant.g:635:13: ( ',' )
            # SolidityInvariant.g:635:15: ','
            pass 
            self.match(44)



            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "COMMA"



    # $ANTLR start "DOT"
    def mDOT(self, ):
        try:
            _type = DOT
            _channel = DEFAULT_CHANNEL

            # SolidityInvariant.g:636:13: ( '.' )
            # SolidityInvariant.g:636:15: '.'
            pass 
            self.match(46)



            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "DOT"



    # $ANTLR start "EQ"
    def mEQ(self, ):
        try:
            _type = EQ
            _channel = DEFAULT_CHANNEL

            # SolidityInvariant.g:637:13: ( '=' )
            # SolidityInvariant.g:637:15: '='
            pass 
            self.match(61)



            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "EQ"



    # $ANTLR start "EQEQ"
    def mEQEQ(self, ):
        try:
            _type = EQEQ
            _channel = DEFAULT_CHANNEL

            # SolidityInvariant.g:639:13: ( '==' )
            # SolidityInvariant.g:639:15: '=='
            pass 
            self.match("==")




            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "EQEQ"



    # $ANTLR start "NOTEQ"
    def mNOTEQ(self, ):
        try:
            _type = NOTEQ
            _channel = DEFAULT_CHANNEL

            # SolidityInvariant.g:640:13: ( '!=' )
            # SolidityInvariant.g:640:15: '!='
            pass 
            self.match("!=")




            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "NOTEQ"



    # $ANTLR start "LE"
    def mLE(self, ):
        try:
            _type = LE
            _channel = DEFAULT_CHANNEL

            # SolidityInvariant.g:641:13: ( '<=' )
            # SolidityInvariant.g:641:15: '<='
            pass 
            self.match("<=")




            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "LE"



    # $ANTLR start "GE"
    def mGE(self, ):
        try:
            _type = GE
            _channel = DEFAULT_CHANNEL

            # SolidityInvariant.g:642:13: ( '>=' )
            # SolidityInvariant.g:642:15: '>='
            pass 
            self.match(">=")




            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "GE"



    # $ANTLR start "LSHIFT"
    def mLSHIFT(self, ):
        try:
            _type = LSHIFT
            _channel = DEFAULT_CHANNEL

            # SolidityInvariant.g:643:13: ( '<<' )
            # SolidityInvariant.g:643:15: '<<'
            pass 
            self.match("<<")




            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "LSHIFT"



    # $ANTLR start "RSHIFT"
    def mRSHIFT(self, ):
        try:
            _type = RSHIFT
            _channel = DEFAULT_CHANNEL

            # SolidityInvariant.g:644:13: ( '>>' )
            # SolidityInvariant.g:644:15: '>>'
            pass 
            self.match(">>")




            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "RSHIFT"



    # $ANTLR start "AMPAMP"
    def mAMPAMP(self, ):
        try:
            _type = AMPAMP
            _channel = DEFAULT_CHANNEL

            # SolidityInvariant.g:645:13: ( '&&' )
            # SolidityInvariant.g:645:15: '&&'
            pass 
            self.match("&&")




            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "AMPAMP"



    # $ANTLR start "BARBAR"
    def mBARBAR(self, ):
        try:
            _type = BARBAR
            _channel = DEFAULT_CHANNEL

            # SolidityInvariant.g:646:13: ( '||' )
            # SolidityInvariant.g:646:15: '||'
            pass 
            self.match("||")




            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "BARBAR"



    # $ANTLR start "LT"
    def mLT(self, ):
        try:
            _type = LT
            _channel = DEFAULT_CHANNEL

            # SolidityInvariant.g:648:13: ( '<' )
            # SolidityInvariant.g:648:15: '<'
            pass 
            self.match(60)



            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "LT"



    # $ANTLR start "GT"
    def mGT(self, ):
        try:
            _type = GT
            _channel = DEFAULT_CHANNEL

            # SolidityInvariant.g:649:13: ( '>' )
            # SolidityInvariant.g:649:15: '>'
            pass 
            self.match(62)



            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "GT"



    # $ANTLR start "BANG"
    def mBANG(self, ):
        try:
            _type = BANG
            _channel = DEFAULT_CHANNEL

            # SolidityInvariant.g:650:13: ( '!' )
            # SolidityInvariant.g:650:15: '!'
            pass 
            self.match(33)



            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "BANG"



    # $ANTLR start "TILDE"
    def mTILDE(self, ):
        try:
            _type = TILDE
            _channel = DEFAULT_CHANNEL

            # SolidityInvariant.g:651:13: ( '~' )
            # SolidityInvariant.g:651:15: '~'
            pass 
            self.match(126)



            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "TILDE"



    # $ANTLR start "QUES"
    def mQUES(self, ):
        try:
            _type = QUES
            _channel = DEFAULT_CHANNEL

            # SolidityInvariant.g:652:13: ( '?' )
            # SolidityInvariant.g:652:15: '?'
            pass 
            self.match(63)



            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "QUES"



    # $ANTLR start "COLON"
    def mCOLON(self, ):
        try:
            _type = COLON
            _channel = DEFAULT_CHANNEL

            # SolidityInvariant.g:653:13: ( ':' )
            # SolidityInvariant.g:653:15: ':'
            pass 
            self.match(58)



            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "COLON"



    # $ANTLR start "PLUS"
    def mPLUS(self, ):
        try:
            _type = PLUS
            _channel = DEFAULT_CHANNEL

            # SolidityInvariant.g:655:13: ( '+' )
            # SolidityInvariant.g:655:15: '+'
            pass 
            self.match(43)



            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "PLUS"



    # $ANTLR start "SUB"
    def mSUB(self, ):
        try:
            _type = SUB
            _channel = DEFAULT_CHANNEL

            # SolidityInvariant.g:656:13: ( '-' )
            # SolidityInvariant.g:656:15: '-'
            pass 
            self.match(45)



            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "SUB"



    # $ANTLR start "STAR"
    def mSTAR(self, ):
        try:
            _type = STAR
            _channel = DEFAULT_CHANNEL

            # SolidityInvariant.g:657:13: ( '*' )
            # SolidityInvariant.g:657:15: '*'
            pass 
            self.match(42)



            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "STAR"



    # $ANTLR start "SLASH"
    def mSLASH(self, ):
        try:
            _type = SLASH
            _channel = DEFAULT_CHANNEL

            # SolidityInvariant.g:658:13: ( '/' )
            # SolidityInvariant.g:658:15: '/'
            pass 
            self.match(47)



            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "SLASH"



    # $ANTLR start "AMP"
    def mAMP(self, ):
        try:
            _type = AMP
            _channel = DEFAULT_CHANNEL

            # SolidityInvariant.g:659:13: ( '&' )
            # SolidityInvariant.g:659:15: '&'
            pass 
            self.match(38)



            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "AMP"



    # $ANTLR start "BAR"
    def mBAR(self, ):
        try:
            _type = BAR
            _channel = DEFAULT_CHANNEL

            # SolidityInvariant.g:660:13: ( '|' )
            # SolidityInvariant.g:660:15: '|'
            pass 
            self.match(124)



            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "BAR"



    # $ANTLR start "CARET"
    def mCARET(self, ):
        try:
            _type = CARET
            _channel = DEFAULT_CHANNEL

            # SolidityInvariant.g:661:13: ( '^' )
            # SolidityInvariant.g:661:15: '^'
            pass 
            self.match(94)



            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "CARET"



    # $ANTLR start "PERCENT"
    def mPERCENT(self, ):
        try:
            _type = PERCENT
            _channel = DEFAULT_CHANNEL

            # SolidityInvariant.g:662:13: ( '%' )
            # SolidityInvariant.g:662:15: '%'
            pass 
            self.match(37)



            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "PERCENT"



    # $ANTLR start "IdentifierStart"
    def mIdentifierStart(self, ):
        try:
            # SolidityInvariant.g:666:5: ( 'a' .. 'z' | 'A' .. 'Z' | '_' )
            # SolidityInvariant.g:
            pass 
            if (65 <= self.input.LA(1) <= 90) or self.input.LA(1) == 95 or (97 <= self.input.LA(1) <= 122):
                self.input.consume()
            else:
                mse = MismatchedSetException(None, self.input)
                self.recover(mse)
                raise mse






        finally:
            pass

    # $ANTLR end "IdentifierStart"



    # $ANTLR start "IdentifierPart"
    def mIdentifierPart(self, ):
        try:
            # SolidityInvariant.g:672:5: ( IdentifierStart | '0' .. '9' )
            # SolidityInvariant.g:
            pass 
            if (48 <= self.input.LA(1) <= 57) or (65 <= self.input.LA(1) <= 90) or self.input.LA(1) == 95 or (97 <= self.input.LA(1) <= 122):
                self.input.consume()
            else:
                mse = MismatchedSetException(None, self.input)
                self.recover(mse)
                raise mse






        finally:
            pass

    # $ANTLR end "IdentifierPart"



    # $ANTLR start "IDENTIFIER"
    def mIDENTIFIER(self, ):
        try:
            _type = IDENTIFIER
            _channel = DEFAULT_CHANNEL

            # SolidityInvariant.g:677:5: ( IdentifierStart ( IdentifierPart )* )
            # SolidityInvariant.g:677:9: IdentifierStart ( IdentifierPart )*
            pass 
            self.mIdentifierStart()


            # SolidityInvariant.g:677:25: ( IdentifierPart )*
            while True: #loop8
                alt8 = 2
                LA8_0 = self.input.LA(1)

                if ((48 <= LA8_0 <= 57) or (65 <= LA8_0 <= 90) or LA8_0 == 95 or (97 <= LA8_0 <= 122)) :
                    alt8 = 1


                if alt8 == 1:
                    # SolidityInvariant.g:
                    pass 
                    if (48 <= self.input.LA(1) <= 57) or (65 <= self.input.LA(1) <= 90) or self.input.LA(1) == 95 or (97 <= self.input.LA(1) <= 122):
                        self.input.consume()
                    else:
                        mse = MismatchedSetException(None, self.input)
                        self.recover(mse)
                        raise mse




                else:
                    break #loop8




            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "IDENTIFIER"



    def mTokens(self):
        # SolidityInvariant.g:1:8: ( T__54 | T__55 | T__56 | T__57 | T__58 | T__59 | T__60 | T__61 | T__62 | T__63 | T__64 | T__65 | T__66 | INTLIT | BOOLLIT | STRINGLIT | WS | LINE_COMMENT | UINT256 | INT | INT256 | BOOL | STRING | BYTES | THIS | NULL | SUPER | LPAREN | RPAREN | LBRACE | RBRACE | LBRACKET | RBRACKET | SEMI | COMMA | DOT | EQ | EQEQ | NOTEQ | LE | GE | LSHIFT | RSHIFT | AMPAMP | BARBAR | LT | GT | BANG | TILDE | QUES | COLON | PLUS | SUB | STAR | SLASH | AMP | BAR | CARET | PERCENT | IDENTIFIER )
        alt9 = 60
        alt9 = self.dfa9.predict(self.input)
        if alt9 == 1:
            # SolidityInvariant.g:1:10: T__54
            pass 
            self.mT__54()



        elif alt9 == 2:
            # SolidityInvariant.g:1:16: T__55
            pass 
            self.mT__55()



        elif alt9 == 3:
            # SolidityInvariant.g:1:22: T__56
            pass 
            self.mT__56()



        elif alt9 == 4:
            # SolidityInvariant.g:1:28: T__57
            pass 
            self.mT__57()



        elif alt9 == 5:
            # SolidityInvariant.g:1:34: T__58
            pass 
            self.mT__58()



        elif alt9 == 6:
            # SolidityInvariant.g:1:40: T__59
            pass 
            self.mT__59()



        elif alt9 == 7:
            # SolidityInvariant.g:1:46: T__60
            pass 
            self.mT__60()



        elif alt9 == 8:
            # SolidityInvariant.g:1:52: T__61
            pass 
            self.mT__61()



        elif alt9 == 9:
            # SolidityInvariant.g:1:58: T__62
            pass 
            self.mT__62()



        elif alt9 == 10:
            # SolidityInvariant.g:1:64: T__63
            pass 
            self.mT__63()



        elif alt9 == 11:
            # SolidityInvariant.g:1:70: T__64
            pass 
            self.mT__64()



        elif alt9 == 12:
            # SolidityInvariant.g:1:76: T__65
            pass 
            self.mT__65()



        elif alt9 == 13:
            # SolidityInvariant.g:1:82: T__66
            pass 
            self.mT__66()



        elif alt9 == 14:
            # SolidityInvariant.g:1:88: INTLIT
            pass 
            self.mINTLIT()



        elif alt9 == 15:
            # SolidityInvariant.g:1:95: BOOLLIT
            pass 
            self.mBOOLLIT()



        elif alt9 == 16:
            # SolidityInvariant.g:1:103: STRINGLIT
            pass 
            self.mSTRINGLIT()



        elif alt9 == 17:
            # SolidityInvariant.g:1:113: WS
            pass 
            self.mWS()



        elif alt9 == 18:
            # SolidityInvariant.g:1:116: LINE_COMMENT
            pass 
            self.mLINE_COMMENT()



        elif alt9 == 19:
            # SolidityInvariant.g:1:129: UINT256
            pass 
            self.mUINT256()



        elif alt9 == 20:
            # SolidityInvariant.g:1:137: INT
            pass 
            self.mINT()



        elif alt9 == 21:
            # SolidityInvariant.g:1:141: INT256
            pass 
            self.mINT256()



        elif alt9 == 22:
            # SolidityInvariant.g:1:148: BOOL
            pass 
            self.mBOOL()



        elif alt9 == 23:
            # SolidityInvariant.g:1:153: STRING
            pass 
            self.mSTRING()



        elif alt9 == 24:
            # SolidityInvariant.g:1:160: BYTES
            pass 
            self.mBYTES()



        elif alt9 == 25:
            # SolidityInvariant.g:1:166: THIS
            pass 
            self.mTHIS()



        elif alt9 == 26:
            # SolidityInvariant.g:1:171: NULL
            pass 
            self.mNULL()



        elif alt9 == 27:
            # SolidityInvariant.g:1:176: SUPER
            pass 
            self.mSUPER()



        elif alt9 == 28:
            # SolidityInvariant.g:1:182: LPAREN
            pass 
            self.mLPAREN()



        elif alt9 == 29:
            # SolidityInvariant.g:1:189: RPAREN
            pass 
            self.mRPAREN()



        elif alt9 == 30:
            # SolidityInvariant.g:1:196: LBRACE
            pass 
            self.mLBRACE()



        elif alt9 == 31:
            # SolidityInvariant.g:1:203: RBRACE
            pass 
            self.mRBRACE()



        elif alt9 == 32:
            # SolidityInvariant.g:1:210: LBRACKET
            pass 
            self.mLBRACKET()



        elif alt9 == 33:
            # SolidityInvariant.g:1:219: RBRACKET
            pass 
            self.mRBRACKET()



        elif alt9 == 34:
            # SolidityInvariant.g:1:228: SEMI
            pass 
            self.mSEMI()



        elif alt9 == 35:
            # SolidityInvariant.g:1:233: COMMA
            pass 
            self.mCOMMA()



        elif alt9 == 36:
            # SolidityInvariant.g:1:239: DOT
            pass 
            self.mDOT()



        elif alt9 == 37:
            # SolidityInvariant.g:1:243: EQ
            pass 
            self.mEQ()



        elif alt9 == 38:
            # SolidityInvariant.g:1:246: EQEQ
            pass 
            self.mEQEQ()



        elif alt9 == 39:
            # SolidityInvariant.g:1:251: NOTEQ
            pass 
            self.mNOTEQ()



        elif alt9 == 40:
            # SolidityInvariant.g:1:257: LE
            pass 
            self.mLE()



        elif alt9 == 41:
            # SolidityInvariant.g:1:260: GE
            pass 
            self.mGE()



        elif alt9 == 42:
            # SolidityInvariant.g:1:263: LSHIFT
            pass 
            self.mLSHIFT()



        elif alt9 == 43:
            # SolidityInvariant.g:1:270: RSHIFT
            pass 
            self.mRSHIFT()



        elif alt9 == 44:
            # SolidityInvariant.g:1:277: AMPAMP
            pass 
            self.mAMPAMP()



        elif alt9 == 45:
            # SolidityInvariant.g:1:284: BARBAR
            pass 
            self.mBARBAR()



        elif alt9 == 46:
            # SolidityInvariant.g:1:291: LT
            pass 
            self.mLT()



        elif alt9 == 47:
            # SolidityInvariant.g:1:294: GT
            pass 
            self.mGT()



        elif alt9 == 48:
            # SolidityInvariant.g:1:297: BANG
            pass 
            self.mBANG()



        elif alt9 == 49:
            # SolidityInvariant.g:1:302: TILDE
            pass 
            self.mTILDE()



        elif alt9 == 50:
            # SolidityInvariant.g:1:308: QUES
            pass 
            self.mQUES()



        elif alt9 == 51:
            # SolidityInvariant.g:1:313: COLON
            pass 
            self.mCOLON()



        elif alt9 == 52:
            # SolidityInvariant.g:1:319: PLUS
            pass 
            self.mPLUS()



        elif alt9 == 53:
            # SolidityInvariant.g:1:324: SUB
            pass 
            self.mSUB()



        elif alt9 == 54:
            # SolidityInvariant.g:1:328: STAR
            pass 
            self.mSTAR()



        elif alt9 == 55:
            # SolidityInvariant.g:1:333: SLASH
            pass 
            self.mSLASH()



        elif alt9 == 56:
            # SolidityInvariant.g:1:339: AMP
            pass 
            self.mAMP()



        elif alt9 == 57:
            # SolidityInvariant.g:1:343: BAR
            pass 
            self.mBAR()



        elif alt9 == 58:
            # SolidityInvariant.g:1:347: CARET
            pass 
            self.mCARET()



        elif alt9 == 59:
            # SolidityInvariant.g:1:353: PERCENT
            pass 
            self.mPERCENT()



        elif alt9 == 60:
            # SolidityInvariant.g:1:361: IDENTIFIER
            pass 
            self.mIDENTIFIER()








    # lookup tables for DFA #9

    DFA9_eot = DFA.unpack(
        u"\1\uffff\1\51\1\53\1\uffff\4\46\1\uffff\1\46\2\uffff\1\73\4\46"
        u"\11\uffff\1\102\1\105\1\107\1\111\11\uffff\1\114\2\uffff\1\116"
        u"\6\uffff\5\46\1\124\3\46\2\uffff\5\46\12\uffff\1\136\3\uffff\4"
        u"\46\1\143\1\uffff\4\46\1\151\3\46\2\uffff\2\46\1\157\1\46\1\uffff"
        u"\1\161\1\162\3\46\1\uffff\2\46\1\170\1\46\1\172\1\uffff\1\173\2"
        u"\uffff\1\161\3\46\1\177\1\uffff\1\46\2\uffff\1\46\1\u0082\1\u0083"
        u"\1\uffff\1\u0084\1\u0085\4\uffff"
        )

    DFA9_eof = DFA.unpack(
        u"\u0086\uffff"
        )

    DFA9_min = DFA.unpack(
        u"\1\11\1\74\1\75\1\145\1\144\1\154\1\163\1\150\1\uffff\1\141\2\uffff"
        u"\1\57\1\151\1\156\1\164\1\165\11\uffff\2\75\1\46\1\174\11\uffff"
        u"\1\41\2\uffff\1\76\6\uffff\1\144\2\157\1\164\1\147\1\60\1\165\1"
        u"\151\1\154\2\uffff\1\156\1\164\1\162\1\160\1\154\12\uffff\1\76"
        u"\3\uffff\1\162\1\143\1\154\1\145\1\60\1\uffff\1\145\2\163\1\164"
        u"\1\60\1\151\1\145\1\154\2\uffff\1\145\1\153\1\60\1\163\1\uffff"
        u"\2\60\1\145\1\62\1\65\1\uffff\1\156\1\162\1\60\1\163\1\60\1\uffff"
        u"\1\60\2\uffff\1\60\1\65\1\66\1\147\1\60\1\uffff\1\163\2\uffff\1"
        u"\66\2\60\1\uffff\2\60\4\uffff"
        )

    DFA9_max = DFA.unpack(
        u"\1\176\2\75\1\162\1\144\1\171\1\163\1\170\1\uffff\1\141\2\uffff"
        u"\1\57\1\151\1\156\2\165\11\uffff\1\75\1\76\1\46\1\174\11\uffff"
        u"\1\75\2\uffff\1\76\6\uffff\1\144\2\157\1\164\1\147\1\172\1\165"
        u"\1\151\1\154\2\uffff\1\156\1\164\1\162\1\160\1\154\12\uffff\1\76"
        u"\3\uffff\1\162\1\143\1\154\1\145\1\172\1\uffff\1\145\2\163\1\164"
        u"\1\172\1\151\1\145\1\154\2\uffff\1\145\1\153\1\172\1\163\1\uffff"
        u"\2\172\1\145\1\62\1\65\1\uffff\1\156\1\162\1\172\1\163\1\172\1"
        u"\uffff\1\172\2\uffff\1\172\1\65\1\66\1\147\1\172\1\uffff\1\163"
        u"\2\uffff\1\66\2\172\1\uffff\2\172\4\uffff"
        )

    DFA9_accept = DFA.unpack(
        u"\10\uffff\1\16\1\uffff\1\20\1\21\5\uffff\1\34\1\35\1\36\1\37\1"
        u"\40\1\41\1\42\1\43\1\44\4\uffff\1\61\1\62\1\63\1\64\1\65\1\66\1"
        u"\72\1\73\1\74\1\uffff\1\52\1\56\1\uffff\1\45\1\5\1\6\1\7\1\10\1"
        u"\11\11\uffff\1\22\1\67\5\uffff\1\47\1\60\1\51\1\53\1\57\1\54\1"
        u"\70\1\55\1\71\1\1\1\uffff\1\50\1\4\1\46\5\uffff\1\15\10\uffff\1"
        u"\3\1\2\4\uffff\1\14\5\uffff\1\24\5\uffff\1\26\1\uffff\1\17\1\31"
        u"\5\uffff\1\32\1\uffff\1\13\1\30\3\uffff\1\33\2\uffff\1\25\1\27"
        u"\1\12\1\23"
        )

    DFA9_special = DFA.unpack(
        u"\u0086\uffff"
        )


    DFA9_transition = [
        DFA.unpack(u"\2\13\1\uffff\2\13\22\uffff\1\13\1\32\1\12\2\uffff\1"
        u"\45\1\34\1\uffff\1\21\1\22\1\43\1\41\1\30\1\42\1\31\1\14\12\10"
        u"\1\40\1\27\1\1\1\2\1\33\1\37\1\uffff\32\46\1\25\1\3\1\26\1\44\1"
        u"\46\1\uffff\1\4\1\5\3\46\1\11\2\46\1\16\3\46\1\6\1\20\4\46\1\17"
        u"\1\7\1\15\5\46\1\23\1\35\1\24\1\36"),
        DFA.unpack(u"\1\50\1\47"),
        DFA.unpack(u"\1\52"),
        DFA.unpack(u"\1\54\1\55\10\uffff\1\56\1\57\1\uffff\1\60"),
        DFA.unpack(u"\1\61"),
        DFA.unpack(u"\1\62\2\uffff\1\63\11\uffff\1\64"),
        DFA.unpack(u"\1\65"),
        DFA.unpack(u"\1\70\11\uffff\1\67\5\uffff\1\66"),
        DFA.unpack(u""),
        DFA.unpack(u"\1\71"),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u"\1\72"),
        DFA.unpack(u"\1\74"),
        DFA.unpack(u"\1\75"),
        DFA.unpack(u"\1\76\1\77"),
        DFA.unpack(u"\1\100"),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u"\1\101"),
        DFA.unpack(u"\1\103\1\104"),
        DFA.unpack(u"\1\106"),
        DFA.unpack(u"\1\110"),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u"\1\112\33\uffff\1\113"),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u"\1\115"),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u"\1\117"),
        DFA.unpack(u"\1\120"),
        DFA.unpack(u"\1\121"),
        DFA.unpack(u"\1\122"),
        DFA.unpack(u"\1\123"),
        DFA.unpack(u"\12\46\7\uffff\32\46\4\uffff\1\46\1\uffff\32\46"),
        DFA.unpack(u"\1\125"),
        DFA.unpack(u"\1\126"),
        DFA.unpack(u"\1\127"),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u"\1\130"),
        DFA.unpack(u"\1\131"),
        DFA.unpack(u"\1\132"),
        DFA.unpack(u"\1\133"),
        DFA.unpack(u"\1\134"),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u"\1\135"),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u"\1\137"),
        DFA.unpack(u"\1\140"),
        DFA.unpack(u"\1\141"),
        DFA.unpack(u"\1\142"),
        DFA.unpack(u"\12\46\7\uffff\32\46\4\uffff\1\46\1\uffff\32\46"),
        DFA.unpack(u""),
        DFA.unpack(u"\1\144"),
        DFA.unpack(u"\1\145"),
        DFA.unpack(u"\1\146"),
        DFA.unpack(u"\1\147"),
        DFA.unpack(u"\2\46\1\150\7\46\7\uffff\32\46\4\uffff\1\46\1\uffff"
        u"\32\46"),
        DFA.unpack(u"\1\152"),
        DFA.unpack(u"\1\153"),
        DFA.unpack(u"\1\154"),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u"\1\155"),
        DFA.unpack(u"\1\156"),
        DFA.unpack(u"\12\46\7\uffff\32\46\4\uffff\1\46\1\uffff\32\46"),
        DFA.unpack(u"\1\160"),
        DFA.unpack(u""),
        DFA.unpack(u"\12\46\7\uffff\32\46\4\uffff\1\46\1\uffff\32\46"),
        DFA.unpack(u"\12\46\7\uffff\32\46\4\uffff\1\46\1\uffff\32\46"),
        DFA.unpack(u"\1\163"),
        DFA.unpack(u"\1\164"),
        DFA.unpack(u"\1\165"),
        DFA.unpack(u""),
        DFA.unpack(u"\1\166"),
        DFA.unpack(u"\1\167"),
        DFA.unpack(u"\12\46\7\uffff\32\46\4\uffff\1\46\1\uffff\32\46"),
        DFA.unpack(u"\1\171"),
        DFA.unpack(u"\12\46\7\uffff\32\46\4\uffff\1\46\1\uffff\32\46"),
        DFA.unpack(u""),
        DFA.unpack(u"\12\46\7\uffff\32\46\4\uffff\1\46\1\uffff\32\46"),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u"\12\46\7\uffff\32\46\4\uffff\1\46\1\uffff\32\46"),
        DFA.unpack(u"\1\174"),
        DFA.unpack(u"\1\175"),
        DFA.unpack(u"\1\176"),
        DFA.unpack(u"\12\46\7\uffff\32\46\4\uffff\1\46\1\uffff\32\46"),
        DFA.unpack(u""),
        DFA.unpack(u"\1\u0080"),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u"\1\u0081"),
        DFA.unpack(u"\12\46\7\uffff\32\46\4\uffff\1\46\1\uffff\32\46"),
        DFA.unpack(u"\12\46\7\uffff\32\46\4\uffff\1\46\1\uffff\32\46"),
        DFA.unpack(u""),
        DFA.unpack(u"\12\46\7\uffff\32\46\4\uffff\1\46\1\uffff\32\46"),
        DFA.unpack(u"\12\46\7\uffff\32\46\4\uffff\1\46\1\uffff\32\46"),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u"")
    ]

    # class definition for DFA #9

    class DFA9(DFA):
        pass


 



def main(argv, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr):
    from antlr3.main import LexerMain
    main = LexerMain(SolidityInvariantLexer)

    main.stdin = stdin
    main.stdout = stdout
    main.stderr = stderr
    main.execute(argv)



if __name__ == '__main__':
    main(sys.argv)
