import ctypes

OPCDA_DLL = ctypes.CDLL('./dlls/OPCClientDLL.dll')

#type 정의
# VARIANT type constants
#pythoncom.VT_EMPTY       # 0
#pythoncom.VT_NULL        # 1
#pythoncom.VT_I2          # 2 (16-bit signed integer)
#pythoncom.VT_I4          # 3 (32-bit signed integer)
#pythoncom.VT_R4          # 4 (32-bit floating point)
#pythoncom.VT_R8          # 5 (64-bit floating point)
#pythoncom.VT_CY          # 6 (currency)
#pythoncom.VT_DATE        # 7 (date)
#pythoncom.VT_BSTR        # 8 (BSTR string)
#pythoncom.VT_DISPATCH    # 9 (IDispatch pointer)
#pythoncom.VT_ERROR       # 10 (SCODE)
#pythoncom.VT_BOOL        # 11 (boolean)
#pythoncom.VT_VARIANT     # 12 (VARIANT pointer)
#pythoncom.VT_UNKNOWN     # 13 (IUnknown pointer)
#pythoncom.VT_DECIMAL     # 14 (16-byte fixed-point number)
#pythoncom.VT_I1          # 16 (8-bit signed integer)
#pythoncom.VT_UI1         # 17 (8-bit unsigned integer)
#pythoncom.VT_UI2         # 18 (16-bit unsigned integer)
#pythoncom.VT_UI4         # 19 (32-bit unsigned integer)
#pythoncom.VT_I8          # 20 (64-bit signed integer)
#pythoncom.VT_UI8         # 21 (64-bit unsigned integer)
#pythoncom.VT_INT         # 22 (integer)
#pythoncom.VT_UINT        # 23 (unsigned integer)
#pythoncom.VT_VOID        # 24 (C style void)
#pythoncom.VT_HRESULT     # 25 (HRESULT)
#pythoncom.VT_PTR         # 26 (pointer type)
#pythoncom.VT_SAFEARRAY   # 27 (SAFEARRAY)
#pythoncom.VT_CARRAY      # 28 (C style array)
#pythoncom.VT_USERDEFINED # 29 (user defined type)
#pythoncom.VT_LPSTR       # 30 (null-terminated string)
#pythoncom.VT_LPWSTR      # 31 (wide null-terminated string)
#pythoncom.VT_RECORD      # 36 (user defined type)
#pythoncom.VT_FILETIME    # 64 (FILETIME)
#pythoncom.VT_BLOB        # 65 (Length-prefixed bytes)
#pythoncom.VT_STREAM      # 66 (Stream object)
#pythoncom.VT_STORAGE     # 67 (Storage object)
#pythoncom.VT_STREAMED_OBJECT  # 68 (Streamed object)
#pythoncom.VT_STORED_OBJECT    # 69 (Stored object)
#pythoncom.VT_BLOB_OBJECT      # 70 (Blob object)
#pythoncom.VT_CF          # 71 (Clipboard format)
#pythoncom.VT_CLSID       # 72 (CLSID)
#pythoncom.VT_VERSIONED_STREAM # 73 (Versioned stream

# VARIANT 구조체 정의
# Union지원이 되지않아 디버그모드로 볼경우
# 프로그램이 꺼질수 있습니다...

class _DUMMYSTRUCTNAME(ctypes.Structure):
    _fields_ = [
        ("scale", ctypes.c_byte),
        ("sign", ctypes.c_byte)
    ]
    _pack_ = 8

class _DUMMYSTRUCTNAME2(ctypes.Structure):
    _fields_ = [
        ("Lo32", ctypes.c_ulong),
        ("Mid32", ctypes.c_ulong)
    ]
    _pack_ = 8

class _DUMMYUNIONNAME(ctypes.Union):
    _fields_ = [
        ("DUMMYSTRUCTNAME", _DUMMYSTRUCTNAME),
        ("signscale",ctypes.c_ushort)
    ]

class _DUMMYUNIONNAME2(ctypes.Union):
    _fields_ = [
        ("DUMMYSTRUCTNAME2", _DUMMYSTRUCTNAME2),
        ("Lo64",ctypes.c_ulonglong)
    ]

class DECIMAL(ctypes.Structure):
    _fields_ = [
        ("wReserved", ctypes.c_ushort),
        ("DUMMYUNIONNAME",_DUMMYUNIONNAME),
        ("Hi32",ctypes.c_ulong),
        ("DUMMYUNIONNAME",_DUMMYUNIONNAME2)
    ]
    _pack_ = 8

class _tagBRECORD(ctypes.Structure):
    _fields_ = [
        ("pvRecord", ctypes.c_void_p),
        #("pRecInfo", ctypes.POINTER(IRecordInfo))  # IRecordInfo의 정의가 필요
        ("pRecInfo",ctypes.c_void_p)
    ]

class _VARIANT_UNION(ctypes.Union):
    _fields_ = [
        ("llVal", ctypes.c_longlong),
        ("lVal", ctypes.c_long),
        ("bVal", ctypes.c_byte),
        ("iVal", ctypes.c_short),
        ("fltVal", ctypes.c_float),
        ("dblVal", ctypes.c_double),
        ("boolVal", ctypes.c_short),
        ("scode", ctypes.c_long),
        ("cyVal", ctypes.c_longlong),
        ("date", ctypes.c_double),
        ("bstrVal", ctypes.c_wchar_p),
        ("punkVal", ctypes.c_void_p),
        ("pdispVal", ctypes.c_void_p),
        ("parray", ctypes.c_void_p),
        ("pbVal", ctypes.POINTER(ctypes.c_byte)),
        ("piVal", ctypes.POINTER(ctypes.c_short)),
        ("plVal", ctypes.POINTER(ctypes.c_long)),
        ("pllVal", ctypes.POINTER(ctypes.c_longlong)),
        ("pfltVal", ctypes.POINTER(ctypes.c_float)),
        ("pdblVal", ctypes.POINTER(ctypes.c_double)),
        ("pboolVal", ctypes.POINTER(ctypes.c_short)),
        ("pscode", ctypes.POINTER(ctypes.c_long)),
        ("pcyVal", ctypes.POINTER(ctypes.c_longlong)),
        ("pdate", ctypes.POINTER(ctypes.c_double)),
        ("pbstrVal", ctypes.POINTER(ctypes.c_wchar_p)),
        ("ppunkVal", ctypes.POINTER(ctypes.c_void_p)),
        ("ppdispVal", ctypes.POINTER(ctypes.c_void_p)),
        ("pparray", ctypes.POINTER(ctypes.c_void_p)),
        ("pvarVal", ctypes.POINTER("VARIANT")),
        ("byref", ctypes.c_void_p),
        ("cVal", ctypes.c_char),
        ("uiVal", ctypes.c_ushort),
        ("ulVal", ctypes.c_ulong),
        ("ullVal", ctypes.c_ulonglong),
        ("intVal", ctypes.c_int),
        ("uintVal", ctypes.c_uint),
        ("pdecVal", ctypes.POINTER(DECIMAL)),
        ("pcVal", ctypes.POINTER(ctypes.c_char)),
        ("puiVal", ctypes.POINTER(ctypes.c_ushort)),
        ("pulVal", ctypes.POINTER(ctypes.c_ulong)),
        ("pullVal", ctypes.POINTER(ctypes.c_ulonglong)),
        ("pintVal", ctypes.POINTER(ctypes.c_int)),
        ("puintVal", ctypes.POINTER(ctypes.c_uint)),
        ("__VARIANT_NAME_4", _tagBRECORD)
    ]

class _tagVARIANT(ctypes.Structure):
    _fields_ = [
        ("vt", ctypes.c_ushort),
        ("wReserved1", ctypes.c_ushort),
        ("wReserved2", ctypes.c_ushort),
        ("wReserved3", ctypes.c_ushort),
        ("union", _VARIANT_UNION)
    ]

class tagVARIANT_union(ctypes.Union):
    _fields_ = [
        ("tagVARIANT", _tagVARIANT),
        ("decVal", DECIMAL)
    ]

class VARIANT(ctypes.Structure):
    _fields_ = [
        ("tag", tagVARIANT_union),
    ]
    _pack_ = 8


#VARIANT_PTR = ctypes.POINTER(VARIANT)


"""
시그니처 정의...
"""
OPCDA_DLL.DLLOPCClient_NEW.argtype = []
OPCDA_DLL.DLLOPCClient_NEW.restype = ctypes.c_void_p

OPCDA_DLL.DLLOPCClient_delete.argtype = [ctypes.c_void_p]
OPCDA_DLL.DLLOPCClient_delete.restype = None

OPCDA_DLL.DLLOPCClient_CheckOpcServerAct.argtype = [ctypes.c_void_p]
OPCDA_DLL.DLLOPCClient_CheckOpcServerAct.restype = ctypes.c_bool

OPCDA_DLL.DLLOPCClient_init.argtype = [ctypes.c_void_p,ctypes.c_char_p,ctypes.c_char_p]
OPCDA_DLL.DLLOPCClient_init.restype = ctypes.c_bool

OPCDA_DLL.DLLOPCClient_getItemNames.argtype = [ctypes.c_void_p,ctypes.POINTER(ctypes.POINTER(ctypes.c_char_p)),ctypes.POINTER(ctypes.c_int)]
OPCDA_DLL.DLLOPCClient_ItemNamesRelease.argtype = [ctypes.POINTER(ctypes.POINTER(ctypes.c_char_p)),ctypes.c_int]

OPCDA_DLL.DLLOPCClient_additem.argtype = [ctypes.c_void_p,ctypes.c_char_p]
OPCDA_DLL.DLLOPCClient_additem.restype = None

OPCDA_DLL.DLLOPCClient_readitem.argtype = [ctypes.c_void_p,ctypes.c_char_p,ctypes.POINTER(VARIANT)]
OPCDA_DLL.DLLOPCClient_readitem.restype = None

OPCDA_DLL.DLLOPCClient_readitems.argtype = [ctypes.c_void_p,ctypes.POINTER(ctypes.c_char_p),ctypes.POINTER(ctypes.POINTER(VARIANT)),ctypes.c_int]
OPCDA_DLL.DLLOPCClient_readitems.restype = None

OPCDA_DLL.DLLOPCClient_writeitem.argtype = [ctypes.c_void_p,ctypes.c_char_p,ctypes.POINTER(VARIANT)]
OPCDA_DLL.DLLOPCClient_writeitem.restype = None

OPCDA_DLL.DLLOPCClient_Release.argtype = [ctypes.c_void_p]
OPCDA_DLL.DLLOPCClient_Release.restype = None

OPCDA_DLL.DLLOPCClient_CoInitializeEx.argtype = []
OPCDA_DLL.DLLOPCClient_CoInitializeEx.restype = None

OPCDA_DLL.DLLOPCClient_CoUnInitializeEx.argtype = []
OPCDA_DLL.DLLOPCClient_CoUnInitializeEx.restype = None
class DLLOPCClient:
    def __init__(self):
        bResult = True
        self.obj = None

        try:
            self.obj = OPCDA_DLL.DLLOPCClient_NEW()
        except:
            bResult = False

        if bResult == False:
            OPCDA_DLL.DLLOPCClient_CoUnInitializeEx()
            bResult = True
            try:
                self.obj = OPCDA_DLL.DLLOPCClient_NEW()
            except:
                bResult = False

    def __del__(self):
        self.Release()
        OPCDA_DLL.DLLOPCClient_delete(ctypes.c_void_p(self.obj))

    def Init(self,szOPCServerName,szHost):
        return OPCDA_DLL.DLLOPCClient_init(ctypes.c_void_p(self.obj),szOPCServerName.encode('utf-8'),szHost.encode('utf-8'))

    def CheckOpcServerAct(self):
        return OPCDA_DLL.DLLOPCClient_CheckOpcServerAct(ctypes.c_void_p(self.obj))

    def getItemNames(self, ArrName : list):
        """
        arrNames = list()
        pArrnames = ctypes.POINTER(ctypes.POINTER(ctypes.c_char_p))()
        nCount = ctypes.c_int()

        OPCDA_DLL.DLLOPCClient_getItemNames(ctypes.c_void_p(self.obj),ctypes.byref(pArrnames),ctypes.byref(nCount))

        result = ctypes.cast(pArrnames,ctypes.POINTER(ctypes.c_char_p))

        for i in range(nCount.value):
            str = ctypes.cast(result[i],ctypes.c_char_p).value.decode('utf-8')
            if i%1000 == 0 :
                time.sleep(0.01)
            arrNames.append(str)

        # 메모리 해제 ..
        OPCDA_DLL.DLLOPCClient_ItemNamesRelease(ctypes.byref(pArrnames),nCount)
        """

    def additem(self, item_name : str):
        OPCDA_DLL.DLLOPCClient_additem(ctypes.c_void_p(self.obj), item_name.encode('utf-8'))

    def readitem(self,item_name:str, var: VARIANT):
        OPCDA_DLL.DLLOPCClient_readitem(ctypes.c_void_p(self.obj),item_name.encode('utf-8'),ctypes.byref(var))

    def readitems(self, item_names : list, vars : list):

        encoded_strings = [s.encode('utf-8') for s in item_names]
        array_of_strings = (ctypes.c_char_p * len(encoded_strings))()

        for i, s in enumerate(encoded_strings):
            array_of_strings[i] = ctypes.c_char_p(s)

        arr_var = (VARIANT * len(item_names))()
        for i in range(len(item_names)):
            var = VARIANT()
            arr_var[i] = var
        OPCDA_DLL.DLLOPCClient_readitems(ctypes.c_void_p(self.obj),array_of_strings,ctypes.byref(arr_var),len(item_names))

        for i in range(len(item_names)):
            type =arr_var[i].tag.tagVARIANT.vt
            #type = arr_var[i].vt
            if type == 0:
                vars.append(None)
            else:
                vars.append(arr_var[i])

    def writeitem(self, item_name: str ,val : VARIANT):
        return OPCDA_DLL.DLLOPCClient_writeitem(ctypes.c_void_p(self.obj),item_name.encode('utf-8'),ctypes.byref(val))

    def Release(self):
        return OPCDA_DLL.DLLOPCClient_Release(ctypes.c_void_p(self.obj))

    def CoInitializeEx(self):
        OPCDA_DLL.DLLOPCClient_CoInitializeEx()

    def CoUnInitializeEx(self):
        OPCDA_DLL.DLLOPCClient_CoUnInitializeEx()





