from django.utils import timezone;
from threading import Thread

def _add_oplog(user, op, app, app_version, message):
    try:
        time = timezone.localtime(timezone.now())
        oplog = OpLog(user=user, op=op, app=app,
                      app_version=app_version, time=time, message=message)
        oplog.save()
    except:
        pass

def add_oplog(user, op, app, app_version, message):
    t = Thread(target=_add_oplog, args=(user, op, app, app_version, message))
    t.start()

