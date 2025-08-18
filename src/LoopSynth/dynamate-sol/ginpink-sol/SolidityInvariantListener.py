# Generated from SolidityInvariant.g by ANTLR 4.9.3
from antlr4 import *
if __name__ is not None and "." in __name__:
    from .SolidityInvariantParser import SolidityInvariantParser
else:
    from SolidityInvariantParser import SolidityInvariantParser

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


# This class defines a complete listener for a parse tree produced by SolidityInvariantParser.
class SolidityInvariantListener(ParseTreeListener):

    # Enter a parse tree produced by SolidityInvariantParser#solidityInvariant.
    def enterSolidityInvariant(self, ctx:SolidityInvariantParser.SolidityInvariantContext):
        pass

    # Exit a parse tree produced by SolidityInvariantParser#solidityInvariant.
    def exitSolidityInvariant(self, ctx:SolidityInvariantParser.SolidityInvariantContext):
        pass


    # Enter a parse tree produced by SolidityInvariantParser#expression.
    def enterExpression(self, ctx:SolidityInvariantParser.ExpressionContext):
        pass

    # Exit a parse tree produced by SolidityInvariantParser#expression.
    def exitExpression(self, ctx:SolidityInvariantParser.ExpressionContext):
        pass


    # Enter a parse tree produced by SolidityInvariantParser#conditionalExpression.
    def enterConditionalExpression(self, ctx:SolidityInvariantParser.ConditionalExpressionContext):
        pass

    # Exit a parse tree produced by SolidityInvariantParser#conditionalExpression.
    def exitConditionalExpression(self, ctx:SolidityInvariantParser.ConditionalExpressionContext):
        pass


    # Enter a parse tree produced by SolidityInvariantParser#equivalenceExpression.
    def enterEquivalenceExpression(self, ctx:SolidityInvariantParser.EquivalenceExpressionContext):
        pass

    # Exit a parse tree produced by SolidityInvariantParser#equivalenceExpression.
    def exitEquivalenceExpression(self, ctx:SolidityInvariantParser.EquivalenceExpressionContext):
        pass


    # Enter a parse tree produced by SolidityInvariantParser#equivalenceOp.
    def enterEquivalenceOp(self, ctx:SolidityInvariantParser.EquivalenceOpContext):
        pass

    # Exit a parse tree produced by SolidityInvariantParser#equivalenceOp.
    def exitEquivalenceOp(self, ctx:SolidityInvariantParser.EquivalenceOpContext):
        pass


    # Enter a parse tree produced by SolidityInvariantParser#impliesExpression.
    def enterImpliesExpression(self, ctx:SolidityInvariantParser.ImpliesExpressionContext):
        pass

    # Exit a parse tree produced by SolidityInvariantParser#impliesExpression.
    def exitImpliesExpression(self, ctx:SolidityInvariantParser.ImpliesExpressionContext):
        pass


    # Enter a parse tree produced by SolidityInvariantParser#impliesNonBackwardExpression.
    def enterImpliesNonBackwardExpression(self, ctx:SolidityInvariantParser.ImpliesNonBackwardExpressionContext):
        pass

    # Exit a parse tree produced by SolidityInvariantParser#impliesNonBackwardExpression.
    def exitImpliesNonBackwardExpression(self, ctx:SolidityInvariantParser.ImpliesNonBackwardExpressionContext):
        pass


    # Enter a parse tree produced by SolidityInvariantParser#logicalOrExpression.
    def enterLogicalOrExpression(self, ctx:SolidityInvariantParser.LogicalOrExpressionContext):
        pass

    # Exit a parse tree produced by SolidityInvariantParser#logicalOrExpression.
    def exitLogicalOrExpression(self, ctx:SolidityInvariantParser.LogicalOrExpressionContext):
        pass


    # Enter a parse tree produced by SolidityInvariantParser#logicalAndExpression.
    def enterLogicalAndExpression(self, ctx:SolidityInvariantParser.LogicalAndExpressionContext):
        pass

    # Exit a parse tree produced by SolidityInvariantParser#logicalAndExpression.
    def exitLogicalAndExpression(self, ctx:SolidityInvariantParser.LogicalAndExpressionContext):
        pass


    # Enter a parse tree produced by SolidityInvariantParser#equalityExpression.
    def enterEqualityExpression(self, ctx:SolidityInvariantParser.EqualityExpressionContext):
        pass

    # Exit a parse tree produced by SolidityInvariantParser#equalityExpression.
    def exitEqualityExpression(self, ctx:SolidityInvariantParser.EqualityExpressionContext):
        pass


    # Enter a parse tree produced by SolidityInvariantParser#relationalExpression.
    def enterRelationalExpression(self, ctx:SolidityInvariantParser.RelationalExpressionContext):
        pass

    # Exit a parse tree produced by SolidityInvariantParser#relationalExpression.
    def exitRelationalExpression(self, ctx:SolidityInvariantParser.RelationalExpressionContext):
        pass


    # Enter a parse tree produced by SolidityInvariantParser#shiftExpression.
    def enterShiftExpression(self, ctx:SolidityInvariantParser.ShiftExpressionContext):
        pass

    # Exit a parse tree produced by SolidityInvariantParser#shiftExpression.
    def exitShiftExpression(self, ctx:SolidityInvariantParser.ShiftExpressionContext):
        pass


    # Enter a parse tree produced by SolidityInvariantParser#additiveExpression.
    def enterAdditiveExpression(self, ctx:SolidityInvariantParser.AdditiveExpressionContext):
        pass

    # Exit a parse tree produced by SolidityInvariantParser#additiveExpression.
    def exitAdditiveExpression(self, ctx:SolidityInvariantParser.AdditiveExpressionContext):
        pass


    # Enter a parse tree produced by SolidityInvariantParser#multiplicativeExpression.
    def enterMultiplicativeExpression(self, ctx:SolidityInvariantParser.MultiplicativeExpressionContext):
        pass

    # Exit a parse tree produced by SolidityInvariantParser#multiplicativeExpression.
    def exitMultiplicativeExpression(self, ctx:SolidityInvariantParser.MultiplicativeExpressionContext):
        pass


    # Enter a parse tree produced by SolidityInvariantParser#bitwiseOrExpression.
    def enterBitwiseOrExpression(self, ctx:SolidityInvariantParser.BitwiseOrExpressionContext):
        pass

    # Exit a parse tree produced by SolidityInvariantParser#bitwiseOrExpression.
    def exitBitwiseOrExpression(self, ctx:SolidityInvariantParser.BitwiseOrExpressionContext):
        pass


    # Enter a parse tree produced by SolidityInvariantParser#bitwiseXorExpression.
    def enterBitwiseXorExpression(self, ctx:SolidityInvariantParser.BitwiseXorExpressionContext):
        pass

    # Exit a parse tree produced by SolidityInvariantParser#bitwiseXorExpression.
    def exitBitwiseXorExpression(self, ctx:SolidityInvariantParser.BitwiseXorExpressionContext):
        pass


    # Enter a parse tree produced by SolidityInvariantParser#bitwiseAndExpression.
    def enterBitwiseAndExpression(self, ctx:SolidityInvariantParser.BitwiseAndExpressionContext):
        pass

    # Exit a parse tree produced by SolidityInvariantParser#bitwiseAndExpression.
    def exitBitwiseAndExpression(self, ctx:SolidityInvariantParser.BitwiseAndExpressionContext):
        pass


    # Enter a parse tree produced by SolidityInvariantParser#unaryExpression.
    def enterUnaryExpression(self, ctx:SolidityInvariantParser.UnaryExpressionContext):
        pass

    # Exit a parse tree produced by SolidityInvariantParser#unaryExpression.
    def exitUnaryExpression(self, ctx:SolidityInvariantParser.UnaryExpressionContext):
        pass


    # Enter a parse tree produced by SolidityInvariantParser#unaryPrimary.
    def enterUnaryPrimary(self, ctx:SolidityInvariantParser.UnaryPrimaryContext):
        pass

    # Exit a parse tree produced by SolidityInvariantParser#unaryPrimary.
    def exitUnaryPrimary(self, ctx:SolidityInvariantParser.UnaryPrimaryContext):
        pass


    # Enter a parse tree produced by SolidityInvariantParser#literal.
    def enterLiteral(self, ctx:SolidityInvariantParser.LiteralContext):
        pass

    # Exit a parse tree produced by SolidityInvariantParser#literal.
    def exitLiteral(self, ctx:SolidityInvariantParser.LiteralContext):
        pass


    # Enter a parse tree produced by SolidityInvariantParser#parExpression.
    def enterParExpression(self, ctx:SolidityInvariantParser.ParExpressionContext):
        pass

    # Exit a parse tree produced by SolidityInvariantParser#parExpression.
    def exitParExpression(self, ctx:SolidityInvariantParser.ParExpressionContext):
        pass


    # Enter a parse tree produced by SolidityInvariantParser#identifierSuffix.
    def enterIdentifierSuffix(self, ctx:SolidityInvariantParser.IdentifierSuffixContext):
        pass

    # Exit a parse tree produced by SolidityInvariantParser#identifierSuffix.
    def exitIdentifierSuffix(self, ctx:SolidityInvariantParser.IdentifierSuffixContext):
        pass


    # Enter a parse tree produced by SolidityInvariantParser#argList.
    def enterArgList(self, ctx:SolidityInvariantParser.ArgListContext):
        pass

    # Exit a parse tree produced by SolidityInvariantParser#argList.
    def exitArgList(self, ctx:SolidityInvariantParser.ArgListContext):
        pass


    # Enter a parse tree produced by SolidityInvariantParser#argListRest.
    def enterArgListRest(self, ctx:SolidityInvariantParser.ArgListRestContext):
        pass

    # Exit a parse tree produced by SolidityInvariantParser#argListRest.
    def exitArgListRest(self, ctx:SolidityInvariantParser.ArgListRestContext):
        pass


    # Enter a parse tree produced by SolidityInvariantParser#jmlPrimary.
    def enterJmlPrimary(self, ctx:SolidityInvariantParser.JmlPrimaryContext):
        pass

    # Exit a parse tree produced by SolidityInvariantParser#jmlPrimary.
    def exitJmlPrimary(self, ctx:SolidityInvariantParser.JmlPrimaryContext):
        pass


    # Enter a parse tree produced by SolidityInvariantParser#resultExpression.
    def enterResultExpression(self, ctx:SolidityInvariantParser.ResultExpressionContext):
        pass

    # Exit a parse tree produced by SolidityInvariantParser#resultExpression.
    def exitResultExpression(self, ctx:SolidityInvariantParser.ResultExpressionContext):
        pass


    # Enter a parse tree produced by SolidityInvariantParser#oldExpression.
    def enterOldExpression(self, ctx:SolidityInvariantParser.OldExpressionContext):
        pass

    # Exit a parse tree produced by SolidityInvariantParser#oldExpression.
    def exitOldExpression(self, ctx:SolidityInvariantParser.OldExpressionContext):
        pass


    # Enter a parse tree produced by SolidityInvariantParser#oldId.
    def enterOldId(self, ctx:SolidityInvariantParser.OldIdContext):
        pass

    # Exit a parse tree produced by SolidityInvariantParser#oldId.
    def exitOldId(self, ctx:SolidityInvariantParser.OldIdContext):
        pass


    # Enter a parse tree produced by SolidityInvariantParser#specQuantifiedExpression.
    def enterSpecQuantifiedExpression(self, ctx:SolidityInvariantParser.SpecQuantifiedExpressionContext):
        pass

    # Exit a parse tree produced by SolidityInvariantParser#specQuantifiedExpression.
    def exitSpecQuantifiedExpression(self, ctx:SolidityInvariantParser.SpecQuantifiedExpressionContext):
        pass


    # Enter a parse tree produced by SolidityInvariantParser#type.
    def enterType(self, ctx:SolidityInvariantParser.TypeContext):
        pass

    # Exit a parse tree produced by SolidityInvariantParser#type.
    def exitType(self, ctx:SolidityInvariantParser.TypeContext):
        pass



del SolidityInvariantParser