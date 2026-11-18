"""Cancel the running session of one of this account's Kaggle kernels (the CLI has no cancel command; the SDK does).

  <kaggle tool python> train/kaggle_cancel.py <kernel slug, e.g. microduck-ts2-mamba> [--dry-run]

Looks up the kernel's current session id (SaveKernel responses and GetKernel carry it under different names, so every
integer field whose name mentions "session" is printed) and calls CancelKernelSession on it. The kernel, its code and
its earlier versions are kept; only the running session ends.
"""
import sys

from kaggle.api.kaggle_api_extended import KaggleApi
from kagglesdk.kernels.types.kernels_api_service import (ApiCancelKernelSessionRequest, ApiGetKernelRequest,
                                                         ApiGetKernelSessionStatusRequest)

slug = sys.argv[1]
dry = "--dry-run" in sys.argv
api = KaggleApi()
api.authenticate()
user = api.config_values["username"]
with api.build_kaggle_client() as k:
    c = k.kernels.kernels_api_client
    st = ApiGetKernelSessionStatusRequest()
    st.user_name, st.kernel_slug = user, slug
    r = c.get_kernel_session_status(st)
    print("status", r.status)
    g = ApiGetKernelRequest()
    g.user_name, g.kernel_slug = user, slug
    kr = c.get_kernel(g)
    sid = None
    for obj in (r, kr, getattr(kr, "metadata", None)):
        for name in dir(obj) if obj is not None else ():
            if "session" in name.lower() and not name.startswith("_"):
                v = getattr(obj, name, None)
                if isinstance(v, int) and v:
                    print(type(obj).__name__, name, v)
                    sid = sid or v
    if sid is None:
        sys.exit("no session id found")
    if dry:
        sys.exit(0)
    q = ApiCancelKernelSessionRequest()
    q.kernel_session_id = sid
    print("cancel", sid, c.cancel_kernel_session(q))
