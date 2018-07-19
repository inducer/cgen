from cgen import (
        POD, Struct, FunctionBody, FunctionDeclaration,
        For, If, Assign, Value, Block, ArrayOf, Comment,
        Template)
from cgen.preprocessor import Define
import numpy as np
import warnings
import pytest
import importlib


@pytest.mark.parametrize('cls', ['Generable',
                                 'Block',
                                 'Collection',
                                 'Comment',
                                 'Line',
                                 'Define',
                                 'Include',
                                 'Pragma',
                                 'IfDef',
                                 'IfNDef'])
def test_imports_from_cgen(cls):
    module = __import__('cgen')
    assert hasattr(module, cls)


@pytest.mark.parametrize('cls, args', [('Define', ('define', 0)),
                                       ('Include', ('include',)),
                                       ('Pragma', ('pragma',)),
                                       ('IfDef', ('', [], [])),
                                       ('IfNDef', ('', [], []))])
def test_preprocessor_classes_raise_deprecated_warning_when_imported_from_cgen(cls, args):
    module = __import__('cgen')
    cls = getattr(module, cls)
    with warnings.catch_warnings(record=True) as warn:
        warnings.simplefilter("always")
        cls(*args)
        assert len(warn) == 1
        assert issubclass(warn[-1].category, DeprecationWarning)
        assert cls.__name__ + ' should be imported from \'preprocessor\' package, not from \'cgen\'.' == str(
            warn[0].message)


@pytest.mark.parametrize('cls, args', [('Define', ('define', 0)),
                                       ('Include', ('include',)),
                                       ('Pragma', ('pragma',)),
                                       ('IfDef', ('', [], [])),
                                       ('IfNDef', ('', [], []))])
def test_preprocessor_classes_do_not_raise_deprecated_warning_when_imported_from_preprocessor(cls, args):
    module = __import__('cgen').preprocessor
    cls = getattr(module, cls)
    with warnings.catch_warnings(record=True) as warn:
        warnings.simplefilter("always")
        a = cls(*args)
        assert len(warn) == 0


@pytest.mark.parametrize('args, result', [
    (('condition == true', [], []), """#if condition == true
#endif"""),
    (('condition == true', [Define('my_define', '')], []), """#if condition == true
#define my_define
#endif"""),
    (('condition == true', [Define('if_define', '')], [Define('else_define', '')]), """#if condition == true
#define if_define
#else
#define else_define
#endif""")
])
def test_preprocessor_if_statement(args, result):
    from cgen.preprocessor import If
    assert str(If(*args)) == result



def test_cgen():
    s = Struct("yuck", [
        POD(np.float32, "h", ),
        POD(np.float32, "order"),
        POD(np.float32, "face_jacobian"),
        ArrayOf(POD(np.float32, "normal"), 17),
        POD(np.uint16, "a_base"),
        POD(np.uint16, "b_base"),
        #CudaGlobal(POD(np.uint8, "a_ilist_number")),
        POD(np.uint8, "b_ilist_number"),
        POD(np.uint8, "bdry_flux_number"),  # 0 if not on boundary
        POD(np.uint8, "reserved"),
        POD(np.uint32, "b_global_base"),
        ])
    f_decl = FunctionDeclaration(POD(np.uint16, "get_num"), [
        POD(np.uint8, "reserved"),
        POD(np.uint32, "b_global_base"),
        ])
    f_body = FunctionBody(f_decl, Block([
        POD(np.uint32, "i"),
        For("i = 0", "i < 17", "++i",
            If(
                "a > b",
                Assign("a", "b"),
                Block([
                    Assign("a", "b-1"),
                    #Break(),
                    ])
                ),
            ),
        #BlankLine(),
        Comment("all done"),
        ]))
    t_decl = Template('typename T',
                      FunctionDeclaration(Value('CUdeviceptr', 'scan'),
                                          [Value('CUdeviceptr', 'inputPtr'),
                                           Value('int', 'length')]))

    print(s)
    print(f_body)
    print(t_decl)
