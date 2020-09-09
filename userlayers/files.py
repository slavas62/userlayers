import os
import uuid

from django.utils.deconstruct import deconstructible

@deconstructible
class UuidHashFilenameUploadTo(object):
    def __init__(self, basepath):
        self.basepath = basepath
        
    def __call__(self, instance, filename):
        ext = os.path.splitext(filename)[-1]
        random_filename = uuid.uuid4().hex + ext
        path = os.path.join(self.basepath, random_filename)
        return path
