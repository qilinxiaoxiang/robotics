# Prelude prepended to bridge jobs: resolves the target Fusion data folder from
# FUSION_PROJECT and FUSION_PATH (slash-separated folders under the project root).
# The shell scripts substitute the two placeholders before sending.
_project, _path = '@@PROJECT@@', '@@PATH@@'
_hub = app.data.activeHub
_p = [x for x in _hub.dataProjects if x.name == _project]
if not _p:
    raise RuntimeError('project not found in active hub %r: %r' % (_hub.name, _project))
folder = _p[0].rootFolder
for _part in [s for s in _path.split('/') if s]:
    _next = folder.dataFolders.itemByName(_part)
    if _next is None and '@@CREATE@@' == 'yes':
        _next = folder.dataFolders.add(_part)
    if _next is None:
        raise RuntimeError('folder not found: %r in %r' % (_part, _path))
    folder = _next


def designs(f):
    """name -> {extension: DataFile} for the files in folder f."""
    out = {}
    for d in f.dataFiles:
        out.setdefault(d.name, {})[d.fileExtension] = d
    return out
