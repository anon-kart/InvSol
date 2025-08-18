import sys
from antlr4 import *
from SolidityLexer import SolidityLexer
from SolidityParser import SolidityParser
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
        if len(sels) == 1:
            return first
        else:
            return selsCombine(first, sels[1:])

class SolidityFormulasParser(Parser):
    grammarFileName = "SolidityFormulas.g"
    api_version = 1

    def __init__(self, input, state=None, *args, **kwargs):
        if state is None:
            state = RecognizerSharedState()
        super().__init__(input, state, *args, **kwargs)
        self._state.ruleMemo = {}

    def solidity_formula(self):
        result = None
        try:
            expression1 = self.expression()
            self.match(self.input, SolidityParser.SEMI)
            result = expression1
        except RecognitionException as re:
            self.recover(self.input, re)
        return result

    def expression(self):
        result = None
        try:
            result = self.conditionalExpression()
        except RecognitionException as re:
            self.recover(self.input, re)
        return result

    def conditionalExpression(self):
        result = None
        try:
            cnd = self.equivalenceExpression()
            if self.input.LA(1) == SolidityParser.QUES:
                self.match(self.input, SolidityParser.QUES)
                th = self.expression()
                self.match(self.input, SolidityParser.COLON)
                el = self.conditionalExpression()
                result = ConditionalExpression(cnd, th, el)
            else:
                result = cnd
        except RecognitionException as re:
            self.recover(self.input, re)
        return result

    def equivalenceExpression(self):
        result = None
        try:
            l = self.impliesExpression()
            if self.input.LA(1) in [SolidityParser.EQUIVALENT, SolidityParser.NOT_EQUIVALENT]:
                op = self.equivalenceOp()
                r = self.impliesExpression()
                op.left = l
                op.right = r
                result = op
            else:
                result = l
        except RecognitionException as re:
            self.recover(self.input, re)
        return result

    def equivalenceOp(self):
        result = None
        try:
            if self.input.LA(1) == SolidityParser.EQUIVALENT:
                self.match(self.input, SolidityParser.EQUIVALENT)
                result = IffExpression()
            elif self.input.LA(1) == SolidityParser.NOT_EQUIVALENT:
                self.match(self.input, SolidityParser.NOT_EQUIVALENT)
                result = NIffExpression()
        except RecognitionException as re:
            self.recover(self.input, re)
        return result
    
    def conditionalOrExpression(self):
        result = None
        try:
            ant = self.conditionalAndExpression()
            l_props = []

            while self.input.LA(1) == SolidityParser.BARBAR:  # token for '||'
                self.match(self.input, SolidityParser.BARBAR)
                ie = self.conditionalAndExpression()
                l_props.append(ie)

            if len(l_props) == 0:
                result = ant
            else:
                result = OrExpression()
                result.aggregate([ant] + l_props)

        except RecognitionException as re:
            self.recover(self.input, re)

        return result

    def conditionalAndExpression(self):
        result = None
        try:
            ant = self.inclusiveOrExpression()  # This must already be implemented
            l_props = []

            while self.input.LA(1) == SolidityParser.AMPAMP:  # token for '&&'
                self.match(self.input, SolidityParser.AMPAMP)
                ie = self.inclusiveOrExpression()
                l_props.append(ie)

            if len(l_props) == 0:
                result = ant
            else:
                result = AndExpression()
                result.aggregate([ant] + l_props)

        except RecognitionException as re:
            self.recover(self.input, re)

        return result

    def exclusiveOrExpression(self):
        result = None
        try:
            ant = self.andExpression()  # This method must exist in your parser
            l_props = []

            while self.input.LA(1) == SolidityParser.CARET:  # Token for '^'
                self.match(self.input, SolidityParser.CARET)
                ie = self.andExpression()
                l_props.append(ie)

            if len(l_props) == 0:
                result = ant
            else:
                result = BitwiseXorExpression()
                result.aggregate([ant] + l_props)

        except RecognitionException as re:
            self.recover(self.input, re)

        return result

    def inclusiveOrExpression(self):
        result = None
        try:
            ant = self.exclusiveOrExpression()
            l_props = []

            while self.input.LA(1) == SolidityParser.BAR:  # Token for '|'
                self.match(self.input, SolidityParser.BAR)
                ie = self.exclusiveOrExpression()
                l_props.append(ie)

            if len(l_props) == 0:
                result = ant
            else:
                result = BitwiseOrExpression()
                result.aggregate([ant] + l_props)

        except RecognitionException as re:
            self.recover(self.input, re)

        return result


    def andExpression(self):
        result = None
        try:
            ant = self.equalityExpression()
            l_props = []

            while self.input.LA(1) == SolidityParser.AMP:  # Token for '&'
                self.match(self.input, SolidityParser.AMP)
                ie = self.equalityExpression()
                l_props.append(ie)

            if len(l_props) == 0:
                result = ant
            else:
                result = BitwiseAndExpression()
                result.aggregate([ant] + l_props)

        except RecognitionException as re:
            self.recover(self.input, re)

        return result
    
    def equalityExpression(self):
        result = None
        try:
            ant = self.instanceOfExpression()
            l_props = []

            while self.input.LA(1) in [SolidityParser.EQEQ, SolidityParser.BANGEQ]:
                op_token = self.input.LA(1)
                if op_token == SolidityParser.EQEQ:
                    self.match(self.input, SolidityParser.EQEQ)
                    op = EqualsExpression()
                elif op_token == SolidityParser.BANGEQ:
                    self.match(self.input, SolidityParser.BANGEQ)
                    op = NEqualsExpression()

                ie = self.instanceOfExpression()
                l_props.append((op, ie))

            if len(l_props) == 0:
                result = ant
            else:
                dum = BinaryExpression()
                result = dum.mix_aggregate([ant] + l_props)

        except RecognitionException as re:
            self.recover(self.input, re)

        return result
    
    def instanceOfExpression(self):
        result = None
        try:
            result = self.relationalExpression()
        except RecognitionException as re:
            self.recover(self.input, re)
        return result
    
    def relationalOp(self):
        result = None
        try:
            la = self.input.LA(1)
            if la == SolidityParser.LT:
                self.match(self.input, SolidityParser.LT)
                result = LessThanExpression()
            elif la == SolidityParser.GT:
                self.match(self.input, SolidityParser.GT)
                result = GreaterThanExpression()
            elif la == SolidityParser.LE:  # Assuming LE token for '<='
                self.match(self.input, SolidityParser.LE)
                result = LessThanOrEqualExpression()
            elif la == SolidityParser.GE:  # Assuming GE token for '>='
                self.match(self.input, SolidityParser.GE)
                result = GreaterThanOrEqualExpression()
        except RecognitionException as re:
            self.recover(self.input, re)
        return result

    def relationalExpression(self):
        result = None
        try:
            ant = self.shiftExpression()  # You can stub shiftExpression for now
            l_props = []

            while self.input.LA(1) in [
                SolidityParser.LT,
                SolidityParser.GT,
                SolidityParser.LE,
                SolidityParser.GE
            ]:
                op = self.relationalOp()
                ie = self.shiftExpression()
                l_props.append((op, ie))

            if len(l_props) == 0:
                result = ant
            else:
                result = BinaryExpression().mix_aggregate([ant] + l_props)

        except RecognitionException as re:
            self.recover(self.input, re)
        return result

    def relationalOp(self):
        result = None
        try:
            la = self.input.LA(1)
            if la == SolidityParser.LE:  # '<='
                self.match(self.input, SolidityParser.LE)
                result = LessThanOrEqualExpression()
            elif la == SolidityParser.GE:  # '>='
                self.match(self.input, SolidityParser.GE)
                result = GreaterThanOrEqualExpression()
            elif la == SolidityParser.LT:
                self.match(self.input, SolidityParser.LT)
                result = LessThanExpression()
            elif la == SolidityParser.GT:
                self.match(self.input, SolidityParser.GT)
                result = GreaterThanExpression()
        except RecognitionException as re:
            self.recover(self.input, re)
        return result

    def shiftExpression(self):
        result = None
        try:
            result = self.additiveExpression()
        except RecognitionException as re:
            self.recover(self.input, re)
        return result

    def additiveExpression(self):
        result = None
        try:
            ant = self.multiplicativeExpression()
            l_props = []

            while self.input.LA(1) in [SolidityParser.PLUS, SolidityParser.SUB]:
                op_token = self.input.LA(1)

                if op_token == SolidityParser.PLUS:
                    self.match(self.input, SolidityParser.PLUS)
                    op = AddExpression()
                elif op_token == SolidityParser.SUB:
                    self.match(self.input, SolidityParser.SUB)
                    op = SubExpression()

                ie = self.multiplicativeExpression()
                l_props.append((op, ie))

            if len(l_props) == 0:
                result = ant
            else:
                result = BinaryExpression().mix_aggregate([ant] + l_props)

        except RecognitionException as re:
            self.recover(self.input, re)

        return result
    
    def multiplicativeExpression(self):
        result = None
        try:
            ant = self.unaryExpression()
            l_props = []

            while self.input.LA(1) in [
                SolidityParser.STAR,
                SolidityParser.SLASH,
                SolidityParser.PERCENT
            ]:
                op_token = self.input.LA(1)
                if op_token == SolidityParser.STAR:
                    self.match(self.input, SolidityParser.STAR)
                    op = MultExpression()
                elif op_token == SolidityParser.SLASH:
                    self.match(self.input, SolidityParser.SLASH)
                    op = DivExpression()
                elif op_token == SolidityParser.PERCENT:
                    self.match(self.input, SolidityParser.PERCENT)
                    op = ModExpression()

                ie = self.unaryExpression()
                l_props.append((op, ie))

            if len(l_props) == 0:
                result = ant
            else:
                result = BinaryExpression().mix_aggregate([ant] + l_props)

        except RecognitionException as re:
            self.recover(self.input, re)

        return result

    def unaryExpression(self):
        result = None
        try:
            if self.input.LA(1) == SolidityParser.PLUS:
                self.match(self.input, SolidityParser.PLUS)
                ex = self.unaryExpression()
                result = ex  # Unary plus just passes through
            elif self.input.LA(1) == SolidityParser.SUB:
                self.match(self.input, SolidityParser.SUB)
                ex = self.unaryExpression()
                result = MinusUnaryExpression()
                result.item = ex
            else:
                result = self.unaryExpressionNotPlusMinus()

        except RecognitionException as re:
            self.recover(self.input, re)

        return result

    def unaryExpressionNotPlusMinus(self):
        return self.primaryExpression()  # Or whatever rule is next in your chain


    def unaryExpressionNotPlusMinus(self):
        result = None
        try:
            if self.input.LA(1) == SolidityParser.TILDE:
                self.match(self.input, SolidityParser.TILDE)
                expr = self.unaryExpression()
                result = expr  # You can later wrap this in a BitwiseNotExpression if needed

            elif self.input.LA(1) == SolidityParser.BANG:
                self.match(self.input, SolidityParser.BANG)
                expr = self.unaryExpression()
                result = NotExpression()
                result.item = expr

            else:
                t = self.primary()
                l_ss = []

                while self.input.LA(1) in [SolidityParser.DOT, SolidityParser.LBRACKET]:
                    sel = self.selector()
                    l_ss.append(sel)

                result = selsCombine(t, l_ss)

        except RecognitionException as re:
            self.recover(self.input, re)

        return result
    
    def primary(self):
        # Dummy placeholder: in practice, you'd parse identifiers, literals, grouped expressions, etc.
        ident = self.match(self.input, SolidityParser.IDENTIFIER)
        return ident.text if ident else "unknown"

    def selector(self):
        if self.input.LA(1) == SolidityParser.DOT:
            self.match(self.input, SolidityParser.DOT)
            ident = self.match(self.input, SolidityParser.IDENTIFIER)
            return (ident.text, None)

        elif self.input.LA(1) == SolidityParser.LBRACKET:
            self.match(self.input, SolidityParser.LBRACKET)
            expr = self.expression()
            self.match(self.input, SolidityParser.RBRACKET)
            return [expr]

    def primary(self):
        result = None
        try:
            la = self.input.LA(1)

            if la == SolidityParser.LPAREN:
                self.match(self.input, SolidityParser.LPAREN)
                expr = self.expression()
                self.match(self.input, SolidityParser.RPAREN)
                result = ParenExpression(expr)

            elif la == SolidityParser.THIS:
                self.match(self.input, SolidityParser.THIS)
                target = Identifier("this")
                idlist = []
                suffix = None

                while self.input.LA(1) == SolidityParser.DOT:
                    self.match(self.input, SolidityParser.DOT)
                    ident = self.match(self.input, SolidityParser.IDENTIFIER)
                    idlist.append(Identifier(ident.text))

                if self.input.LA(1) in [SolidityParser.LPAREN, SolidityParser.LBRACKET]:
                    suffix = self.identifierSuffix()

                result = primaryCombine(target, idlist, suffix)

            elif la == SolidityParser.IDENTIFIER:
                ident = self.match(self.input, SolidityParser.IDENTIFIER)
                target = Identifier(ident.text)
                idlist = []

                while self.input.LA(1) == SolidityParser.DOT:
                    self.match(self.input, SolidityParser.DOT)
                    ident = self.match(self.input, SolidityParser.IDENTIFIER)
                    idlist.append(Identifier(ident.text))

                suffix = None
                if self.input.LA(1) in [SolidityParser.LPAREN, SolidityParser.LBRACKET]:
                    suffix = self.identifierSuffix()

                result = primaryCombine(target, idlist, suffix)

            elif la == SolidityParser.SUPER:
                self.match(self.input, SolidityParser.SUPER)
                result = Identifier("super")  # You may refine with suffix support

            elif la in [
                SolidityParser.INTLITERAL, SolidityParser.STRINGLITERAL,
                SolidityParser.TRUE, SolidityParser.FALSE
            ]:
                token = self.input.LT(1)
                self.consume()
                result = Literal(token.text)

        except RecognitionException as re:
            self.recover(self.input, re)

        return result

    def identifierSuffix(self):
        if self.input.LA(1) == SolidityParser.LPAREN:
            self.match(self.input, SolidityParser.LPAREN)
            args = []
            if self.input.LA(1) != SolidityParser.RPAREN:
                args.append(self.expression())
                while self.input.LA(1) == SolidityParser.COMMA:
                    self.match(self.input, SolidityParser.COMMA)
                    args.append(self.expression())
            self.match(self.input, SolidityParser.RPAREN)
            return ('(', args)

        elif self.input.LA(1) == SolidityParser.LBRACKET:
            self.match(self.input, SolidityParser.LBRACKET)
            idx = self.expression()
            self.match(self.input, SolidityParser.RBRACKET)
            return ('[', idx)

    def parExpression(self):
        self.match(self.input, SolidityParser.LPAREN)
        expr = self.expression()
        self.match(self.input, SolidityParser.RPAREN)
        return expr
    
    def identifierSuffix(self):
        if self.input.LA(1) == SolidityParser.LPAREN:
            self.match(self.input, SolidityParser.LPAREN)
            args = []
            if self.input.LA(1) != SolidityParser.RPAREN:
                args.append(self.expression())
                while self.input.LA(1) == SolidityParser.COMMA:
                    self.match(self.input, SolidityParser.COMMA)
                    args.append(self.expression())
            self.match(self.input, SolidityParser.RPAREN)
            return ('(', args)

        elif self.input.LA(1) == SolidityParser.LBRACKET:
            self.match(self.input, SolidityParser.LBRACKET)
            idx = self.expression()
            self.match(self.input, SolidityParser.RBRACKET)
            return ('[', idx)

    def parExpression(self):
        self.match(self.input, SolidityParser.LPAREN)
        expr = self.expression()
        self.match(self.input, SolidityParser.RPAREN)
        return ParenExpression(expr)

    def primary(self):
        result = None
        try:
            la = self.input.LA(1)

            if la == SolidityParser.LPAREN:
                result = self.parExpression()

            elif la == SolidityParser.THIS:
                self.match(self.input, SolidityParser.THIS)
                target = Identifier("this")
                idlist = []
                suffix = None

                while self.input.LA(1) == SolidityParser.DOT:
                    self.match(self.input, SolidityParser.DOT)
                    ident = self.match(self.input, SolidityParser.IDENTIFIER)
                    idlist.append(Identifier(ident.text))

                if self.input.LA(1) in [SolidityParser.LPAREN, SolidityParser.LBRACKET]:
                    suffix = self.identifierSuffix()

                result = primaryCombine(target, idlist, suffix)

            elif la == SolidityParser.IDENTIFIER:
                ident = self.match(self.input, SolidityParser.IDENTIFIER)
                target = Identifier(ident.text)
                idlist = []

                while self.input.LA(1) == SolidityParser.DOT:
                    self.match(self.input, SolidityParser.DOT)
                    ident = self.match(self.input, SolidityParser.IDENTIFIER)
                    idlist.append(Identifier(ident.text))

                suffix = None
                if self.input.LA(1) in [SolidityParser.LPAREN, SolidityParser.LBRACKET]:
                    suffix = self.identifierSuffix()

                result = primaryCombine(target, idlist, suffix)

            elif la == SolidityParser.SUPER:
                self.match(self.input, SolidityParser.SUPER)
                result = Identifier("super")

            elif la in [
                SolidityParser.INTLITERAL,
                SolidityParser.STRINGLITERAL,
                SolidityParser.TRUE,
                SolidityParser.FALSE
            ]:
                token = self.input.LT(1)
                self.consume()
                result = Literal(token.text)

        except RecognitionException as re:
            self.recover(self.input, re)

        return result

    def identifierSuffix(self):
        args = None
        try:
            la = self.input.LA(1)

            if la == SolidityParser.LBRACKET:
                l_args = []
                while self.input.LA(1) == SolidityParser.LBRACKET:
                    self.match(self.input, SolidityParser.LBRACKET)
                    ex = self.expression()
                    self.match(self.input, SolidityParser.RBRACKET)
                    l_args.append(ex)
                args = ('[', l_args)

            elif la == SolidityParser.LPAREN:
                args_list = self.arguments()
                args = ('(', args_list)

            # Skip .class, .this, .super – not relevant in Solidity

        except RecognitionException as re:
            self.recover(self.input, re)

        return args

    def createdName(self):
        result = None
        try:
            la = self.input.LA(1)
            if la == SolidityParser.IDENTIFIER:
                result = self.classOrInterfaceType()
            elif la in [
                SolidityParser.BOOL, SolidityParser.INT, SolidityParser.UINT,
                SolidityParser.BYTE, SolidityParser.ADDRESS, SolidityParser.STRING
            ]:
                result = self.primitiveType()
        except RecognitionException as re:
            self.recover(self.input, re)
        return result

    def classOrInterfaceType(self):
        result = None
        try:
            ident_token = self.match(self.input, SolidityParser.IDENTIFIER)
            result = ident_token.text
        except RecognitionException as re:
            self.recover(self.input, re)
        return result

    def primitiveType(self):
        result = None
        try:
            la = self.input.LA(1)
            if la == SolidityParser.BOOL:
                self.match(self.input, SolidityParser.BOOL)
                result = "bool"
            elif la == SolidityParser.ADDRESS:
                self.match(self.input, SolidityParser.ADDRESS)
                result = "address"
            elif la == SolidityParser.STRING:
                self.match(self.input, SolidityParser.STRING)
                result = "string"
            elif la == SolidityParser.BYTE:
                self.match(self.input, SolidityParser.BYTE)
                result = "byte"
            elif la == SolidityParser.INT:
                self.match(self.input, SolidityParser.INT)
                result = "int"
            elif la == SolidityParser.UINT:
                self.match(self.input, SolidityParser.UINT)
                result = "uint"
        except RecognitionException as re:
            self.recover(self.input, re)
        return result

    def resultExpression(self):
        result = ResultExpression()
        self.match(self.input, SolidityParser.RESULT)  # token 128
        return result

    def oldExpression(self):
        result = OldExpression()
        self.match(self.input, SolidityParser.OLD)  # tokens 126/127
        return result

    def jmlPrimary(self):
        result = None
        try:
            if self.input.LA(1) == SolidityParser.RESULT:
                self.match(self.input, SolidityParser.RESULT)
                result = ResultExpression()
            elif self.input.LA(1) in [SolidityParser.OLD1, SolidityParser.OLD2]:  # replace with actual tokens for \old
                self.match(self.input, self.input.LA(1))
                result = OldExpression()
            else:
                self.reportError("Unsupported JML construct in Solidity adaptation.")
        except RecognitionException as re:
            self.recover(self.input, re)
        return result

    # Add this at the end of your file (expression_parser.py)

    def parse_expr(expr_str):
        """
        Parses a Solidity expression string into an AST node using ANTLR.
        Equivalent to `parseString` in DynaMate's JML setup.
        """
        try:
            input_stream = InputStream(expr_str.strip())
            lexer = SolidityLexer(input_stream)
            stream = CommonTokenStream(lexer)
            parser = SolidityFormulasParser(stream)
            return parser.solidity_formula()
        except Exception as e:
            print(f"[parse_expr] Error parsing: {expr_str}\n{e}")
            return None


# incomplete....................
