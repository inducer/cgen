from cgen import (
        POD, Struct, FunctionBody, FunctionDeclaration,
        For, If, Assign, Value, Block, ArrayOf, Comment,
        Template)
import numpy as np


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
