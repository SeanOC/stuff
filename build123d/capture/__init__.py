"""Offline spike only: production/COPYed packages must never import capture.

CB2 may reuse capture.encoding (stdlib only); image analysis remains in the browser.
"""
# Keep encoding importable without OpenCV in the render service.
__all__ = ['detect_grid', 'rectify', 'segment', 'footprint']


def __getattr__(name):
    if name in __all__:
        from importlib import import_module
        module = import_module('.footprint', __name__)
        globals().update({key: getattr(module, key) for key in __all__})
        return globals()[name]
    raise AttributeError(name)
