grammar SolidityInvariant;

options {
    language=Python;
    output=AST;
    backtrack=true;
    memoize=true;
}

@header {
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
}

@rulecatch {
    except RecognitionException as re:
        self.recover(self.input, re)
}

solidityInvariant returns [result]
    :   expression ';'
        { $result = $expression.result; }
    ;

expression returns [result]
    :   conditionalExpression
        { $result = $conditionalExpression.result; }
    ;

conditionalExpression returns [result]
    :   cnd=equivalenceExpression
        ( '?' th=expression ':' el=conditionalExpression )?
        {
            if th is None:
                $result = $cnd.result
            else:
                $result = ConditionalExpression()
                $result.condition = $cnd.result
                $result.then_exp = $th.result
                $result.else_exp = $el.result
            }
    ;

equivalenceExpression returns [result]
    :   l=impliesExpression
        ( eqOp=equivalenceOp r=impliesExpression )?
        {
            if r is None:
                $result = $l.result
            else:
                $eqOp.result.left = $l.result
                $eqOp.result.right = $r.result
                $result = $eqOp.result
        }
    ;

equivalenceOp returns [result]
    :   '<==>'     { $result = IffExpression(); }
    |   '<=!=>'    { $result = NIffExpression(); }
    ;

impliesExpression returns [result]
    :   ant=logicalOrExpression
        {
            exprs = [$ant.result]
        }
        ('==>' ie=impliesNonBackwardExpression
            {
                exprs.append($ie.result)
            }
        )*
        {
            if len(exprs) == 1:
                $result = exprs[0]
            elif len(exprs) >= 2:
                $result = ImpliesExpression()
                $result.aggregate(exprs)
            else:
                raise Exception("Invalid impliesExpression: no expressions to aggregate")
        }
    |   left=logicalOrExpression
        {
            exprs = [$left.result]
        }
        ('<==' right=logicalOrExpression
            {
                exprs.append($right.result)
            }
        )*
        {
            // Optional: implement reverse implication logic
            $result = exprs[0]
        }
    ;

impliesNonBackwardExpression returns [result]
    :   ant=logicalOrExpression
        {
            exprs = [$ant.result]
        }
        ('==>' ie=impliesNonBackwardExpression
            {
                exprs.append($ie.result)
            }
        )*
        {
            if len(exprs) == 1:
                $result = exprs[0]
            elif len(exprs) >= 2:
                $result = ImpliesExpression()
                $result.aggregate(exprs)
            else:
                raise Exception("Invalid impliesNonBackwardExpression: no expressions to aggregate")
        }
    ;

logicalOrExpression returns [result]
    :   l=logicalAndExpression
        ( '||' r=logicalAndExpression )*
        {
            r_exprs = [r.result for r in r] if r is not None else []
            props = [$l.result] + r_exprs
            if len(props) == 1:
                $result = props[0]
            else:
                $result = OrExpression()
                $result.aggregate(props)
        }

    ;

logicalAndExpression returns [result]
    :   l=bitwiseOrExpression
        ( '&&' r=equalityExpression )*
        {
            r_exprs = [r.result for r in r] if r is not None else []
            props = [$l.result] + r_exprs
            if len(props) == 1:
                $result = props[0]
            else:
                $result = AndExpression()
                $result.aggregate(props)
        }

    ;

equalityExpression returns [result]
    :   l=relationalExpression
        {
            exprs = [$l.result]
            ops = []
        }
        (op=('==' | '!=') r=relationalExpression
            {
                ops.append(op.text)
                exprs.append(r.result)
            }
        )*
        {
            if not ops:
                $result = exprs[0]
            else:
                zipped = [(exprs[i], ops[i], exprs[i+1]) for i in range(len(ops))]
                $result = BinaryExpression()
                $result.aggregate(zipped)
            }
    ;

relationalExpression returns [result]
    :   l=shiftExpression
        {
            exprs = [$l.result]
            ops = []
        }
        (
            op=('<' | '<=' | '>' | '>=') r=shiftExpression
            {
                ops.append(op.text)
                exprs.append(r.result)
            }
        )*
        {
            if not ops:
                $result = exprs[0]
            else:
                zipped = [(exprs[i], ops[i], exprs[i+1]) for i in range(len(ops))]
                $result = BinaryExpression()
                $result.aggregate(zipped)
            }
    ;

shiftExpression returns [result]
    :   l=additiveExpression
        {
            exprs = [$l.result]
            ops = []
        }
        (
            op=('<<' | '>>') r=additiveExpression
            {
                ops.append(op.text)
                exprs.append(r.result)
            }
        )*
        {
            if len(ops) == 0:
                $result = exprs[0]
            else:
                zipped = [(exprs[i], ops[i], exprs[i+1]) for i in range(len(ops))]
                $result = BinaryExpression()
                $result.aggregate(zipped)
        }
    ;

additiveExpression returns [result]
    :   l=multiplicativeExpression
        {
            exprs = [$l.result]
            ops = []
        }
        (
            op=('+' | '-') r=multiplicativeExpression
            {
                ops.append(op.text)
                exprs.append(r.result)
            }
        )*
        {
            if len(ops) == 0:
                $result = exprs[0]
            else:
                zipped = [(exprs[i], ops[i], exprs[i+1]) for i in range(len(ops))]
                $result = BinaryExpression()
                $result.aggregate(zipped)
        }
    ;

multiplicativeExpression returns [result]
    :   l=unaryExpression
        {
            exprs = [$l.result]
            ops = []
        }
        (
            op=('*' | '/' | '%') r=unaryExpression
            {
                ops.append(op.text)
                exprs.append(r.result)
            }
        )*
        {
            if len(ops) == 0:
                $result = exprs[0]
            else:
                zipped = [(exprs[i], ops[i], exprs[i+1]) for i in range(len(ops))]
                $result = BinaryExpression()
                $result.aggregate(zipped)
        }
    ;


bitwiseOrExpression returns [result]
    :   l=bitwiseXorExpression
        {
            exprs = [$l.result]
            ops = []
        }
        (op='|' r=bitwiseXorExpression
            {
                ops.append(op.text)
                exprs.append(r.result)
            }
        )*
        {
            if len(ops) == 0:
                $result = exprs[0]
            else:
                zipped = [(exprs[i], ops[i], exprs[i+1]) for i in range(len(ops))]
                $result = BinaryExpression()
                $result.aggregate(zipped)
            }
    ;

bitwiseXorExpression returns [result]
    :   l=bitwiseAndExpression
        {
            exprs = [$l.result]
            ops = []
        }
        (op='^' r=bitwiseAndExpression
            {
                ops.append(op.text)
                exprs.append(r.result)
            }
        )*
        {
            if len(ops) == 0:
                $result = exprs[0]
            else:
                zipped = [(exprs[i], ops[i], exprs[i+1]) for i in range(len(ops))]
                $result = BinaryExpression()
                $result.aggregate(zipped)
            }
    ;

bitwiseAndExpression returns [result]
    :   l=equalityExpression
        {
            exprs = [$l.result]
            ops = []
        }
        (op='&' r=equalityExpression
            {
                ops.append(op.text)
                exprs.append(r.result)
            }
        )*
        {
            if len(ops) == 0:
                $result = exprs[0]
            else:
                zipped = [(exprs[i], ops[i], exprs[i+1]) for i in range(len(ops))]
                $result = BinaryExpression()
                $result.aggregate(zipped)
            }
    ;

unaryExpression returns [result]
    :   '+' u=unaryExpression
        { $result = $u.result; }
    |   '-' u=unaryExpression
        {
            $result = MinusUnaryExpression()
            $result.item = $u.result
        }
    |   '!' u=unaryExpression
        {
            $result = NotExpression()
            $result.item = $u.result
        }
    |   '~' u=unaryExpression
        {
            $result = BitwiseNotExpression()
            $result.item = $u.result
        }
    |   unaryPrimary
        { $result = $unaryPrimary.result; }
    ;

unaryPrimary returns [result]
    :   simpleIdentifier indexSuffix?
        {
            if $indexSuffix.result is None:
                $result = $simpleIdentifier.result;
            else:
                ref = ArrayReference()
                ref.target = $simpleIdentifier.result
                ref.args = [$indexSuffix.result]
                $result = ref
            }
    |   solidityGlobal
        { $result = $solidityGlobal.result; }
    |   complexReference
        { $result = $complexReference.result; }
    |   literal
        { $result = $literal.result; }
    |   parExpression
        { $result = $parExpression.result; }
    |   jmlPrimary
        { $result = $jmlPrimary.result; }
    ;

solidityGlobal returns [result]
    :   base=('msg' | 'block' | 'tx' | 'address' | 'this')
        ('.' attr=IDENTIFIER)+
        {
            root = Identifier()
            root.val = $base.text

            current = AttributeCall()
            current.target = root
            current.call = []

            for token in $attr:
                new_attr = Identifier()
                new_attr.val = token.text
                current = AttributeCall()
                current.target = current
                current.call = [new_attr]

            $result = current
        }
    ;


simpleIdentifier returns [result]
    :   IDENTIFIER
        {
            $result = Identifier()
            $result.val = $IDENTIFIER.text
        }
    ;

complexReference returns [result]
    :   t=IDENTIFIER
        {
            l_t = Identifier()
            l_t.val = $t.text
            l_ids = []
            l_suf = None
        }
        ('.' id=IDENTIFIER
            {
                l_id = Identifier()
                l_id.val = $id.text
                l_ids.append(l_id)
            }
        )+
        (sfx=identifierSuffix)?
        {
            if sfx is not None:
                l_suf = $sfx.args
            $result = primaryCombine(l_t, l_ids, l_suf)
        }
    ;    

literal returns [result]
    :   INTLIT
        {
            $result = IntLiteral()
            $result.val = int($INTLIT.text)
        }
    |   BOOLLIT
        {
            $result = BoolLiteral()
            $result.val = True if $BOOLLIT.text == 'true' else False
        }
    |   STRINGLIT
        {
            $result = StringLiteral()
            $result.val = $STRINGLIT.text.strip('"')
        }
    ;

parExpression returns [result]
    :   '(' expression ')'
        { $result = $expression.result; }
    ;

indexSuffix returns [result]
    :   '[' expression ']'
        { $result = $expression.result; }
    ;


identifierSuffix returns [args]
    :   '(' a=argList? ')'
        {
            if a is not None:
                $args = ('(', a)
            else:
                $args = ('(', [])
        }
    |   '[' expression ']'
        {
            $args = ('[', $expression.result)
        }
    ;

argList returns [args]
    :   first=expression restList=argListRest*
        {
            $args = [$first.result]
            for r in restList:
                $args.append(r)
        }
    ;

argListRest returns [value]
    :   ',' expr=expression
        {
            $value = $expr.result
        }
    ;

jmlPrimary returns [result]
    :   resultExpression
        { $result = $resultExpression.result; }
    |   oldExpression
        { $result = $oldExpression.result; }
    |   specQuantifiedExpression
        { $result = $specQuantifiedExpression.result; }
    ;

resultExpression returns [result]
    :   '\\result'
        {
            $result = ResultExpression()
        }
    ;

oldExpression returns [result]
    :   oldId '(' expression ')'
        {
            $result = OldExpression()
            $result.item = $expression.result
        }
    ;

oldId
    :   '\\old'
    |   '\\pre'
    ;

specQuantifiedExpression returns [result]
    :   '\\forall' IDENTIFIER ':' type ';' expression
        {
            $result = ForallExpression()
            $result.var = $IDENTIFIER.text
            $result.typ = $type.result
            $result.cond = $expression.result
        }
    |   '\\exists' IDENTIFIER ':' type ';' expression
        {
            $result = ExistsExpression()
            $result.var = $IDENTIFIER.text
            $result.typ = $type.result
            $result.cond = $expression.result
        }
    ;

type returns [result]
    :   UINT256     { $result = TypeLiteral('uint256'); }
    |   INT         { $result = TypeLiteral('int'); }
    |   INT256      { $result = TypeLiteral('int256'); }
    |   BOOL        { $result = TypeLiteral('bool'); }
    |   STRING      { $result = TypeLiteral('string'); }
    |   BYTES       { $result = TypeLiteral('bytes'); }
    ;

// -----------------------------
//         LEXER RULES
// -----------------------------

INTLIT
    :   ('0'..'9')+
    ;

BOOLLIT
    :   'true'
    |   'false'
    ;

STRINGLIT
    :   '"' ( EscapeSequence | ~('\\'|'"') )* '"'
    ;

fragment EscapeSequence
    :   '\\' (
            'b' | 't' | 'n' | 'f' | 'r' | '"' | '\'' | '\\'
          | ('0'..'3') ('0'..'7') ('0'..'7')
          | ('0'..'7') ('0'..'7')
          | ('0'..'7')
        )
    ;

WS
    :   (' ' | '\r' | '\t' | '\u000C' | '\n')
        { $channel = HIDDEN; }
    ;

LINE_COMMENT
    :   '//' ~('\n'|'\r')* ('\r'? '\n')?
        { $channel = HIDDEN; }
    ;

// -----------------------------
//         TOKEN TYPES
// -----------------------------

UINT256 : 'uint256';
INT     : 'int';
INT256  : 'int256';
BOOL    : 'bool';
STRING  : 'string';
BYTES   : 'bytes';

THIS        : 'this';
NULL        : 'null';
SUPER       : 'super';

LPAREN      : '(';
RPAREN      : ')';
LBRACE      : '{';
RBRACE      : '}';
LBRACKET    : '[';
RBRACKET    : ']';
SEMI        : ';';
COMMA       : ',';
DOT         : '.';
EQ          : '=';

EQEQ        : '==';
NOTEQ       : '!=';
LE          : '<=';
GE          : '>=';
LSHIFT      : '<<';
RSHIFT      : '>>';
AMPAMP      : '&&';
BARBAR      : '||';

LT          : '<';
GT          : '>';
BANG        : '!';
TILDE       : '~';
QUES        : '?';
COLON       : ':';

PLUS        : '+';
SUB         : '-';
STAR        : '*';
SLASH       : '/';
AMP         : '&';
BAR         : '|';
CARET       : '^';
PERCENT     : '%';

// Identifier definition
fragment IdentifierStart
    :   'a'..'z'
    |   'A'..'Z'
    |   '_'
    ;

fragment IdentifierPart
    :   IdentifierStart
    |   '0'..'9'
    ;

IDENTIFIER
    :   IdentifierStart IdentifierPart*
    ;

