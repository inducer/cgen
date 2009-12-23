#ifndef _UTHHFF_CODEPY_BPL_HPP_INCLUDED
#define _UTHHFF_CODEPY_BPL_HPP_INCLUDED




#include <boost/python.hpp>
#include <boost/python/suite/indexing/vector_indexing_suite.hpp>



#define CODEPY_PYTHON_ERROR(TYPE, REASON) \
{ \
  PyErr_SetString(PyExc_##TYPE, REASON); \
  throw boost::python::error_already_set(); \
}




namespace codepy
{
  template <class T>
    class no_compare_indexing_suite :
      public boost::python::vector_indexing_suite<T, false, no_compare_indexing_suite<T> >
  {
    public:
      static bool contains(T &container, typename T::value_type const &key)
      { CODEPY_PYTHON_ERROR(NotImplementedError, "containment checking not supported on this container"); }
  };
}




#endif
