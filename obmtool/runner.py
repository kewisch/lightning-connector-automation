from profile import ObmProfile
from mozrunner.local import ThunderbirdRunner

class ObmRunner(ThunderbirdRunner):
  profile_class = ObmProfile
