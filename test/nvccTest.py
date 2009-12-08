from codepy.cgen import *
from codepy.bpl import BoostPythonModule
from codepy.cuda import CudaModule
from codepy.cgen.cuda import CudaGlobal

# The host module should include a function which is callable from Python
hostMod = BoostPythonModule()


# This host function extracts a pointer and shape information from a PyCUDA
# GPUArray, and then sends them to a CUDA function.  The CUDA function
# returns a pointer to an array of the same type and shape as the input array.
# The host function then constructs a GPUArray with the result.
hostMod.add_function(
    FunctionBody(
        FunctionDeclaration(Pointer(Value("PyObject", "adjacentDifference")),
                            [Pointer(Value("PyObject", "gpuArray"))]),
        Block([Statement(x) for x in [
                    # Extract information from incoming GPUArray
                    'PyObject* shape = PyObject_GetAttrString(gpuArray, "shape")',
                    'PyObject* type = PyObject_GetAttrString(gpuArray, "dtype")',
                    'PyObject* pointer = PyObject_GetAttrString(gpuArray, "gpudata")',
                    'CUdeviceptr cudaPointer = boost::python::extract<CUdeviceptr>(pointer)',
                    'PyObject* length = PySequence_GetItem(shape, 0)',
                    'int intLength = boost::python::extract<int>(length)',
                    # Call CUDA function
                    'CUdeviceptr diffResult = diffInstance(cudaPointer, intLength)',
                    # Build resulting GPUArray
                    'PyObject* args = Py_BuildValue("()")',
                    'PyObject* newShape = Py_BuildValue("(i)", intLength)',
                    'PyObject* kwargs = Py_BuildValue("{sOsOsi}", "shape", newShape, "dtype", type, "gpudata", diffResult)',
                    'PyObject* GPUArrayClass = PyObject_GetAttrString(gpuArray, "__class__")',
                    'PyObject* remoteResult = PyObject_Call(GPUArrayClass, args, kwargs)',
                    'return remoteResult']])))
hostMod.add_to_preamble([Include('boost/python/extract.hpp')])

                                 
cudaMod = CudaModule(hostMod)
cudaMod.add_to_preamble([Include('cuda.h')])
diff =[
    Template('typename T', CudaGlobal(FunctionDeclaration(Value('void', 'diffKernel'),
                                                          [Value('T*', 'inputPtr'),
                                                           Value('int', 'length'),
                                                           Value('T*', 'outputPtr')]))),
    Block([Statement('int globalIndex = blockIdx.x * blockDim.x + threadIdx.x'),
           If('globalIndex == 0',
              Statement('outputPtr[0] = inputPtr[0]'),
              If('globalIndex < length',
                 Statement('outputPtr[globalIndex] = inputPtr[globalIndex] - inputPtr[globalIndex-1]'),
                 Statement('')))]),

    Template('typename T',
                FunctionDeclaration(Value('CUdeviceptr', 'difference'),
                                          [Value('CUdeviceptr', 'inputPtr'),
                                           Value('int', 'length')])),
    Block([Statement(x) for x in [
                'CUdeviceptr returnBuffer',
                'cuMemAlloc(&returnBuffer, sizeof(T) * length)',
                'int blockSize = 256',
                'int gridSize = (length-1)/blockSize + 1',
                'diffKernel<<<gridSize, blockSize>>>((T*)inputPtr, length, (T*)returnBuffer)',
                'return returnBuffer']])]
cudaMod.add_to_module(diff)
diffInstance = FunctionBody(
    FunctionDeclaration(Value('CUdeviceptr', 'diffInstance'),
                        [Value('CUdeviceptr', 'inputPtr'),
                         Value('int', 'length')]),
    Block([Statement('return difference<int>(inputPtr, length)')]))
# CudaModule.add_function also adds a declaration of this function to the BoostPythonModule which
# is responsible for the host function.
cudaMod.add_function(diffInstance)



import codepy.jit
gccToolchain = codepy.jit.guess_toolchain()
nvccToolchain = codepy.jit.guess_nvcctoolchain()

module = cudaMod.compile(gccToolchain, nvccToolchain, debug=True)
import pycuda.autoinit
import pycuda.driver


import pycuda.gpuarray
import numpy as np
length = 25
constantValue = 2
# This is a strange way to create a GPUArray, but is meant to illustrate
# how to construct a GPUArray if the GPU buffer it owns has been
# created by something else

pointer = pycuda.driver.mem_alloc(length * 4)
pycuda.driver.memset_d32(pointer, constantValue, length)
a = pycuda.gpuarray.GPUArray((25,), np.int32, gpudata=pointer)
b = module.adjacentDifference(a).get()

golden = [constantValue] + [0] * (length - 1)
difference = [(x-y)*(x-y) for x, y in zip(b, golden)]
error = sum(difference)
if (error == 0):
    print("Test passed!")
else:
    print("Error should be 0, but is: %s" % error)
    print("Test failed")

